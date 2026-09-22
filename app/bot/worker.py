import asyncio
import logging
import random
import threading
from datetime import datetime, timezone

from playwright._impl._errors import TargetClosedError
from playwright.async_api import async_playwright

from app.bot.auth import ensure_logged_in
from app.bot.bidder import place_minimum_bid
from app.bot.discovery import fetch_new_projects
from app.database import (
    bids_last_hour_count,
    bids_today_count,
    create_session,
    end_session,
    record_bid,
    record_session_error,
    update_session_bid_counts,
)
from app.error_logger import clear_context, log_error, set_context
from app.schemas import BotSettings

logger = logging.getLogger(__name__)


class BotWorker:
    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._settings: BotSettings | None = None
        self.running = False
        self.dry_run = False
        self.last_error: str | None = None
        self.last_action: str | None = None
        self.last_bid_status: str | None = None
        self.last_bid_project: str | None = None
        self.last_bid_template: str | None = None
        self.projects_found_last_scan = 0
        self._loop: asyncio.AbstractEventLoop | None = None
        self._session_id: int | None = None
        self._browser_context = None

    def start(self, settings: BotSettings) -> None:
        if self.running:
            raise RuntimeError("Bot is already running")
        self._settings = settings
        self.dry_run = settings.dry_run
        self._stop_event.clear()
        self._browser_context = None
        self.last_error = None
        self.last_bid_status = None
        self.last_bid_project = None
        self.last_bid_template = None
        self._session_id = create_session()
        self.running = True
        self._thread = threading.Thread(target=self._run_thread, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self.last_action = "Stopping..."
        if self._session_id is not None:
            end_session(self._session_id, "stopped")
        if self._browser_context is not None and self._loop is not None:
            try:
                asyncio.run_coroutine_threadsafe(
                    self._browser_context.close(), self._loop
                )
            except Exception:
                pass
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(lambda: None)

    def _run_thread(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._run_async())
        except Exception as e:
            self.last_error = str(e)
            logger.exception("Bot worker crashed")
            log_error(
                "worker_crash",
                str(e),
                context="Bot worker thread crashed unexpectedly",
            )
            if self._session_id is not None:
                record_session_error(
                    self._session_id,
                    "worker_crash",
                    str(e),
                    context="bot_worker._run_thread",
                )
                end_session(self._session_id, "crashed")
        finally:
            self.running = False
            self.last_action = "Stopped"
            clear_context()
            self._loop.close()

    async def _run_async(self) -> None:
        settings = self._settings
        if not settings:
            return

        self.last_action = "Starting browser..."
        set_context(action="Starting browser", session_id=self._session_id)
        async with async_playwright() as playwright:
            context = None
            try:
                context, page = await ensure_logged_in(
                    playwright,
                    settings.email,
                    settings.password,
                    settings.headless,
                    manual_wait_seconds=settings.manual_login_wait_seconds,
                )
                self._browser_context = context

                while not self._stop_event.is_set():
                    if self._over_rate_limit(settings):
                        self.last_action = "Rate limit reached — waiting..."
                        set_context(action="Rate limited, waiting")
                        await asyncio.sleep(60)
                        continue

                    try:
                        await page.evaluate("1")
                    except TargetClosedError:
                        logger.error("Browser page died — stopping bot")
                        self.last_error = "Browser closed unexpectedly — restart the bot"
                        self.last_action = "Browser died"
                        if self._session_id is not None:
                            end_session(self._session_id, "crashed")
                        break
                    except Exception:
                        logger.error("Browser page died — stopping bot")
                        self.last_error = "Browser closed unexpectedly — restart the bot"
                        self.last_action = "Browser died"
                        if self._session_id is not None:
                            end_session(self._session_id, "crashed")
                        break

                    self.last_action = "Scanning for projects..."
                    set_context(action="Scanning Freelancer for new projects")
                    try:
                        projects = await fetch_new_projects(
                            page,
                            max_age_days=settings.max_project_age_days,
                            max_proposals=settings.max_proposals,
                            my_skills=settings.my_skills,
                            target_categories=settings.target_categories,
                            stop_check=self._stop_event.is_set,
                        )
                    except TargetClosedError:
                        logger.error("Browser closed during project scan — stopping")
                        self.last_error = "Browser closed unexpectedly during scan — restart the bot"
                        self.last_action = "Browser died"
                        if self._session_id is not None:
                            end_session(self._session_id, "crashed")
                        break
                    self.projects_found_last_scan = len(projects)

                    if not projects:
                        self.last_action = (
                            "No eligible projects (check age/proposal filters or bid sheet for skipped) "
                            "— rescanning in 2–3 min"
                        )
                        await self._interruptible_sleep(120, 180)
                        continue

                    for project in projects:
                        if self._stop_event.is_set():
                            break
                        if self._over_rate_limit(settings):
                            break

                        self.last_action = f"Processing: {project.title[:60]}"
                        self.last_bid_project = project.title[:100]
                        if settings.use_smart_proposals:
                            self.last_bid_template = "smart"
                        elif project.category == "seo":
                            self.last_bid_template = "seo"
                        elif project.category == "social_media":
                            self.last_bid_template = "social_media"
                        elif project.category == "web_dev":
                            self.last_bid_template = "web_dev"
                        else:
                            self.last_bid_template = "generic"

                        set_context(
                            action=f"Processing bid for project: {project.title[:60]}",
                            project_id=project.project_id,
                            project_url=project.url,
                            category=project.category,
                        )

                        if settings.dry_run:
                            record_bid(
                                project_id=project.project_id,
                                title=project.title,
                                url=project.url,
                                category=project.category,
                                status="skipped",
                                error_message="Dry run — bid not placed",
                            )
                            self.last_action = f"Dry run logged: {project.title[:50]}"
                            self.last_bid_status = "skipped (dry run)"
                        else:
                            try:
                                result = await place_minimum_bid(page, project, settings, self._stop_event.is_set)
                            except TargetClosedError:
                                logger.error("Browser closed during bidding — stopping")
                                self.last_error = "Browser closed during bidding — restart the bot"
                                self.last_action = "Browser died"
                                record_bid(
                                    project_id=project.project_id,
                                    title=project.title,
                                    url=project.url,
                                    category=project.category,
                                    status="failed",
                                    error_message="Browser closed during bidding",
                                )
                                break
                            status = "success" if result.success else "failed"
                            if not result.success and result.error_message and "browser" in result.error_message.lower():
                                self.last_error = "Browser died during bidding — stopping"
                                self.last_action = "Browser died"
                                record_bid(
                                    project_id=project.project_id,
                                    title=project.title,
                                    url=project.url,
                                    category=project.category,
                                    status="failed",
                                    bid_amount=result.bid_amount,
                                    currency=result.currency,
                                    error_message=result.error_message,
                                )
                                break
                            record_bid(
                                project_id=project.project_id,
                                title=project.title,
                                url=project.url,
                                category=project.category,
                                status=status,
                                bid_amount=result.bid_amount,
                                currency=result.currency,
                                error_message=result.error_message,
                            )
                            if self._session_id is not None:
                                update_session_bid_counts(self._session_id, result.success)
                                if not result.success and result.error_message:
                                    log_error(
                                        "bid_failed",
                                        result.error_message,
                                        context=f"Placing minimum bid on project '{project.title[:80]}'",
                                        project_id=project.project_id,
                                        page_url=project.url,
                                    )
                                    record_session_error(
                                        self._session_id,
                                        "bid_failed",
                                        result.error_message,
                                        context=project.project_id,
                                    )
                            if not result.success:
                                self.last_error = result.error_message
                            self.last_bid_status = status

                        delay = random.uniform(
                            settings.min_delay_seconds,
                            settings.max_delay_seconds,
                        )
                        self.last_action = f"Waiting {int(delay)}s before next bid..."
                        await self._interruptible_sleep(delay, delay)

                    if not self._stop_event.is_set():
                        self.last_action = "Scan complete — pausing before next scan"
                        await self._interruptible_sleep(60, 120)

            finally:
                if context:
                    try:
                        await context.browser.close()
                    except Exception:
                        pass

    def _over_rate_limit(self, settings: BotSettings) -> bool:
        if bids_last_hour_count() >= settings.max_bids_per_hour:
            return True
        if bids_today_count() >= settings.max_bids_per_day:
            return True
        return False

    async def _interruptible_sleep(self, min_sec: float, max_sec: float) -> None:
        total = random.uniform(min_sec, max_sec) if min_sec != max_sec else min_sec
        elapsed = 0.0
        while elapsed < total and not self._stop_event.is_set():
            await asyncio.sleep(min(1.0, total - elapsed))
            elapsed += 1.0


bot_worker = BotWorker()
