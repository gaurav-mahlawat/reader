import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from app.auth import TOKEN_TTL_SECONDS, check_credentials, make_token, verify_token
from app.database import (
    ensure_db,
    export_bids_csv,
    list_bids,
    list_session_errors,
    list_sessions,
)
from app.error_logger import read_errors
from app.schemas import (
    BidResponse,
    BotSettings,
    BotStatusResponse,
    SessionErrorResponse,
    SessionResponse,
)
from app.bot.worker import bot_worker
from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_db()
    yield
    if bot_worker.running:
        bot_worker.stop()


app = FastAPI(title="Reader", lifespan=lifespan)

PUBLIC_PATHS = {"/login", "/logout"}


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if not settings.auth_enabled:
        return await call_next(request)
    path = request.url.path
    if path in PUBLIC_PATHS or path.startswith("/static"):
        return await call_next(request)
    token = request.cookies.get("reader_session")
    if token and verify_token(token):
        return await call_next(request)
    if path.startswith("/api"):
        return JSONResponse(status_code=401, content={"detail": "Authentication required"})
    return RedirectResponse(url="/login", status_code=307)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html")


@app.post("/login")
async def login_submit(request: Request):
    form = await request.form()
    username = str(form.get("username", ""))
    password = str(form.get("password", ""))
    if check_credentials(username, password):
        token = make_token(username)
        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie(
            "reader_session",
            token,
            max_age=TOKEN_TTL_SECONDS,
            httponly=True,
            samesite="lax",
            secure=request.url.scheme == "https",
        )
        return response
    return templates.TemplateResponse(
        request,
        "login.html",
        {"error": "Invalid username or password"},
        status_code=401,
    )


@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("reader_session")
    return response


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {"headless_default": settings.headless_default},
    )


@app.post("/api/bot/start")
async def start_bot(settings: BotSettings):
    if bot_worker.running:
        raise HTTPException(status_code=400, detail="Bot is already running")
    if settings.min_delay_seconds > settings.max_delay_seconds:
        raise HTTPException(
            status_code=400,
            detail="min_delay_seconds must be <= max_delay_seconds",
        )
    try:
        bot_worker.start(settings)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"ok": True, "message": "Bot started"}


@app.post("/api/bot/stop")
async def stop_bot():
    bot_worker.stop()
    return {"ok": True, "message": "Stop requested"}


@app.get("/api/bot/status", response_model=BotStatusResponse)
async def bot_status():
    from app.database import bids_last_hour_count, bids_today_count

    return BotStatusResponse(
        running=bot_worker.running,
        dry_run=bot_worker.dry_run,
        bids_today=bids_today_count(),
        bids_last_hour=bids_last_hour_count(),
        last_error=bot_worker.last_error,
        last_action=bot_worker.last_action,
        projects_found_last_scan=bot_worker.projects_found_last_scan,
        last_bid_status=bot_worker.last_bid_status,
        last_bid_project=bot_worker.last_bid_project,
        last_bid_template=bot_worker.last_bid_template,
    )


@app.get("/api/bids")
async def get_bids():
    bids = list_bids()
    return [BidResponse.from_orm_bid(b) for b in bids]


@app.get("/api/bids/export")
async def export_bids():
    csv_content = export_bids_csv()
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=bids_export.csv"},
    )


@app.get("/api/sessions")
async def get_sessions():
    sessions = list_sessions()
    return [SessionResponse.from_orm_session(s) for s in sessions]


@app.get("/api/sessions/{session_id}/errors")
async def get_session_errors(session_id: int):
    errors = list_session_errors(session_id)
    return [SessionErrorResponse.from_orm_error(e) for e in errors]


@app.get("/api/errors")
async def get_all_errors():
    errors = list_session_errors()
    return [SessionErrorResponse.from_orm_error(e) for e in errors]


@app.get("/api/errors/file")
async def get_file_errors():
    return read_errors(limit=100)
