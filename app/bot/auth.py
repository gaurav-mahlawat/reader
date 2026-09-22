import asyncio
import logging

from playwright.async_api import BrowserContext, Page, Playwright

from app.bot.utils import human_delay
from app.config import settings
from app.error_logger import log_error

logger = logging.getLogger(__name__)

LOGIN_URL = "https://www.freelancer.in/login"
LOGIN_SUCCESS_URL_PARTS = [
    "/dashboard",
    "/users/me",
    "/profile",
    "freelancer.com/users",
]

# Current Freelancer.in login form (2025/2026)
EMAIL_SELECTORS = [
    "#emailOrUsernameInput",
    'input[type="email"]',
    'input[name="username"]',
    'input[name="email"]',
    'input[placeholder*="mail" i]',
    'input[placeholder*="Email" i]',
    'input[placeholder*="email" i]',
    'input[id*="email" i]',
    'input[id*="username" i]',
    'input[id*="user" i]',
]

PASSWORD_SELECTORS = [
    "#passwordInput",
    'input[type="password"]',
    'input[name="password"]',
    'input[placeholder*="password" i]',
    'input[placeholder*="Password" i]',
    'input[id*="password" i]',
]

CONTINUE_SELECTORS = [
    'button:has-text("Continue")',
    'button:has-text("Next")',
    'input[type="submit"]:has-text("Continue")',
    'input[type="submit"]:has-text("Next")',
    'button[type="submit"]:has-text("Continue")',
    'button[type="submit"]:has-text("Next")',
]

SUBMIT_SELECTORS = [
    'button[type="submit"]:has-text("Log in")',
    'button[type="submit"]:has-text("Log In")',
    'button:has-text("Log in")',
    'button:has-text("Log In")',
    'button:has-text("Sign in")',
    'button:has-text("Sign In")',
    'button[type="submit"]',
    'input[type="submit"]',
]

COOKIE_DISMISS_SELECTORS = [
    'button:has-text("Accept")',
    'button:has-text("Accept All")',
    'button:has-text("I agree")',
    'button:has-text("Got it")',
    '[id*="accept" i]',
]


async def dismiss_cookie_banner(page: Page) -> None:
    for selector in COOKIE_DISMISS_SELECTORS:
        try:
            btn = page.locator(selector).first
            if await btn.count() > 0 and await btn.is_visible():
                await btn.click(timeout=3000)
                await human_delay(0.5, 1)
                return
        except Exception:
            log_error(
                "cookie_dismiss_failed",
                f"Failed to dismiss cookie banner with selector: {selector}",
                context="Dismissing cookie banner on Freelancer login page",
            )


async def _fill_first(page: Page, selectors: list[str], value: str) -> bool:
    for selector in selectors:
        locator = page.locator(selector).first
        try:
            if await locator.count() > 0:
                await locator.wait_for(state="visible", timeout=5000)
                await locator.click()
                await locator.fill(value)
                return True
        except Exception:
            log_error(
                "form_fill_failed",
                f"Failed to fill field with selector: {selector}",
                context="Filling login form field on Freelancer",
            )
    return False


async def _click_first(page: Page, selectors: list[str]) -> bool:
    for selector in selectors:
        locator = page.locator(selector).first
        try:
            if await locator.count() > 0:
                await locator.wait_for(state="visible", timeout=5000)
                await locator.click()
                return True
        except Exception:
            log_error(
                "button_click_failed",
                f"Failed to click button with selector: {selector}",
                context="Clicking login submit button on Freelancer",
            )
    return False


async def is_logged_in(page: Page) -> bool:
    url = page.url.lower()

    if "/login" in url:
        return False

    if any(part in url for part in LOGIN_SUCCESS_URL_PARTS):
        return True

    try:
        for selector in EMAIL_SELECTORS[:3]:
            el = page.locator(selector).first
            if await el.count() > 0:
                visible = await el.is_visible()
                if visible:
                    return False
    except Exception:
        log_error(
            "login_check_failed",
            "Failed to check login status via email field presence",
            context="Checking if user is logged in on Freelancer (email field check)",
            page_url=page.url,
        )

    try:
        logout = page.locator(
            'a:has-text("Log out"), button:has-text("Log out"), '
            'a:has-text("Logout"), [href*="logout"], fl-logout, '
            '[data-testid="logout-link"]'
        )
        if await logout.count() > 0:
            return True
    except Exception:
        log_error(
            "login_check_failed",
            "Failed to check login status via logout link",
            context="Checking if user is logged in on Freelancer (logout link check)",
            page_url=page.url,
        )

    try:
        user_menu = page.locator(
            '[class*="UserMenu"], [class*="user-menu"], '
            '[data-testid="user-menu"], fl-avatar, .HeaderUserMenu, '
            '[class*="ProfileMenu"], [class*="profile-menu"], '
            '[class*="AccountMenu"], [data-testid="main-navigation-user-menu"]'
        )
        if await user_menu.count() > 0:
            return True
    except Exception:
        log_error(
            "login_check_failed",
            "Failed to check login status via user menu",
            context="Checking if user is logged in on Freelancer (user menu check)",
            page_url=page.url,
        )

    try:
        profile_link = page.locator(
            'a[href*="/u/"], a[href*="/profile"], a[href*="/users/me"]'
        )
        if await profile_link.count() > 0:
            return True
    except Exception:
        pass

    return False


async def wait_for_login(
    page: Page,
    timeout_seconds: int = 180,
    poll_interval: float = 2.0,
) -> bool:
    """Wait until user is logged in (after auto-fill or manual CAPTCHA/2FA)."""
    attempts = int(timeout_seconds / poll_interval)
    captcha_warned = False

    for i in range(attempts):
        if await is_logged_in(page):
            return True

        content = (await page.content()).lower()
        if "captcha" in content or "recaptcha" in content:
            if not captcha_warned:
                logger.warning(
                    "CAPTCHA detected — complete it in the browser window, then wait..."
                )
                captcha_warned = True

        if i > 0 and i % 15 == 0:
            logger.info("Still waiting for login... (%ds)", int(i * poll_interval))

        await asyncio.sleep(poll_interval)

    return False


async def login(
    page: Page,
    email: str,
    password: str,
    manual_wait_seconds: int = 180,
) -> None:
    logger.info("Navigating to login page")
    await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=90000)
    await human_delay(2, 4)
    await dismiss_cookie_banner(page)

    if await is_logged_in(page):
        logger.info("Already logged in on login page")
        return

    email_ok = await _fill_first(page, EMAIL_SELECTORS, email)
    if not email_ok:
        logger.warning("Auto-fill email failed — log in manually in the browser")
        await _wait_and_raise_if_still_not_logged_in(page, manual_wait_seconds)
        return

    continue_clicked = await _click_first(page, CONTINUE_SELECTORS)
    if continue_clicked:
        logger.info("Clicked Continue/Next after email (two-step login)")
        await human_delay(1, 2)

    password_ok = await _fill_first(page, PASSWORD_SELECTORS, password)
    if not password_ok:
        logger.warning("Auto-fill password failed — log in manually in the browser")
        await _wait_and_raise_if_still_not_logged_in(page, manual_wait_seconds)
        return

    submit_clicked = await _click_first(page, SUBMIT_SELECTORS)
    if not submit_clicked:
        logger.info("No submit button matched — pressing Enter")
        await page.keyboard.press("Enter")
    await human_delay(2, 4)

    await _wait_and_raise_if_still_not_logged_in(page, manual_wait_seconds)


async def _wait_and_raise_if_still_not_logged_in(page: Page, manual_wait_seconds: int) -> None:
    if await wait_for_login(page, timeout_seconds=manual_wait_seconds):
        logger.info("Login successful — %s", page.url)
        return

    screenshot_path = settings.data_path / "login_failed.png"
    await page.screenshot(path=str(screenshot_path))
    log_error(
        "login_failed",
        "Login failed after waiting for manual CAPTCHA/2FA completion",
        context="Waiting for user to complete CAPTCHA/2FA on Freelancer login page",
        page_url=page.url,
        screenshot=str(screenshot_path),
    )
    raise RuntimeError(
        "Login failed. With the browser window open: complete CAPTCHA/2FA, "
        "verify email/password, click Log in, then try again. "
        f"Screenshot saved to {screenshot_path}"
    )


async def _load_stored_email() -> str | None:
    email_path = settings.session_email_path
    if email_path.exists():
        try:
            return email_path.read_text(encoding="utf-8").strip()
        except Exception:
            return None
    return None


async def _save_stored_email(email: str) -> None:
    email_path = settings.session_email_path
    try:
        email_path.write_text(email.strip(), encoding="utf-8")
    except Exception:
        logger.warning("Failed to save session email marker")


async def _stale_session(email: str) -> bool:
    if not settings.session_path.exists():
        return False
    stored = await _load_stored_email()
    if stored and stored.lower().strip() == email.lower().strip():
        return False
    return True


async def _clear_session() -> None:
    session_path = settings.session_path
    email_path = settings.session_email_path
    try:
        if session_path.exists():
            session_path.unlink()
    except Exception:
        logger.warning("Failed to delete session file")
    try:
        if email_path.exists():
            email_path.unlink()
    except Exception:
        logger.warning("Failed to delete session email marker")


async def ensure_logged_in(
    playwright: Playwright,
    email: str,
    password: str,
    headless: bool,
    manual_wait_seconds: int = 180,
) -> tuple[BrowserContext, Page]:
    session_path = settings.session_path

    if await _stale_session(email):
        logger.info("Credentials changed — clearing old session for fresh login")
        await _clear_session()

    browser = await playwright.chromium.launch(
        headless=headless,
        args=["--disable-blink-features=AutomationControlled"],
    )

    context_kwargs: dict = {
        "viewport": {"width": 1366, "height": 768},
        "user_agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        ),
        "locale": "en-IN",
    }

    if session_path.exists():
        context_kwargs["storage_state"] = str(session_path)

    context = await browser.new_context(**context_kwargs)
    page = await context.new_page()

    await page.goto("https://www.freelancer.in/", wait_until="domcontentloaded", timeout=90000)
    await human_delay(2, 3)
    await dismiss_cookie_banner(page)

    if not await is_logged_in(page):
        if session_path.exists():
            logger.info("Session expired — logging in again")
            await _clear_session()
        await login(page, email, password, manual_wait_seconds=manual_wait_seconds)

    await context.storage_state(path=str(session_path))
    await _save_stored_email(email)
    logger.info("Session saved to %s", session_path)
    return context, page
