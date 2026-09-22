import logging
import re
from dataclasses import dataclass

from playwright.async_api import Page

from app.bot.utils import human_delay
from app.error_logger import log_error

logger = logging.getLogger(__name__)


@dataclass
class ProjectMeta:
    proposal_count: int | None
    posted_age_days: float | None
    posted_label: str | None
    title: str = ""
    description: str = ""
    skill_tags: list[str] | None = None
    budget_label: str | None = None


def parse_posted_age_days(text: str, html: str | None = None) -> float | None:
    """Parse 'Posted 21 minutes ago' / 'Posted 2 days ago' into fractional days.
    Tries body text first, then falls back to raw HTML if available.
    """
    sources = [text]
    if html:
        sources.append(html)

    for src in sources:
        m = re.search(
            r"posted\s+(\d+)\s*(second|minute|hour|day|week|month)s?\s+ago",
            src,
            re.IGNORECASE,
        )
        if m:
            value = int(m.group(1))
            unit = m.group(2).lower()
            if unit == "second":
                return value / 86400
            if unit == "minute":
                return value / 1440
            if unit == "hour":
                return value / 24
            if unit == "day":
                return float(value)
            if unit == "week":
                return value * 7
            if unit == "month":
                return value * 30
            return None
    return None


def parse_proposal_count_from_html(html: str) -> int | None:
    patterns = [
        r'"bidCount"\s*:\s*(\d+)',
        r'"bid_count"\s*:\s*(\d+)',
        r'"num_bids"\s*:\s*(\d+)',
        r'"bids"\s*:\s*(\d+)',
        r'bidCount["\']?\s*[:=]\s*(\d+)',
        r"(\d+)\s+freelancers?\s+bid",
        r"(\d+)\s+proposals?\b",
        r"(\d+)\s+bids?\s+on\s+this",
    ]
    counts: list[int] = []
    for pattern in patterns:
        for match in re.finditer(pattern, html, re.IGNORECASE):
            counts.append(int(match.group(1)))
    if counts:
        # Prefer bidCount-style values (usually first accurate hit)
        return counts[0]
    return None


async def _extract_skill_tags(page: Page) -> list[str]:
    tags: list[str] = []
    selectors = [
        "fl-tag",
        '[class*="SkillTag"]',
        '[class*="skill-tag"]',
        ".skills-list a",
        '[data-component="skills"] a',
        'a[href*="/jobs/"]',
    ]
    for selector in selectors:
        try:
            loc = page.locator(selector)
            count = await loc.count()
            for i in range(min(count, 30)):
                text = (await loc.nth(i).inner_text()).strip()
                if text and 2 < len(text) < 80 and text not in tags:
                    tags.append(text)
        except Exception:
            log_error(
                "skill_tag_extraction_failed",
                f"Failed to extract skill tags with selector: {selector}",
                context="Extracting skill tags from Freelancer project page",
                page_url=page.url,
            )
            continue
    return tags[:25]


async def fetch_project_meta(page: Page, url: str) -> ProjectMeta:
    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
    await human_delay(1.5, 3)
    html = await page.content()
    body = await page.inner_text("body")

    proposal_count = parse_proposal_count_from_html(html)
    posted_label = None
    posted_sources = [body, html]
    for src in posted_sources:
        posted_match = re.search(
            r"posted\s+\d+\s*(?:second|minute|hour|day|week|month)s?\s+ago",
            src,
            re.IGNORECASE,
        )
        if posted_match:
            posted_label = posted_match.group(0)
            break
    posted_age_days = parse_posted_age_days(body, html)

    title = ""
    try:
        h1 = page.locator("h1").first
        if await h1.count() > 0:
            title = (await h1.inner_text()).strip()
    except Exception:
        log_error(
            "title_extraction_failed",
            "Failed to extract project title from h1 element",
            context="Extracting project title from Freelancer project page",
            page_url=page.url,
        )

    description = ""
    desc_selectors = [
        '[class*="ProjectDescription"]',
        '[class*="project-description"]',
        ".PageProjectViewLogout-detail",
        "section",
    ]
    for selector in desc_selectors:
        try:
            loc = page.locator(selector).first
            if await loc.count() > 0:
                description = (await loc.inner_text()).strip()[:3000]
                if len(description) > 80:
                    break
        except Exception:
            log_error(
                "description_extraction_failed",
                f"Failed to extract project description with selector: {selector}",
                context="Extracting project description from Freelancer project page",
                page_url=page.url,
            )
            continue
    if not description:
        description = body[:3000]

    skill_tags = await _extract_skill_tags(page)
    budget_label = _extract_budget(html)

    return ProjectMeta(
        proposal_count=proposal_count,
        posted_age_days=posted_age_days,
        posted_label=posted_label,
        title=title,
        description=description,
        skill_tags=skill_tags,
        budget_label=budget_label,
    )


def _extract_budget(html: str) -> str | None:
    patterns = [
        r'budget["\s:=]+(?:<[^>]+>)*\s*([\$\₹€£]?\s*[\d,]+(?:\s*[-–—to]+\s*)?[\$\₹€£]?\s*[\d,]+(?:\s*(?:USD|INR|EUR|GBP|AUD|per hour|/hr))?)',
        r'(?:budget|fixed.price)[:\s]*([\$\₹€£]?\s*[\d,]+(?:\s*[-–—to]+\s*)?[\$\₹€£]?\s*[\d,]+(?:\s*(?:USD|INR|EUR|GBP|AUD|per hour|/hr))?)',
        r'([\$\₹€£]\s*[\d,]+(?:\s*[-–—to]+\s*)?[\$\₹€£]?\s*[\d,]+(?:\s*(?:USD|INR|EUR|GBP|AUD|per hour|/hr))?)',
    ]
    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            label = match.group(1).strip()
            if label and len(label) > 2:
                return label
    return None


def passes_filters(
    meta: ProjectMeta,
    max_age_days: int,
    max_proposals: int,
) -> tuple[bool, str | None]:
    if meta.posted_age_days is not None and meta.posted_age_days > max_age_days:
        label = meta.posted_label or f"{meta.posted_age_days:.1f} days ago"
        return False, f"Too old ({label}, max {max_age_days} days)"

    if meta.proposal_count is not None and meta.proposal_count >= max_proposals:
        return False, f"Too many proposals ({meta.proposal_count}, max {max_proposals - 1})"

    if meta.proposal_count is None:
        logger.warning("Proposal count unknown — allowing project")
        return True, None

    return True, None
