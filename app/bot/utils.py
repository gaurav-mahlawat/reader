import asyncio
import random
import re
from pathlib import Path
from typing import Callable
from urllib.parse import quote_plus

import yaml

from app.config import PROJECT_ROOT

KEYWORDS_PATH = PROJECT_ROOT / "config" / "keywords.yaml"


def load_keywords_config() -> dict:
    if not KEYWORDS_PATH.exists():
        return {"web_dev": [], "social_media": [], "seo": [], "my_skills": []}
    with open(KEYWORDS_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def parse_skills_list(raw: str | list | None) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(s).strip() for s in raw if str(s).strip()]
    return [s.strip() for s in re.split(r"[,;\n]+", str(raw)) if s.strip()]


def default_skills_from_config(config: dict | None = None) -> list[str]:
    config = config or load_keywords_config()
    explicit = parse_skills_list(config.get("my_skills"))
    if explicit:
        return explicit
    merged: list[str] = []
    for key in ("web_dev", "social_media", "seo"):
        merged.extend(config.get(key, []))
    return merged


def build_project_search_urls(skills: list[str]) -> list[str]:
    """Search active projects by skill (not job category pages)."""
    base = "https://www.freelancer.in/search/projects"
    urls: list[str] = []
    seen: set[str] = set()
    for skill in skills:
        q = quote_plus(skill.strip())
        if not q:
            continue
        url = f"{base}?q={q}&projectSort=latest"
        if url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def matches_user_skill(text: str, user_skills: list[str]) -> str | None:
    """Return the first user skill found in project text."""
    lowered = text.lower()
    for skill in sorted(user_skills, key=len, reverse=True):
        sk = skill.lower().strip()
        if sk and sk in lowered:
            return skill
    return None


def skill_to_category(skill: str, config: dict | None = None) -> str:
    config = config or load_keywords_config()
    lowered = skill.lower()
    for category in ("web_dev", "social_media", "seo"):
        for kw in config.get(category, []):
            if kw.lower() in lowered or lowered in kw.lower():
                return category
    cat = match_category(skill, config)
    return cat or "skill_match"


def match_category(text: str, config: dict | None = None) -> str | None:
    config = config or load_keywords_config()
    lowered = text.lower()
    for category in ("web_dev", "social_media", "seo"):
        keywords = config.get(category, [])
        for kw in keywords:
            if kw.lower() in lowered:
                return category
    return None


def extract_project_id(url: str) -> str | None:
    """Freelancer uses slug URLs like /projects/react-js/my-project-name."""
    patterns = [
        r"freelancer\.(?:com|in)/projects/([^?#]+)",
        r"/projects/([^?#]+)",
        r"/projects/[^/]+-(\d+)",
        r"project_id=(\d+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            pid = match.group(1).strip("/")
            if pid and pid not in ("contest", "users"):
                return pid
    return None


def category_from_search_url(search_url: str) -> str | None:
    lowered = search_url.lower()
    if "web-development" in lowered or "website" in lowered or "software" in lowered:
        return "web_dev"
    if "internet-marketing" in lowered or "social" in lowered:
        return "social_media"
    if "seo" in lowered:
        return "seo"
    return None


async def human_delay(min_sec: float, max_sec: float, stop_check: Callable[[], bool] | None = None) -> None:
    total = random.uniform(min_sec, max_sec)
    elapsed = 0.0
    while elapsed < total:
        if stop_check and stop_check():
            return
        remaining = min(1.0, total - elapsed)
        await asyncio.sleep(remaining)
        elapsed += 1.0


async def human_type(page, selector: str, text: str, delay_ms: tuple[int, int] = (100, 250), stop_check: Callable[[], bool] | None = None) -> None:
    locator = page.locator(selector).first
    await locator.click()
    await locator.fill("")
    for char in text:
        if stop_check and stop_check():
            return
        await locator.type(char, delay=random.randint(*delay_ms))


def normalize_url(href: str) -> str:
    if href.startswith("http"):
        return href.split("?")[0].rstrip("/")
    if href.startswith("/"):
        return f"https://www.freelancer.in{href.split('?')[0].rstrip('/')}"
    return href


URL_CATEGORY_MAP = {
    "seo": "seo",
    "keyword-research": "seo",
    "keyword-research-2": "seo",
    "keywords": "seo",
    "link-building": "seo",
    "link-building-2": "seo",
    "backlinks": "seo",
    "content-writing": "seo",
    "article-writing": "seo",
    "articles": "seo",
    "copywriting": "seo",
    "blog-writing": "seo",
    "content-marketing": "seo",
    "content-strategy": "seo",
    "google-analytics": "seo",
    "search-engine-marketing": "seo",
    "search-engine-optimization": "seo",
    "sem": "seo",
    "social-media": "social_media",
    "social-media-marketing": "social_media",
    "social-media-management": "social_media",
    "social-networking": "social_media",
    "facebook-marketing": "social_media",
    "facebook": "social_media",
    "instagram": "social_media",
    "instagram-marketing": "social_media",
    "linkedin": "social_media",
    "tiktok": "social_media",
    "twitter": "social_media",
    "youtube": "social_media",
    "internet-marketing": "social_media",
    "google-ads": "social_media",
    "ppc": "social_media",
    "influencer-marketing": "social_media",
    "content-calendar": "social_media",
    "community-management": "social_media",
    "lead-generation": "social_media",
    "video-services": "social_media",
    "video-editing": "social_media",
    "web-development": "web_dev",
    "website-development": "web_dev",
    "website-design": "web_dev",
    "web-design": "web_dev",
    "website": "web_dev",
    "ui-design": "web_dev",
    "ux-design": "web_dev",
    "ui-ux": "web_dev",
    "graphic-design": "web_dev",
    "logo-design": "web_dev",
    "banner-design": "web_dev",
    "html": "web_dev",
    "html5": "web_dev",
    "css": "web_dev",
    "css3": "web_dev",
    "php": "web_dev",
    "javascript": "web_dev",
    "angular-js": "web_dev",
    "react-js": "web_dev",
    "nextjs": "web_dev",
    "vue-js": "web_dev",
    "node-js": "web_dev",
    "python": "web_dev",
    "django": "web_dev",
    "flask": "web_dev",
    "laravel": "web_dev",
    "wordpress": "web_dev",
    "woocommerce": "web_dev",
    "shopify": "web_dev",
    "shopify-site": "web_dev",
    "shopify-templates": "web_dev",
    "magento": "web_dev",
    "ecommerce": "web_dev",
    "shopping-cart": "web_dev",
    "mobile-app": "web_dev",
    "mobile-app-development": "web_dev",
    "app-development": "web_dev",
    "android": "web_dev",
    "ios": "web_dev",
    "flutter": "web_dev",
    "react-native": "web_dev",
    "software-development": "web_dev",
    "database": "web_dev",
    "database-development": "web_dev",
    "api": "web_dev",
    "api-development": "web_dev",
    "api-integration": "web_dev",
    "full-stack": "web_dev",
    "frontend": "web_dev",
    "backend": "web_dev",
    "web-scraping": "web_dev",
    "data-scraping": "web_dev",
    "scraping": "web_dev",
    "automation": "web_dev",
    "scripting": "web_dev",
    "chrome-extension": "web_dev",
    "plugin": "web_dev",
    "crm": "web_dev",
    "erp": "web_dev",
    "saas": "web_dev",
    "server": "web_dev",
    "hosting": "web_dev",
    "domain": "web_dev",
    "illustrator": "web_dev",
    "photoshop": "web_dev",
    "figma": "web_dev",
    "2d-drawing": "web_dev",
    "3d-modeling": "web_dev",
    "3d-design": "web_dev",
    "animation": "web_dev",
    "2d-animation": "web_dev",
    "3d-animation": "web_dev",
    "wix": "web_dev",
    "webflow": "web_dev",
    "elementor": "web_dev",
    "divi": "web_dev",
    "framer": "web_dev",
    "bubble": "web_dev",
    "adobe-photoshop": "web_dev",
    "adobe-premiere-pro": "web_dev",
    "ai-chatbot": "web_dev",
    "ai-content-writing": "seo",
    "ai-graphic-design": "web_dev",
    "ai-video-editing": "social_media",
    "data-analysis": "web_dev",
    "technical-writing": "seo",
    "packaging-design": "web_dev",
    "elearning": "web_dev",
    "fashion-design": "web_dev",
}


def _extract_path_category_slug(project_url: str) -> str | None:
    match = re.search(r"/projects/([^/?#]+)", project_url, re.IGNORECASE)
    if not match:
        return None
    return match.group(1).lower().strip()


def url_category_matches_target(project_url: str, target_categories: list[str]) -> tuple[bool, str | None, str | None]:
    cat = get_url_category(project_url)
    if cat is None:
        return True, None, None
    slug = _extract_path_category_slug(project_url)
    if cat not in target_categories:
        return False, slug, cat
    return True, None, cat


def get_url_category(project_url: str) -> str | None:
    slug = _extract_path_category_slug(project_url)
    if slug is None:
        return None
    cat = URL_CATEGORY_MAP.get(slug)
    if cat is not None:
        return cat
    url_lower = project_url.lower()
    web_dev_patterns = [
        "website", "web-dev", "web-design", "app-dev", "software", "programming",
        "coding", "frontend", "backend", "fullstack", "mobile-app", "react",
        "angular", "vue", "next", "gatsby", "svelte", "node", "express",
        "django", "laravel", "rails", "aspnet", "wordpress", "shopify",
        "woocommerce", "magento", "prestashop", "custom-cms", "api",
        "rest-api", "graphql", "database", "mysql", "mongodb", "postgresql",
        "firebase", "docker", "kubernetes", "aws", "azure", "devops",
        "blockchain", "smart-contract", "solidity", "web3", "nft",
        "game-dev", "unity", "unreal", "ar-vr", "saas", "crm", "erp",
        "pos", "landing-page", "portfolio", "theme", "plugin", "extension",
        "browser-extension", "chrome-extension", "figma-to-html",
        "psd-to-html", "responsive", "pwa", "single-page-app",
    ]
    seo_patterns = [
        "seo", "keyword", "backlink", "link-build", "on-page", "off-page",
        "technical-seo", "local-seo", "google-ranking", "serp", "sem",
        "content-writ", "article-writ", "blog-writ", "blog-post", "blogging",
        "copywrit", "proofread", "editing", "translation", "transcription",
        "ghost-writ", "product-description", "ebook", "newsletter",
        "email-copy", "sales-copy", "press-release", "resume",
        "business-plan", "grant-writ", "academic-writ", "research",
    ]
    social_media_patterns = [
        "social-media", "social-market", "instagram", "facebook", "tiktok",
        "youtube", "linkedin", "twitter", "pinterest", "snapchat",
        "reddit", "discord", "telegram", "whatsapp", "influencer",
        "content-creat", "video-edit", "video-prod", "photography",
        "videography", "reels", "shorts", "tiktok-video",
        "community-manage", "digital-market", "ppc", "google-ads",
        "facebook-ads", "ad-campaign", "adwords", "bing-ads",
        "email-market", "marketing-automation", "lead-gen",
        "online-market", "affiliate-market", "growth-hack",
    ]
    for pattern in web_dev_patterns:
        if pattern in url_lower:
            return "web_dev"
    for pattern in seo_patterns:
        if pattern in url_lower:
            return "seo"
    for pattern in social_media_patterns:
        if pattern in url_lower:
            return "social_media"
    return None
