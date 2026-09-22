from pydantic import BaseModel, Field, field_validator

from app.bot.utils import parse_skills_list

VALID_CATEGORIES = ["web_dev", "social_media", "seo"]

GENERIC_TEMPLATE = (
    "{greeting} my name is {freelancer_name}.\n\n"
    "{understanding_paragraph}\n\n"
    "{experience_paragraph}\n\n"
    "My approach for this project:\n"
    "{approach_paragraph}\n\n"
    "{specifics_paragraph}\n\n"
    "{question}\n\n"
    "I am available to start right away and would love to discuss this further.\n\n"
    "— {freelancer_name}\n"
    "Skills: {skill_tags}"
)

SEO_TEMPLATE = (
    "{greeting} my name is {freelancer_name}.\n\n"
    "{understanding_paragraph}\n\n"
    "{experience_paragraph}\n\n"
    "My SEO process:\n"
    "{approach_paragraph}\n\n"
    "{specifics_paragraph}\n\n"
    "{question}\n\n"
    "I can start immediately and would love to discuss your goals in more detail.\n\n"
    "— {freelancer_name}\n"
    "Skills: {skill_tags}"
)

SOCIAL_MEDIA_TEMPLATE = (
    "{greeting} my name is {freelancer_name}.\n\n"
    "{understanding_paragraph}\n\n"
    "{experience_paragraph}\n\n"
    "My social media strategy:\n"
    "{approach_paragraph}\n\n"
    "{specifics_paragraph}\n\n"
    "{question}\n\n"
    "I am ready to begin and excited to discuss your vision.\n\n"
    "— {freelancer_name}\n"
    "Skills: {skill_tags}"
)

WEB_DEV_TEMPLATE = (
    "{greeting} my name is {freelancer_name}.\n\n"
    "{understanding_paragraph}\n\n"
    "{experience_paragraph}\n\n"
    "My development process:\n"
    "{approach_paragraph}\n\n"
    "{specifics_paragraph}\n\n"
    "{question}\n\n"
    "I can start immediately and would love to discuss the technical details.\n\n"
    "— {freelancer_name}\n"
    "Skills: {skill_tags}"
)


class BotSettings(BaseModel):
    email: str
    password: str
    freelancer_name: str = Field(
        default="",
        description="Your display name used in proposals (e.g. Gaurav)",
    )
    years_of_experience: int = Field(
        default=3,
        ge=0,
        le=50,
        description="Years of experience shown in proposals",
    )
    target_categories: list[str] = Field(
        default_factory=lambda: ["web_dev", "social_media", "seo"],
        description="Project segments to target this session: web_dev, social_media, seo",
    )
    generic_template: str = Field(default=GENERIC_TEMPLATE)
    seo_template: str = Field(default=SEO_TEMPLATE)
    social_media_template: str = Field(default=SOCIAL_MEDIA_TEMPLATE)
    web_dev_template: str = Field(default=WEB_DEV_TEMPLATE)
    delivery_days: int = Field(default=7, ge=1, le=365)
    min_delay_seconds: int = Field(default=300, ge=60)
    max_delay_seconds: int = Field(default=600, ge=60)
    max_bids_per_hour: int = Field(default=8, ge=1, le=50)
    max_bids_per_day: int = Field(default=40, ge=1, le=200)
    headless: bool = False
    dry_run: bool = False
    manual_login_wait_seconds: int = Field(
        default=180,
        ge=30,
        le=600,
        description="Seconds to wait for CAPTCHA/2FA/manual login in browser",
    )
    max_project_age_days: int = Field(
        default=3,
        ge=1,
        le=14,
        description="Only bid on projects posted within this many days",
    )
    max_proposals: int = Field(
        default=20,
        ge=1,
        le=500,
        description="Skip projects with this many proposals or more",
    )
    my_skills: list[str] = Field(
        default_factory=list,
        description="Your skills — bot searches projects matching these (not job pages)",
    )
    use_smart_proposals: bool = Field(
        default=True,
        description="Use AI-powered project-aware proposals instead of static templates",
    )
    proposal_style: str = Field(
        default="medium",
        description="Proposal verbosity: short, medium, or long",
    )

    @field_validator("target_categories", mode="before")
    @classmethod
    def _parse_target_categories(cls, v):
        if v is None or v == "":
            return ["web_dev", "social_media", "seo"]
        if isinstance(v, str):
            return [c.strip() for c in v.split(",") if c.strip() in VALID_CATEGORIES] or ["web_dev", "social_media", "seo"]
        if isinstance(v, list):
            filtered = [c for c in v if c in VALID_CATEGORIES]
            return filtered or ["web_dev", "social_media", "seo"]
        return ["web_dev", "social_media", "seo"]

    @field_validator("my_skills", mode="before")
    @classmethod
    def _parse_my_skills(cls, v):
        if v is None or v == "":
            return []
        if isinstance(v, str):
            return parse_skills_list(v)
        if isinstance(v, list):
            return parse_skills_list(v)
        return []


class BotStatusResponse(BaseModel):
    running: bool
    dry_run: bool
    bids_today: int
    bids_last_hour: int
    last_error: str | None
    last_action: str | None
    projects_found_last_scan: int
    last_bid_status: str | None
    last_bid_project: str | None
    last_bid_template: str | None


class BidResponse(BaseModel):
    id: int
    project_id: str
    title: str
    url: str
    category: str
    bid_amount: float | None
    currency: str | None
    status: str
    error_message: str | None
    bid_at: str

    @classmethod
    def from_orm_bid(cls, bid) -> "BidResponse":
        return cls(
            id=bid.id,
            project_id=bid.project_id,
            title=bid.title,
            url=bid.url,
            category=bid.category,
            bid_amount=bid.bid_amount,
            currency=bid.currency,
            status=bid.status,
            error_message=bid.error_message,
            bid_at=bid.bid_at.isoformat() if bid.bid_at else "",
        )


class SessionResponse(BaseModel):
    id: int
    start_at: str
    end_at: str | None
    status: str
    total_bids: int
    successful_bids: int
    failed_bids: int
    last_error: str | None

    @classmethod
    def from_orm_session(cls, s) -> "SessionResponse":
        return cls(
            id=s.id,
            start_at=s.start_at.isoformat() if s.start_at else "",
            end_at=s.end_at.isoformat() if s.end_at else None,
            status=s.status,
            total_bids=s.total_bids,
            successful_bids=s.successful_bids,
            failed_bids=s.failed_bids,
            last_error=s.last_error,
        )


class SessionErrorResponse(BaseModel):
    id: int
    session_id: int
    timestamp: str
    error_type: str
    error_message: str
    traceback: str | None
    context: str | None

    @classmethod
    def from_orm_error(cls, e) -> "SessionErrorResponse":
        return cls(
            id=e.id,
            session_id=e.session_id,
            timestamp=e.timestamp.isoformat() if e.timestamp else "",
            error_type=e.error_type,
            error_message=e.error_message,
            traceback=e.traceback,
            context=e.context,
        )
