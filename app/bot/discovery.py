import logging
import re
from dataclasses import dataclass
from typing import Callable
from urllib.parse import quote_plus

from playwright._impl._errors import TargetClosedError
from playwright.async_api import Page

from app.bot.project_meta import fetch_project_meta, passes_filters
from app.bot.utils import (
    build_project_search_urls,
    default_skills_from_config,
    extract_project_id,
    human_delay,
    load_keywords_config,
    matches_user_skill,
    normalize_url,
    parse_skills_list,
    skill_to_category,
    url_category_matches_target,
)
from app.database import get_processed_project_ids, record_bid
from app.error_logger import log_error

logger = logging.getLogger(__name__)


@dataclass
class ProjectCandidate:
    project_id: str
    title: str
    url: str
    category: str
    snippet: str
    matched_skill: str = ""
    proposal_count: int | None = None
    posted_label: str | None = None
    posted_age_days: float | None = None
    description: str = ""
    skill_tags: list[str] | None = None
    budget_label: str | None = None


async def _collect_links_from_page(page: Page) -> list[tuple[str, str]]:
    """Return list of (url, title) from project search results."""
    results: list[tuple[str, str]] = []
    selectors = [
        'a[href*="/projects/"]',
        'fl-project-contest-card a[href*="/projects/"]',
        '.JobSearchCard-item a',
        '[data-project-id] a',
    ]

    seen_urls: set[str] = set()
    for selector in selectors:
        links = page.locator(selector)
        count = await links.count()
        for i in range(min(count, 80)):
            try:
                link = links.nth(i)
                href = await link.get_attribute("href")
                if not href or "/projects/" not in href:
                    continue
                url = normalize_url(href)
                if url in seen_urls:
                    continue
                if any(x in url for x in ["/contest/", "/users/", "/employer/", "/jobs/"]):
                    continue
                title = (await link.inner_text()).strip()
                if not title or len(title) < 5:
                    parent = link.locator(
                        "xpath=ancestor::*[contains(@class,'title') or contains(@class,'Title')][1]"
                    )
                    if await parent.count() > 0:
                        title = (await parent.first.inner_text()).strip()
                if len(title) < 3:
                    title = "Untitled project"
                seen_urls.add(url)
                results.append((url, title[:500]))
            except TargetClosedError:
                raise
            except Exception:
                log_error(
                    "link_collection_failed",
                    f"Failed to process link #{i} from selector: {selector}",
                    context="Collecting project links from Freelancer search results",
                )
                continue
        if results:
            break

    if not results:
        html = await page.content()
        for match in re.finditer(r'href="(/projects/[^"]+)"', html):
            url = normalize_url(match.group(1))
            if "/jobs/" in url or url in seen_urls:
                continue
            seen_urls.add(url)
            results.append((url, "Project"))

    return results


def _build_search_urls(user_skills: list[str], config: dict) -> list[str]:
    skills = user_skills or default_skills_from_config(config)
    urls = build_project_search_urls(skills)
    if urls:
        return urls
    return [
        f"https://www.freelancer.in/search/projects?q={quote_plus('web development')}&projectSort=latest",
    ]



async def fetch_new_projects(
    page: Page,
    max_per_scan: int = 20,
    max_age_days: int = 3,
    max_proposals: int = 50,
    my_skills: list[str] | None = None,
    target_categories: list[str] | None = None,
    stop_check: Callable[[], bool] | None = None,
) -> list[ProjectCandidate]:
    """
    Find projects matching the user's skills via project search (not job listings).
    Each project must mention at least one of your skills in title, description, or tags.
    """
    config = load_keywords_config()
    user_skills = parse_skills_list(my_skills) or default_skills_from_config(config)
    target_cats = target_categories or ["web_dev", "social_media", "seo"]

    if target_categories is not None:
        def _skill_matches_category(skill: str) -> bool:
            cat = skill_to_category(skill, config)
            return cat in target_cats or cat == "skill_match"

        filtered = [s for s in user_skills if _skill_matches_category(s)]
        if filtered:
            logger.info(
                "Category filter [%s] — kept %d of %d skills",
                ", ".join(target_cats), len(filtered), len(user_skills),
            )
            user_skills = filtered
        else:
            logger.warning("No skills match selected categories [%s], using all", ", ".join(target_cats))

    search_urls = _build_search_urls(user_skills, config)

    logger.info("Targeting %d skills via project search: %s", len(user_skills), ", ".join(user_skills[:8]))
    logger.info("Category filter: %s", ", ".join(target_cats))

    already_processed = get_processed_project_ids()
    candidates: list[ProjectCandidate] = []
    seen_ids: set[str] = set()
    links_to_check: list[tuple[str, str, str]] = []

    for search_url in search_urls:
        if stop_check and stop_check():
            logger.info("Stop requested — aborting project search")
            break
        try:
            logger.info("Searching projects: %s", search_url)
            await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
            await human_delay(2, 5)
            for _ in range(3):
                await page.evaluate("window.scrollBy(0, window.innerHeight)")
                await human_delay(1.5, 3)

            collected = await _collect_links_from_page(page)
            logger.info("Collected %d project links", len(collected))

            for url, title in collected:
                project_id = extract_project_id(url)
                if not project_id or project_id in seen_ids or project_id in already_processed:
                    continue
                seen_ids.add(project_id)
                full_url = url if url.startswith("http") else f"https://www.freelancer.in{url}"
                links_to_check.append((project_id, full_url, title))
        except TargetClosedError:
            raise
        except Exception as e:
            logger.warning("Search failed %s: %s", search_url, e)
            log_error(
                "search_failed",
                str(e),
                context=f"Searching projects on Freelancer with URL: {search_url}",
                page_url=search_url,
            )

    logger.info(
        "Checking %d projects against your skills (≤%d days, <%d proposals)...",
        len(links_to_check),
        max_age_days,
        max_proposals,
    )

    for project_id, full_url, title in links_to_check:
        if stop_check and stop_check():
            logger.info("Stop requested — aborting project checks")
            break
        if len(candidates) >= max_per_scan:
            break
        try:
            meta = await fetch_project_meta(page, full_url)
            display_title = meta.title or title or "Project"

            skill_text = " ".join(
                [
                    display_title,
                    meta.description or "",
                    " ".join(meta.skill_tags or []),
                    full_url,
                ]
            )
            matched_skill = matches_user_skill(skill_text, user_skills)
            if not matched_skill:
                reason = f"No match for your skills (checked: {', '.join(user_skills[:5])}…)"
                logger.info("Skip %s: %s", project_id, reason)
                record_bid(
                    project_id=project_id,
                    title=display_title,
                    url=full_url,
                    category="no_match",
                    status="skipped",
                    error_message=reason,
                )
                continue

            url_cat_ok, url_cat_slug, url_cat = url_category_matches_target(full_url, target_cats)
            if not url_cat_ok:
                reason = f"URL category '{url_cat_slug}' not in selected segments ({', '.join(target_cats)})"
                logger.info("Skip %s: %s", project_id, reason)
                record_bid(
                    project_id=project_id,
                    title=display_title,
                    url=full_url,
                    category="wrong_url_category",
                    status="skipped",
                    error_message=reason,
                )
                continue

            category = url_cat or skill_to_category(matched_skill, config)

            if url_cat:
                project_text = f"{display_title} {meta.description or ''}".lower()
                cat_keywords = [kw.lower() for kw in config.get(url_cat, [])]
                if not any(kw in project_text for kw in cat_keywords):
                    skill_cat = skill_to_category(matched_skill, config)
                    logger.info(
                        "URL says '%s' but project text has no %s keywords — reclassifying to '%s'",
                        url_cat, url_cat, skill_cat,
                    )
                    category = skill_cat

            ok, reason = passes_filters(meta, max_age_days, max_proposals)
            if not ok:
                logger.info("Skip %s: %s", project_id, reason)
                record_bid(
                    project_id=project_id,
                    title=display_title,
                    url=full_url,
                    category=category,
                    status="skipped",
                    error_message=reason,
                )
                continue

            if target_cats and category not in target_cats:
                reason = f"Category '{category}' not in selected segments ({', '.join(target_cats)})"
                logger.info("Skip %s: %s", project_id, reason)
                record_bid(
                    project_id=project_id,
                    title=display_title,
                    url=full_url,
                    category=category,
                    status="skipped",
                    error_message=reason,
                )
                continue

            candidates.append(
                ProjectCandidate(
                    project_id=project_id,
                    title=display_title,
                    url=full_url,
                    category=category,
                    snippet=meta.description[:200] if meta.description else display_title,
                    matched_skill=matched_skill,
                    proposal_count=meta.proposal_count,
                    posted_label=meta.posted_label,
                    posted_age_days=meta.posted_age_days,
                    description=meta.description,
                    skill_tags=meta.skill_tags,
                    budget_label=meta.budget_label,
                )
            )
            logger.info(
                "Eligible: %s — skill '%s', %s proposals, %s",
                project_id,
                matched_skill,
                meta.proposal_count,
                meta.posted_label,
            )
            await human_delay(2, 4)
        except TargetClosedError:
            raise
        except Exception as e:
            logger.warning("Failed to check project %s: %s", project_id, e)
            log_error(
                "project_metadata_fetch_failed",
                str(e),
                context=f"Fetching metadata for project '{title[:80]}' to check eligibility",
                project_id=project_id,
                page_url=full_url,
            )

    logger.info("Found %d skill-matched projects", len(candidates))

    candidates = _sort_by_priority(candidates)

    return candidates


def _sort_by_priority(candidates: list[ProjectCandidate]) -> list[ProjectCandidate]:
    def priority_score(c: ProjectCandidate) -> float:
        proposals = c.proposal_count if c.proposal_count is not None else 0
        age = c.posted_age_days if c.posted_age_days is not None else 999
        return proposals + (age * 5)

    candidates.sort(key=priority_score)
    if candidates:
        logger.info(
            "Bid order: 1) %s (%s proposals, %s), last: %s (%s proposals, %s)",
            candidates[0].title[:50],
            candidates[0].proposal_count,
            candidates[0].posted_label,
            candidates[-1].title[:50],
            candidates[-1].proposal_count,
            candidates[-1].posted_label,
        )
    return candidates
