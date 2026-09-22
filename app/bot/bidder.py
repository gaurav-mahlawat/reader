import logging
import random
import re
from dataclasses import dataclass
from typing import Callable

from playwright._impl._errors import TargetClosedError
from playwright.async_api import Page

from app.bot.discovery import ProjectCandidate
from app.bot.proposal_engine import (
    GREETINGS,
    build_proposal_from_template,
    build_proposal_sections,
    generate_question,
)
from app.bot.utils import human_delay, human_type
from app.error_logger import log_error
from app.schemas import BotSettings

logger = logging.getLogger(__name__)


@dataclass
class BidResult:
    success: bool
    bid_amount: float | None
    currency: str | None
    error_message: str | None


BID_BUTTON_SELECTORS = [
    'a:has-text("Bid Now")',
    'a:has-text("Place a Bid")',
    'a:has-text("Bid on This")',
    'a:has-text("Bid on This Project")',
    'a:has-text("Submit Proposal")',
    'a:has-text("Submit a Proposal")',
    'a:has-text("Apply Now")',
    'button:has-text("Bid Now")',
    'button:has-text("Place a Bid")',
    'button:has-text("Bid on This")',
    'button:has-text("Bid on This Project")',
    'button:has-text("Submit Proposal")',
    'button:has-text("Submit a Proposal")',
    'button:has-text("Apply Now")',
    '[role="button"]:has-text("Bid Now")',
    '[role="button"]:has-text("Place a Bid")',
    '[role="button"]:has-text("Bid on This")',
    '[role="button"]:has-text("Bid on This Project")',
    '[class*="BidNow"] button',
    '[class*="BidNow"] a',
    '[class*="bid-now"] button',
    '[class*="bid-now"] a',
    '[class*="place-bid"] button',
    '[class*="place-bid"] a',
    '[class*="PlaceBid"] button',
    '[class*="PlaceBid"] a',
    '[data-ng-click*="bid"] button',
    '[data-ng-click*="bid"]',
    '[ng-click*="bid"] button',
    '[ng-click*="bid"]',
]

AMOUNT_SELECTORS = [
    'input[formcontrolname="amount"]',
    'input[formcontrolname="bidAmount"]',
    'input[formcontrolname="bid_amount"]',
    'input[name="amount"]',
    'input[name="bid_amount"]',
    '#bid_amount',
    'input[placeholder*="amount" i]',
    'input[type="number"]',
]

PERIOD_SELECTORS = [
    'input[formcontrolname="period"]',
    'input[formcontrolname="deliveryDays"]',
    'input[formcontrolname="delivery_days"]',
    'select[formcontrolname="period"]',
    'select[formcontrolname="deliveryDays"]',
    'input[name="period"]',
    'input[name="delivery_days"]',
    'input[placeholder*="day" i]',
    'select[name="period"]',
    'select[name="delivery_days"]',
]

DESCRIPTION_SELECTORS = [
    'textarea[formcontrolname="description"]',
    'textarea[formcontrolname="proposal"]',
    'textarea[formcontrolname="coverLetter"]',
    'textarea[name="description"]',
    'textarea[name="proposal"]',
    'textarea',
    '[contenteditable="true"]',
]

SUBMIT_SELECTORS = [
    'button:has-text("Submit Proposal")',
    'button:has-text("Submit a Proposal")',
    'button:has-text("Submit Bid")',
    'button:has-text("Post Bid")',
    'button:has-text("Place Bid")',
    'button:has-text("Bid Now")',
    'button:has-text("Submit")',
    'button:has-text("Post")',
    'button:has-text("Send")',
    'button:has-text("Continue")',
    '[role="button"]:has-text("Submit Proposal")',
    '[role="button"]:has-text("Submit Bid")',
    '[role="button"]:has-text("Place Bid")',
    'button[type="submit"]:has-text("Bid")',
    'button[type="submit"]:has-text("Submit")',
    'button[type="submit"]:has-text("Post")',
]


async def _read_minimum_amount(page: Page) -> tuple[float | None, str | None]:
    """Try to read minimum bid from page text or input attributes."""
    content = await page.content()
    patterns = [
        r"minimum\s+bid[:\s]*(?:is\s+)?(?:[\$₹€£])?\s*([\d,]+(?:\.\d+)?)",
        r"bid\s+at\s+least[:\s]*(?:[\$₹€£])?\s*([\d,]+(?:\.\d+)?)",
        r"minimum[:\s]*(?:[\$₹€£])?\s*([\d,]+(?:\.\d+)?)",
        r"(?:at\s+least|minimum\s+of)[:\s]*(?:[\$₹€£])?\s*([\d,]+(?:\.\d+)?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            amount = float(match.group(1).replace(",", ""))
            return amount, None

    for selector in AMOUNT_SELECTORS:
        locator = page.locator(selector).first
        try:
            if await locator.count() == 0:
                continue
            min_attr = await locator.get_attribute("min")
            if min_attr:
                return float(min_attr), None
            placeholder = await locator.get_attribute("placeholder") or ""
            pm = re.search(r"([\d,]+(?:\.\d+)?)", placeholder)
            if pm:
                return float(pm.group(1).replace(",", "")), None
        except TargetClosedError:
            raise
        except Exception:
            log_error(
                "minimum_amount_read_failed",
                f"Failed to read minimum amount from selector: {selector}",
                context="Reading minimum bid amount from bid form on Freelancer project page",
                page_url=page.url,
            )
            continue

    return None, "Could not determine minimum bid amount"


async def _detect_currency(page: Page) -> str | None:
    content = await page.content()
    if "₹" in content or "INR" in content:
        return "INR"
    if "€" in content or "EUR" in content:
        return "EUR"
    if "£" in content or "GBP" in content:
        return "GBP"
    return "USD"


async def _fill_amount(page: Page, amount: float, stop_check: Callable[[], bool] | None = None) -> bool:
    if stop_check and stop_check():
        return False
    amount_str = str(int(amount)) if amount == int(amount) else str(amount)
    for selector in AMOUNT_SELECTORS:
        locator = page.locator(selector).first
        try:
            if await locator.count() > 0 and await locator.is_visible():
                await locator.click()
                await locator.fill(amount_str)
                return True
        except TargetClosedError:
            raise
        except Exception:
            log_error(
                "amount_fill_failed",
                f"Failed to fill bid amount with selector: {selector}",
                context=f"Filling bid amount field ({amount_str}) in bid form",
                page_url=page.url,
            )
            continue
    return False


async def _fill_period(page: Page, days: int) -> None:
    for selector in PERIOD_SELECTORS:
        locator = page.locator(selector).first
        try:
            if await locator.count() > 0 and await locator.is_visible():
                tag_name = (await locator.evaluate("el => el.tagName")).lower()
                if tag_name == "select":
                    await locator.select_option(str(days))
                else:
                    await locator.click()
                    await locator.fill(str(days))
                return
        except TargetClosedError:
            raise
        except Exception:
            log_error(
                "period_fill_failed",
                f"Failed to fill delivery period with selector: {selector}",
                context=f"Filling delivery period field ({days} days) in bid form",
                page_url=page.url,
            )
            continue


async def _fill_description(page: Page, text: str, stop_check: Callable[[], bool] | None = None) -> bool:
    if stop_check and stop_check():
        return False
    for selector in DESCRIPTION_SELECTORS:
        locator = page.locator(selector).first
        try:
            if await locator.count() > 0 and await locator.is_visible():
                tag_name = (await locator.evaluate("el => el.tagName")).lower()
                if tag_name == "textarea":
                    await human_type(page, selector, text, stop_check=stop_check)
                else:
                    await locator.click()
                    await locator.fill(text)
                return True
        except TargetClosedError:
            raise
        except Exception:
            log_error(
                "description_fill_failed",
                f"Failed to fill proposal description with selector: {selector}",
                context="Filling proposal description textarea in bid form",
                page_url=page.url,
            )
            continue
    return False


async def _submit_bid(page: Page, stop_check: Callable[[], bool] | None = None) -> bool:
    if stop_check and stop_check():
        return False
    for selector in SUBMIT_SELECTORS:
        locator = page.locator(selector).first
        try:
            if await locator.count() > 0 and await locator.is_visible():
                await locator.scroll_into_view_if_needed()
                await locator.click()
                return True
        except TargetClosedError:
            raise
        except Exception:
            log_error(
                "submit_button_click_failed",
                f"Failed to click submit button with selector: {selector}",
                context="Clicking submit button to place bid on Freelancer",
                page_url=page.url,
            )
            continue
    return False





def _select_template(settings: BotSettings, project: ProjectCandidate) -> tuple[str, str]:
    if settings.use_smart_proposals:
        return "", "smart"
    if project.category == "seo":
        return settings.seo_template, "seo"
    if project.category == "social_media":
        return settings.social_media_template, "social_media"
    if project.category == "web_dev":
        return settings.web_dev_template, "web_dev"
    return settings.generic_template, "generic"


MAX_PROPOSAL_LENGTH = 1200


def _truncate_proposal(text: str, max_len: int = MAX_PROPOSAL_LENGTH) -> str:
    if len(text) <= max_len:
        return text
    truncated = text[:max_len]
    last_newline = truncated.rfind("\n")
    last_sentence = truncated.rfind(". ")
    cut = max(last_newline, last_sentence)
    if cut > max_len * 0.6:
        return text[:cut + 1].rstrip()
    last_space = truncated.rfind(" ")
    if last_space > max_len * 0.6:
        return text[:last_space].rstrip()
    return truncated.rstrip()


def build_proposal(template: str, template_name: str, project: ProjectCandidate, settings: BotSettings | None = None) -> str:
    try:
        if template_name == "smart" or (settings and settings.use_smart_proposals):
            proposal = build_proposal_sections(project, settings)
        elif template:
            proposal = build_proposal_from_template(template, project, settings)
        else:
            proposal = build_proposal_sections(project, settings)
        return _truncate_proposal(proposal)
    except Exception:
        logger.exception("Proposal generation crashed, using fallback")
        name = (settings.freelancer_name if settings and settings.freelancer_name else "there").strip() or "there"
        return (
            f"Hi, my name is {name}.\n\n"
            f"I read your project \"{project.title}\" and I am confident I can deliver "
            f"excellent results. I have experience with similar projects and can start "
            f"right away. Let's discuss your requirements in detail.\n\n"
            f"- {name}\n"
            f"Skills: {project.matched_skill or project.category}"
        )


async def _is_bid_form_open(page: Page) -> bool:
    """Check if the bid form fields are already visible."""
    for selector in [*AMOUNT_SELECTORS, *DESCRIPTION_SELECTORS]:
        try:
            loc = page.locator(selector).first
            if await loc.count() > 0 and await loc.is_visible():
                return True
        except TargetClosedError:
            raise
        except Exception:
            log_error(
                "bid_form_check_failed",
                f"Failed to check bid form visibility with selector: {selector}",
                context="Checking if bid form is open on Freelancer project page",
                page_url=page.url,
            )
            continue
    return False


async def _open_bid_form(page: Page, stop_check: Callable[[], bool] | None = None) -> bool:
    """Click the 'Bid Now' / 'Place a Bid' button to open the bid form."""
    if stop_check and stop_check():
        return False
    if await _is_bid_form_open(page):
        logger.info("Bid form already open")
        return True

    for selector in BID_BUTTON_SELECTORS:
        if stop_check and stop_check():
            return False
        locator = page.locator(selector).first
        try:
            if await locator.count() > 0 and await locator.is_visible():
                logger.info("Opening bid form with selector: %s", selector)
                await locator.scroll_into_view_if_needed()
                await locator.click()
                await human_delay(3, 5, stop_check)
                if stop_check and stop_check():
                    return False
                if await _is_bid_form_open(page):
                    return True
                logger.info("Selector %s clicked but bid form did not appear; trying next selector", selector)
        except TargetClosedError:
            raise
        except Exception:
            log_error(
                "bid_button_click_failed",
                f"Failed to click bid button with selector: {selector}",
                context="Opening bid form on Freelancer project page by clicking bid button",
                page_url=page.url,
            )
            continue

    try:
        text_match = page.get_by_text(re.compile(r"bid|proposal|apply", re.IGNORECASE)).first
        if await text_match.count() > 0 and await text_match.is_visible():
            logger.info("Opening bid form with visible text fallback")
            await text_match.scroll_into_view_if_needed()
            await text_match.click()
            await human_delay(3, 5, stop_check)
            if await _is_bid_form_open(page):
                return True
    except TargetClosedError:
        raise
    except Exception:
        log_error(
            "bid_button_text_fallback_failed",
            "Failed to click bid button using text fallback (bid/proposal/apply)",
            context="Opening bid form via text-based fallback selector on Freelancer project page",
            page_url=page.url,
        )

    logger.warning("No bid button found or form did not appear")
    return False


async def place_minimum_bid(
    page: Page,
    project: ProjectCandidate,
    settings: BotSettings,
    stop_check: Callable[[], bool] | None = None,
) -> BidResult:
    try:
        if stop_check and stop_check():
            return BidResult(False, None, None, "Stopped by user")
        await page.goto(project.url, wait_until="domcontentloaded", timeout=90000)
        await human_delay(5, 10, stop_check)
        if stop_check and stop_check():
            return BidResult(False, None, None, "Stopped by user")

        page_html = (await page.content()).lower()
        if any(x in page_html for x in ["bidding ended", "project closed", "no longer accepting"]):
            log_error(
                "project_closed",
                f"Project '{project.title[:80]}' is closed or no longer accepting bids",
                context="Checking if project is still open for bidding",
                project_id=project.project_id,
                page_url=project.url,
            )
            return BidResult(False, None, None, "Project closed")

        if not await _open_bid_form(page, stop_check):
            log_error(
                "bid_form_open_failed",
                f"Could not open bid form on project '{project.title[:80]}'",
                context="Attempting to open bid form on Freelancer project page",
                project_id=project.project_id,
                page_url=project.url,
            )
            return BidResult(False, None, None, "Could not open bid form — no bid button found")
        if stop_check and stop_check():
            return BidResult(False, None, None, "Stopped by user")

        min_amount, err = await _read_minimum_amount(page)
        if min_amount is None:
            min_amount = 50.0
            logger.warning("Using fallback minimum amount %s for project %s", min_amount, project.project_id)
            log_error(
                "fallback_amount_used",
                f"Using fallback minimum amount {min_amount} for project '{project.title[:80]}'",
                context="Could not determine minimum bid amount from page, using fallback",
                project_id=project.project_id,
                page_url=project.url,
            )
        if stop_check and stop_check():
            return BidResult(False, None, None, "Stopped by user")

        currency = await _detect_currency(page)
        template, template_name = _select_template(settings, project)
        proposal = build_proposal(template, template_name, project, settings)

        if not await _fill_amount(page, min_amount, stop_check):
            logger.warning("Failed to fill amount field for %s", project.project_id)
            log_error(
                "amount_fill_failed",
                f"Could not fill bid amount field ({min_amount}) on project '{project.title[:80]}'",
                context="Filling bid amount in bid form",
                project_id=project.project_id,
                page_url=project.url,
            )
            return BidResult(False, None, currency, "Could not fill bid amount field")
        if stop_check and stop_check():
            return BidResult(False, None, None, "Stopped by user")

        await _fill_period(page, settings.delivery_days)
        if stop_check and stop_check():
            return BidResult(False, None, None, "Stopped by user")

        if not await _fill_description(page, proposal, stop_check):
            logger.warning("Failed to fill proposal textarea for %s", project.project_id)
            log_error(
                "description_fill_failed",
                f"Could not fill proposal description on project '{project.title[:80]}'",
                context="Filling proposal description in bid form",
                project_id=project.project_id,
                page_url=project.url,
            )
            return BidResult(False, min_amount, currency, "Could not fill proposal textarea")
        if stop_check and stop_check():
            return BidResult(False, None, None, "Stopped by user")

        await human_delay(3, 6, stop_check)
        if stop_check and stop_check():
            return BidResult(False, None, None, "Stopped by user")

        if not await _submit_bid(page, stop_check):
            logger.warning("Failed to find submit button for %s", project.project_id)
            log_error(
                "submit_button_not_found",
                f"Could not find submit button on project '{project.title[:80]}'",
                context="Looking for submit bid button after filling bid form",
                project_id=project.project_id,
                page_url=project.url,
            )
            return BidResult(False, min_amount, currency, "Could not find submit bid button")

        await human_delay(5, 8, stop_check)

        after_text = (await page.content()).lower()
        if any(
            phrase in after_text
            for phrase in ["bid placed", "successfully placed", "your bid has been", "bid submitted", "proposal sent", "proposal submitted"]
        ):
            logger.info("Bid placed successfully on %s", project.project_id)
            return BidResult(True, min_amount, currency, None)

        error_locators = page.locator('[class*="error"], [class*="Error"], .alert-danger, .alert-error')
        if await error_locators.count() > 0:
            err_text = (await error_locators.first.inner_text()).strip()[:300]
            if err_text:
                logger.warning("Bid error on %s: %s", project.project_id, err_text)
                min_match = re.search(r"(?:at\s+least|minimum)[:\s]*(?:[\$₹€£])?\s*([\d,]+(?:\.\d+)?)", err_text, re.IGNORECASE)
                if min_match:
                    corrected = float(min_match.group(1).replace(",", ""))
                    logger.info("Retrying bid on %s with corrected minimum amount %s", project.project_id, corrected)
                    if await _fill_amount(page, corrected, stop_check):
                        await human_delay(3, 6, stop_check)
                        if stop_check and stop_check():
                            return BidResult(False, None, None, "Stopped by user")
                        if await _submit_bid(page, stop_check):
                            await human_delay(5, 8, stop_check)
                            after_text = (await page.content()).lower()
                            if any(
                                phrase in after_text
                                for phrase in ["bid placed", "successfully placed", "your bid has been", "bid submitted", "proposal sent", "proposal submitted"]
                            ):
                                logger.info("Bid placed successfully on %s after amount correction", project.project_id)
                                return BidResult(True, corrected, currency, None)
                            err_loc2 = page.locator('[class*="error"], [class*="Error"], .alert-danger, .alert-error')
                            if await err_loc2.count() > 0:
                                err2 = (await err_loc2.first.inner_text()).strip()[:300]
                                if err2:
                                    log_error(
                                        "bid_error_after_retry",
                                        err2,
                                        context=f"Error after retrying with corrected amount {corrected} on '{project.title[:80]}'",
                                        project_id=project.project_id,
                                        page_url=project.url,
                                    )
                                    return BidResult(False, corrected, currency, err2)
                log_error(
                    "bid_error_from_page",
                    err_text,
                    context=f"Error message found on page after submitting bid for '{project.title[:80]}'",
                    project_id=project.project_id,
                    page_url=project.url,
                )
                return BidResult(False, min_amount, currency, err_text)

        logger.warning("Bid result unclear for %s — assuming success", project.project_id)
        log_error(
            "bid_result_unclear",
            f"Bid result unclear for project '{project.title[:80]}' — assuming success",
            context="Bid submitted but no confirmation or error message found on page",
            project_id=project.project_id,
            page_url=project.url,
        )
        return BidResult(True, min_amount, currency, None)

    except TargetClosedError:
        raise
    except Exception as e:
        logger.exception("Bid failed for %s", project.project_id)
        log_error(
            "bid_crashed",
            str(e),
            context=f"Exception while placing bid on project '{project.title[:80]}'",
            project_id=project.project_id,
            page_url=project.url,
        )
        return BidResult(False, None, None, str(e))
