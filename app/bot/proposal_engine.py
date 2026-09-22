import logging
import re
import random
from dataclasses import dataclass, field

from app.bot.discovery import ProjectCandidate

logger = logging.getLogger(__name__)


@dataclass
class ProjectAnalysis:
    deliverables: list[str] = field(default_factory=list)
    technologies: list[str] = field(default_factory=list)
    platforms: list[str] = field(default_factory=list)
    constraints: dict[str, str] = field(default_factory=dict)
    client_type: str = "unknown"
    tone: str = "professional"
    key_phrases: list[str] = field(default_factory=list)
    seo_services: list[str] = field(default_factory=list)
    content_types: list[str] = field(default_factory=list)
    niche: str = ""
    target_keywords: list[str] = field(default_factory=list)
    goals: list[str] = field(default_factory=list)


TECH_DICTIONARY = {
    "react": "React", "reactjs": "React", "react.js": "React",
    "angular": "Angular", "vue": "Vue.js", "vuejs": "Vue.js",
    "next": "Next.js", "nextjs": "Next.js", "next.js": "Next.js",
    "node": "Node.js", "nodejs": "Node.js", "express": "Express",
    "django": "Django", "flask": "Flask", "fastapi": "FastAPI",
    "laravel": "Laravel", "symfony": "Symfony",
    "wordpress": "WordPress", "woocommerce": "WooCommerce", "joomla": "Joomla",
    "shopify": "Shopify", "magento": "Magento",
    "php": "PHP", "python": "Python", "javascript": "JavaScript",
    "typescript": "TypeScript", "java": "Java", "c#": "C#", "c++": "C++",
    "ruby": "Ruby", "rails": "Ruby on Rails", "go": "Go", "golang": "Go",
    "swift": "Swift", "kotlin": "Kotlin", "flutter": "Flutter",
    "react native": "React Native", "ionic": "Ionic",
    "mongodb": "MongoDB", "mysql": "MySQL", "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL", "sqlite": "SQLite", "redis": "Redis",
    "firebase": "Firebase", "supabase": "Supabase",
    "aws": "AWS", "azure": "Azure", "gcp": "GCP", "google cloud": "GCP",
    "docker": "Docker", "kubernetes": "Kubernetes", "k8s": "Kubernetes",
    "graphql": "GraphQL", "rest": "REST API", "restful": "REST API",
    "api": "API", "stripe": "Stripe", "paypal": "PayPal",
    "tailwind": "Tailwind CSS", "bootstrap": "Bootstrap",
    "sass": "Sass/SCSS", "scss": "Sass/SCSS", "css": "CSS", "html": "HTML",
    "figma": "Figma", "xd": "Adobe XD", "sketch": "Sketch",
    "blockchain": "Blockchain", "web3": "Web3", "solidity": "Solidity",
    "machine learning": "Machine Learning", "ai": "AI", "artificial intelligence": "AI",
    "nlp": "NLP", "chatbot": "Chatbot", "chatgpt": "ChatGPT",
    "web scraping": "Web Scraping", "scraping": "Web Scraping",
    "data scraping": "Data Scraping", "selenium": "Selenium",
    "puppeteer": "Puppeteer", "playwright": "Playwright",
    "excel": "Excel", "power bi": "Power BI", "tableau": "Tableau",
    "etl": "ETL", "data pipeline": "Data Pipeline",
    "photoshop": "Photoshop", "illustrator": "Illustrator",
    "canva": "Canva", "premiere": "Premiere Pro",
    "after effects": "After Effects",
    "crm": "CRM", "salesforce": "Salesforce", "hubspot": "HubSpot",
    "zapier": "Zapier", "make.com": "Make.com",
    "elementor": "Elementor", "divi": "Divi", "wpbakery": "WP Bakery",
    "wix": "Wix", "squarespace": "Squarespace", "webflow": "Webflow",
    "bubble": "Bubble.io", "bubble.io": "Bubble.io",
}

PLATFORM_DICTIONARY = {
    "instagram": "Instagram", "facebook": "Facebook", "linkedin": "LinkedIn",
    "twitter": "Twitter/X", "x.com": "Twitter/X", "tiktok": "TikTok",
    "youtube": "YouTube", "pinterest": "Pinterest", "snapchat": "Snapchat",
    "reddit": "Reddit", "discord": "Discord", "whatsapp": "WhatsApp",
    "telegram": "Telegram", "threads": "Threads",
    "shopify": "Shopify", "woocommerce": "WooCommerce",
    "amazon": "Amazon", "ebay": "eBay", "etsy": "Etsy",
    "wordpress": "WordPress", "wix": "Wix", "squarespace": "Squarespace",
    "webflow": "Webflow", "bubble": "Bubble.io",
    "google ads": "Google Ads", "facebook ads": "Facebook Ads",
    "google my business": "Google Business Profile",
}

SEO_SERVICE_DICT = {
    "backlink": "backlink building", "backlinks": "backlink building",
    "link building": "backlink building", "link-building": "backlink building",
    "linkbuilder": "backlink building",
    "guest post": "guest posting", "guest posts": "guest posting", "guest posting": "guest posting",
    "niche edit": "niche edits", "niche edits": "niche edits",
    "outreach": "link outreach",
    "keyword research": "keyword research", "keyword-research": "keyword research",
    "keyword analysis": "keyword research", "keyword mapping": "keyword research",
    "keyword strategy": "keyword research",
    "on-page seo": "on-page SEO", "on-page": "on-page SEO", "on page": "on-page SEO",
    "onpage": "on-page SEO", "on page seo": "on-page SEO",
    "off-page seo": "off-page SEO", "off-page": "off-page SEO", "off page": "off-page SEO",
    "offpage": "off-page SEO", "off page seo": "off-page SEO",
    "technical seo": "technical SEO audit", "technical audit": "technical SEO audit",
    "site audit": "technical SEO audit", "seo audit": "technical SEO audit",
    "crawl": "technical SEO audit", "site speed": "technical SEO audit",
    "core web vitals": "technical SEO audit", "core web vital": "technical SEO audit",
    "local seo": "local SEO", "local-seo": "local SEO",
    "gmb": "local SEO", "google my business": "local SEO",
    "citation": "local SEO", "citations": "local SEO",
    "content writing": "content writing", "content-writing": "content writing",
    "seo content": "content writing", "content writer": "content writing",
    "article writing": "article writing", "article-writing": "article writing",
    "article writer": "article writing",
    "blog writing": "blog writing", "blog-writing": "blog writing",
    "blog post": "blog writing", "blog posts": "blog writing", "blogging": "blog writing",
    "blog writer": "blog writing",
    "copywriting": "copywriting", "copy writer": "copywriting", "sales copy": "copywriting",
    "product description": "product descriptions",
    "product descriptions": "product descriptions",
    "press release": "press releases", "press releases": "press releases",
    "ebook": "ebook writing", "ebooks": "ebook writing",
    "newsletter": "newsletter writing", "newsletters": "newsletter writing",
    "serp": "SERP analysis", "ranking": "rank tracking", "rankings": "rank tracking",
    "google ranking": "rank tracking", "rank tracking": "rank tracking",
    "analytics": "analytics & reporting", "google analytics": "analytics & reporting",
    "search console": "analytics & reporting",
    "ecommerce seo": "ecommerce SEO", "amazon seo": "ecommerce SEO",
    "shopify seo": "ecommerce SEO", "etsy seo": "ecommerce SEO",
    "youtube seo": "YouTube SEO", "video seo": "YouTube SEO",
    "sem": "SEM / paid search", "ppc": "SEM / paid search",
    "google ads": "SEM / paid search", "adwords": "SEM / paid search",
    "smo": "social media optimization",
    "guest blogging": "guest posting", "guest blog": "guest posting",
}

CONTENT_TYPE_DICT = {
    "blog post": "blog posts", "blog posts": "blog posts", "blogs": "blog posts",
    "article": "articles", "articles": "articles",
    "product description": "product descriptions", "product descriptions": "product descriptions",
    "landing page": "landing pages", "landing pages": "landing pages",
    "service page": "service pages", "web copy": "website copy",
    "email": "email copy", "email copy": "email copy", "newsletter": "newsletters",
    "newsletters": "newsletters",
    "social media post": "social media posts", "social media posts": "social media posts",
    "social media caption": "social media captions", "captions": "social media captions",
    "press release": "press releases", "press releases": "press releases",
    "white paper": "white papers", "whitepaper": "white papers", "white papers": "white papers",
    "case study": "case studies", "case studies": "case studies",
    "ebook": "ebooks", "ebooks": "ebooks",
    "video script": "video scripts", "scripts": "scripts",
    "ad copy": "ad copy", "meta description": "meta descriptions",
    "meta descriptions": "meta descriptions",
    "meta title": "meta titles", "meta titles": "meta titles",
    "headline": "headlines", "headlines": "headlines",
    "reels": "Instagram Reels", "short": "short-form videos",
    "short form": "short-form videos", "shorts": "short-form videos",
}

SEO_TOOL_DICT = {
    "ahrefs": "Ahrefs", "semrush": "Semrush", "moz": "Moz",
    "google search console": "Google Search Console", "search console": "Google Search Console",
    "google analytics": "Google Analytics", "screaming frog": "Screaming Frog",
    "ubersuggest": "Ubersuggest", "spyfu": "SpyFu",
    "keyword planner": "Keyword Planner", "serpstat": "Serpstat",
}

NICHE_PATTERNS = [
    r"(?:in|for|about)\s+(?:the\s+)?([\w\s]{3,40}?(?:industry|niche|sector|market|business|space|field|vertical))",
    r"(?:travel|health|fashion|finance|tech|real estate|education|fitness|food|beauty|legal|medical|sports|gaming|automotive|home|pet|wedding|music|photography)\s*(?:industry|niche|business|blog|website|store|agency|company)?",
    r"(?:for\s+(?:a|an|my|our)\s+)([\w\s]{3,30}?(?:business|company|store|shop|brand|agency|blog|website|startup|firm|clinic|restaurant|hotel|salon|gym|school|studio|practice))",
    r"(?:for\s+(?:a|an|my|our|the)\s+)([\w\s]{3,25}?(?:clinic|practice|studio|agency|store|shop|blog|website|business|company|brand))",
]

GOAL_PATTERNS = [
    (r"(?:increase|boost|grow|improve)\s+(?:my|our|the)\s+(?:organic\s+)?traffic", "increase organic traffic"),
    (r"(?:rank\s+(?:in|on|higher)|top\s+ranking|first\s+page|page\s+1)", "improve search rankings"),
    (r"(?:generate|get|drive)\s+(?:more\s+)?leads", "generate leads"),
    (r"(?:increase|boost|grow)\s+(?:sales|revenue|conversion)", "increase sales/revenue"),
    (r"(?:build|improve|increase)\s+(?:brand\s+)?awareness", "build brand awareness"),
    (r"(?:get\s+)?more\s+(?:customers|clients|users)", "acquire more customers"),
    (r"(?:improve|optimize|fix)\s+(?:site\s+)?speed", "improve site speed"),
    (r"(?:fix|resolve|address)\s+(?:technical\s+)?issues", "fix technical issues"),
    (r"(?:outrank|beat|compete\s+with)", "outrank competitors"),
    (r"authority|domain\s+authority|da\s+score", "build domain authority"),
]

DELIVERABLE_PATTERNS = [
    r"(?:need|want|looking for|require|build|create|develop|design|set up|migrate|redesign|revamp|fix|update|implement|integrate|launch|deploy)\s+(?:an?\s+)?([\w\s\-]{3,60}?(?:website|app|application|dashboard|store|bot|plugin|theme|landing page|ecommerce|portal|api|integration|database|backend|frontend|mobile app|web app|crm|extension|widget|script|tool|system|platform|module|component|template|automation|workflow|chatbot|crawler|scraper|scanner|payment system|checkout|cart|membership|login|authentication|search|filter|form|calendar|scheduler|gallery|slider|custom post type|newsletter|analytics|reporting|tracking))",
    r"(?:build|create|develop|design|set up)\s+(?:an?\s+)?([\w\s\-]{3,60}?(?:with|using)\s+[\w\s,]+)",
    r"(?:i\s+(?:need|want|have|require|am looking))\s+(?:an?\s+)?([\w\s\-]{5,100}?(?:website|app|application|software|system|platform|store|site|page|blog|shop|service))",
]

TONE_KEYWORDS = {
    "urgent": ["urgent", "asap", "immediately", "as soon as possible", "right away", "emergency", "today", "tomorrow", "quick"],
    "casual": ["bro", "dude", "mate", "cool", "awesome"],
    "detailed": ["specifically", "exactly", "precisely", "in detail", "detailed"],
}

CLIENT_TYPE_PATTERNS = {
    "agency": ["my client", "our client", "client of", "agency", "we are an agency"],
    "business_owner": ["my business", "my company", "our business", "our company", "my store", "my shop", "my brand", "small business"],
    "startup": ["startup", "mvp", "prototype", "poc", "proof of concept", "seed", "pre-seed", "venture"],
    "individual": ["i need", "i want", "i am looking", "i have", "i'm looking", "personal project", "my blog", "my portfolio"],
}


def analyze_project(project: ProjectCandidate) -> ProjectAnalysis:
    text = " ".join([
        project.title,
        project.description or "",
        " ".join(project.skill_tags or []),
    ]).lower()

    analysis = ProjectAnalysis()

    analysis.technologies = _extract_technologies(text)
    analysis.platforms = _extract_platforms(text)
    analysis.deliverables = _extract_deliverables(text)
    analysis.constraints = _extract_constraints(text)
    analysis.tone = _detect_tone(text)
    analysis.client_type = _detect_client_type(text)
    analysis.key_phrases = _extract_key_phrases(project)

    if project.category in ("seo", "skill_match"):
        analysis.seo_services = _extract_seo_services(text)
        analysis.content_types = _extract_content_types(text)
        analysis.target_keywords = _extract_target_keywords(text)
        analysis.goals = _extract_goals(text)
    analysis.niche = _extract_niche(text, project.title)

    return analysis


def _extract_technologies(text: str) -> list[str]:
    found: list[tuple[int, str]] = []
    seen = set()
    for key, label in TECH_DICTIONARY.items():
        pattern = re.compile(r'\b' + re.escape(key) + r'\b', re.IGNORECASE)
        if pattern.search(text):
            found.append((len(key), label))
    found.sort(key=lambda x: x[0], reverse=True)
    result = []
    for _, label in found:
        if label.lower() not in seen:
            seen.add(label.lower())
            result.append(label)
    return result[:10]


def _extract_platforms(text: str) -> list[str]:
    found = []
    seen = set()
    for key, label in PLATFORM_DICTIONARY.items():
        if key in text:
            found.append((len(key), label))
    found.sort(key=lambda x: x[0], reverse=True)
    result = []
    for _, label in found:
        if label.lower() not in seen:
            seen.add(label.lower())
            result.append(label)
    return result[:8]


def _extract_deliverables(text: str) -> list[str]:
    deliverables = []
    for pattern in DELIVERABLE_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            item = match.group(1).strip()
            item = re.sub(r"\s+", " ", item)
            if 3 < len(item) < 50 and item not in deliverables:
                deliverables.append(item)
    return deliverables[:5]


def _extract_seo_services(text: str) -> list[str]:
    found: list[tuple[int, str]] = []
    seen = set()
    for key, label in SEO_SERVICE_DICT.items():
        if key in text:
            found.append((len(key), label))
    found.sort(key=lambda x: x[0], reverse=True)
    result = []
    for _, label in found:
        if label not in seen:
            seen.add(label)
            result.append(label)
    return result[:6]


def _extract_content_types(text: str) -> list[str]:
    found = []
    seen = set()
    for key, label in CONTENT_TYPE_DICT.items():
        if key in text:
            found.append((len(key), label))
    found.sort(key=lambda x: x[0], reverse=True)
    result = []
    for _, label in found:
        if label not in seen:
            seen.add(label)
            result.append(label)
    return result[:4]


def _extract_niche(text: str, title: str) -> str:
    combined = (title + " " + text).lower()
    for pattern in NICHE_PATTERNS:
        m = re.search(pattern, combined, re.IGNORECASE)
        if m:
            niche = m.group(0).strip()
            niche = re.sub(r'^\s*(in|for|about)\s+(the\s+)?', '', niche, flags=re.IGNORECASE)
            niche = re.sub(r'^\s*(my|our)\s+', '', niche, flags=re.IGNORECASE)
            if len(niche) > 2 and len(niche) < 50:
                return niche
    niche_words = [
        "travel", "health", "fashion", "finance", "tech", "real estate",
        "education", "fitness", "food", "beauty", "legal", "medical",
        "sports", "gaming", "automotive", "home decor", "pet", "wedding",
        "music", "photography", "lifestyle", "parenting", "diy", "outdoor",
        "sustainability", "crypto", "saas", "b2b", "ecommerce", "retail",
        "hospitality", "construction", "insurance", "logistics", "manufacturing",
        "dental", "clinic", "healthcare", "pharmacy", "veterinary",
        "restaurant", "coffee", "hotel", "spa", "salon", "barber",
        "yoga", "meditation", "organic", "vegan", "luxury", "jewelry",
        "furniture", "interior design", "architecture", "landscaping",
        "cleaning", "plumbing", "electrician", "hvac", "roofing",
        "tutoring", "coaching", "consulting", "accounting", "bookkeeping",
        "recruitment", "staffing", "event planning", "travel agency",
        "car rental", "taxi", "delivery", "catering", "bakery",
        "cannabis", "cbd", "supplements", "skincare", "hair care",
        "baby", "kids", "senior", "nonprofit", "church", "religious",
        "publishing", "printing", "signage", "marketing agency",
        "web design agency", "development agency", "creative agency",
    ]
    for word in niche_words:
        if word in combined:
            return word
    return ""


def _extract_target_keywords(text: str) -> list[str]:
    kw_match = re.findall(
        r'(?:keyword|target|rank\s+for|ranking\s+for)[:\s]+([\w\s,]+?)(?:\.|$|\n)',
        text, re.IGNORECASE,
    )
    if kw_match:
        keywords = []
        for match in kw_match:
            keywords.extend([k.strip() for k in re.split(r'[,;]', match) if len(k.strip()) > 1])
        return keywords[:5]
    quoted = re.findall(r'"([^"]{3,60})"', text)
    if quoted and len(quoted) <= 8:
        return [q for q in quoted if len(q.split()) <= 5][:5]
    return []


def _extract_goals(text: str) -> list[str]:
    goals = []
    for pattern, label in GOAL_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            goals.append(label)
    return goals[:3]


def _extract_constraints(text: str) -> dict[str, str]:
    constraints = {}

    time_match = re.search(
        r'(\d+[\s-]*(?:day|week|month|hour)s?)\s*(?:timeline|deadline|delivery|time)',
        text, re.IGNORECASE
    )
    if time_match:
        constraints["timeline"] = time_match.group(0).strip()
    else:
        time2 = re.search(
            r'(?:timeline|deadline|delivery|need it in)\s*:?\s*(\d+[\s-]*(?:day|week|month|hour)s?)',
            text, re.IGNORECASE
        )
        if time2:
            constraints["timeline"] = time2.group(0).strip()

    urgent_match = re.search(r'(urgent|asap|immediately|as soon as possible)', text, re.IGNORECASE)
    if urgent_match:
        constraints["urgency"] = urgent_match.group(1)

    seo_match = re.search(r'(seo[\s-]friendly|seo[\s-]optimized)', text, re.IGNORECASE)
    if seo_match:
        constraints["special"] = seo_match.group(1)

    responsive_match = re.search(r'(responsive|mobile[\s-]friendly|mobile[\s-]responsive)', text, re.IGNORECASE)
    if responsive_match:
        constraints["responsive"] = responsive_match.group(1)

    return constraints


def _detect_tone(text: str) -> str:
    scores = {}
    for tone, keywords in TONE_KEYWORDS.items():
        scores[tone] = sum(1 for kw in keywords if kw in text)
    if scores.get("urgent", 0) >= 2:
        return "urgent"
    if scores.get("casual", 0) >= 1:
        return "casual"
    if scores.get("detailed", 0) >= 1:
        return "detailed"
    return "professional"


def _detect_client_type(text: str) -> str:
    scores = {}
    for ctype, keywords in CLIENT_TYPE_PATTERNS.items():
        scores[ctype] = sum(1 for kw in keywords if kw in text)
    if scores:
        best = max(scores, key=lambda k: scores[k])
        if scores[best] > 0:
            return best
    return "unknown"


def _extract_key_phrases(project: ProjectCandidate) -> list[str]:
    desc = project.description or ""
    sentences = re.split(r'[.!?]+', desc)
    phrases = []
    for s in sentences:
        s = s.strip()
        if len(s) > 20 and len(s) < 200:
            has_action = any(
                kw in s.lower()
                for kw in ["need", "want", "looking", "build", "create", "require", "develop", "design", "have"]
            )
            if has_action:
                phrases.append(s)
    return phrases[:3]


def generate_understanding(project: ProjectCandidate, analysis: ProjectAnalysis) -> str:
    title = project.title.strip()

    seo = analysis.seo_services
    niche = analysis.niche
    goals = analysis.goals
    tech = analysis.technologies
    deliverables = analysis.deliverables
    content = analysis.content_types

    if seo:
        service_text = _join_readable(seo[:3])
        if niche and goals:
            first_goal = goals[0]
            return (
                f"I read through your project \"{title}\" carefully. "
                f"I understand you need {service_text} for your {niche} business, "
                f"and your primary goal is to {first_goal}. "
                f"I have a clear strategy mapped out for exactly this type of project."
            )
        if niche:
            return (
                f"I went through your project \"{title}\" in detail. "
                f"You're looking for {service_text} in the {niche} space — "
                f"I have extensive experience delivering exactly this combination "
                f"and know what works in this niche."
            )
        if content:
            content_text = _join_readable(content[:2])
            return (
                f"I reviewed \"{title}\" thoroughly. "
                f"You need {service_text} — specifically {content_text}. "
                f"I have written hundreds of pieces in this format and understand "
                f"what makes content rank and convert."
            )
        return (
            f"I read your project \"{title}\" carefully. "
            f"You need {service_text} and I have a clear understanding of "
            f"what's required to deliver outstanding results."
        )

    if tech and deliverables:
        tech_str = ", ".join(tech[:3])
        del_str = ", ".join(deliverables[:2])
        if niche:
            return (
                f"I went through \"{title}\" in detail. "
                f"You're building {del_str} for the {niche} space using {tech_str} — "
                f"I have built similar solutions and know the nuances of this domain."
            )
        return (
            f"I went through your project \"{title}\" in detail. "
            f"You're looking for {del_str} using {tech_str} - "
            f"I have strong experience with this exact stack."
        )
    if tech:
        if niche:
            return (
                f"I read \"{title}\" thoroughly. "
                f"I see you're working with {', '.join(tech[:3])} for a {niche} project, "
                f"and I specialize in building solutions for this specific tech stack."
            )
        return (
            f"I read your project \"{title}\" thoroughly. "
            f"I see you're working with {', '.join(tech[:3])}, "
            f"and I specialize in building solutions with these technologies."
        )
    if deliverables:
        if niche:
            return (
                f"I reviewed \"{title}\" carefully. "
                f"You need {', '.join(deliverables[:2])} for the {niche} industry, "
                f"and I have delivered multiple successful projects in this exact area."
            )
        return (
            f"I reviewed \"{title}\" carefully. "
            f"You need {', '.join(deliverables[:2])}, and I have delivered "
            f"multiple similar projects successfully."
        )

    key_phrase = ""
    if analysis.key_phrases:
        kp = analysis.key_phrases[0]
        kp = re.sub(r'^\s*(i\s+(?:need|want|am looking|require|have|for|looking for|looking to))\s+', '', kp, flags=re.IGNORECASE)
        kp = re.sub(r'^\s*(for|to|a|an|the)\s+', '', kp, flags=re.IGNORECASE)
        kp = kp.strip().rstrip('.')
        if kp and len(kp) > 10:
            kp = kp[0].lower() + kp[1:]
            kp = re.sub(r'^\s*(a|an|the|for|to)\s+', '', kp, flags=re.IGNORECASE)
            if kp and len(kp) > 15:
                return (
                    f"I read through your project \"{title}\" carefully. "
                    f"I understand you need {kp} — "
                    f"and I know exactly how to approach this."
                )

    if niche:
        return (
            f"I read through your project \"{title}\" and I understand "
            f"what you need for your {niche} business. "
            f"I am confident I can deliver exactly what you're looking for."
        )

    return (
        f"I read through your project \"{title}\" and I have a clear "
        f"understanding of what you need. I am confident I can deliver "
        f"exactly what you're looking for."
    )


def generate_experience(analysis: ProjectAnalysis, category: str, years: int) -> str:
    tech = analysis.technologies
    seo = analysis.seo_services
    niche = analysis.niche

    if category == "seo":
        if seo:
            service_text = _join_readable(seo[:2])
            if "backlink" in service_text or "guest post" in service_text:
                if niche:
                    return (
                        f"With {years}+ years of experience in link building, "
                        f"I have secured high-DA backlinks for 50+ sites in the {niche} niche. "
                        f"I focus on white-hat outreach and avoid spammy techniques that can harm rankings."
                    )
                return (
                    f"With {years}+ years of experience in SEO and link building, "
                        f"I have built thousands of quality backlinks through guest posting, niche edits, and "
                        f"strategic outreach. I focus on white-hat techniques that deliver real ranking improvements."
                )
            if "content writing" in service_text or "article" in service_text or "blog" in service_text:
                if niche:
                    return (
                        f"With {years}+ years of experience writing SEO-optimized content, "
                        f"I have created hundreds of articles that rank on page 1 — "
                        f"with extensive work in the {niche} industry. "
                        f"I write content that both search engines and readers love."
                    )
                return (
                    f"With {years}+ years in SEO content writing, I have produced "
                    f"500+ articles and blog posts that consistently rank in the top 3. "
                    f"I do thorough keyword research before writing, ensuring every piece "
                    f"has the best chance to rank."
                )
            if "audit" in service_text or "technical" in service_text:
                if niche:
                    return (
                        f"With {years}+ years performing technical SEO audits, "
                        f"I have helped {niche} businesses fix crawl errors, improve "
                        f"Core Web Vitals, and boost organic traffic by 40–200%. "
                        f"I use Screaming Frog, Ahrefs, and Search Console for comprehensive audits."
                    )
                return (
                    f"With {years}+ years in technical SEO, I have performed "
                    f"deep-dive audits for 30+ sites, identifying and fixing issues "
                    f"that directly improved crawl efficiency and rankings. "
                    f"I know exactly what Google looks for in 2026."
                )
            if "keyword research" in service_text:
                if niche:
                    return (
                        f"With {years}+ years in SEO, I have done keyword research "
                        f"for dozens of {niche} businesses, identifying high-volume"
                        f", low-competition keywords that drove measurable traffic growth. "
                        f"I use Ahrefs and Semrush for data-driven keyword mapping."
                    )
                return (
                    f"With {years}+ years in SEO, I specialize in keyword research "
                    f"and competitive analysis. I identify untapped keyword opportunities "
                    f"that your competitors are missing, giving you a real advantage."
                )
            if "local seo" in service_text or "local" in service_text:
                return (
                    f"With {years}+ years in local SEO, I have helped 20+ local "
                    f"businesses rank in the Google Maps 3-pack. I optimize GMB profiles, "
                    f"build citations, and generate reviews that drive local visibility."
                )
            if "ecommerce" in service_text:
                if niche:
                    return (
                        f"With {years}+ years in ecommerce SEO for {niche} stores, "
                        f"I have optimized product pages, category structures, and "
                        f"technical elements that boosted organic revenue by 30–80%."
                    )
                return (
                    f"With {years}+ years in ecommerce SEO, I have optimized Shopify, "
                    f"WooCommerce and Magento stores for organic growth. I understand "
                    f"product schema, faceted navigation, and ecommerce content strategy."
                )
            if "social media optimization" in service_text:
                return (
                    f"With {years}+ years in digital marketing, I combine SEO with "
                    f"social media optimization to create a unified organic growth strategy. "
                    f"I have grown brand presence across search and social simultaneously."
                )

        if niche:
            return (
                f"With {years}+ years in SEO, I have helped {niche} businesses "
                f"increase their organic traffic through data-driven strategies. "
                f"I focus on sustainable white-hat techniques that deliver lasting results."
            )
        return (
            f"With {years}+ years in SEO, I have helped businesses increase "
            f"their organic traffic significantly through data-driven strategies. "
            f"I focus on sustainable white-hat techniques that deliver lasting results."
        )

    if category == "social_media":
        platforms_str = ", ".join(analysis.platforms[:3]) if analysis.platforms else "major platforms"
        if niche:
            return (
                f"With {years}+ years in social media marketing, I have managed "
                f"campaigns for {niche} brands across {platforms_str} — consistently "
                f"exceeding engagement and growth targets."
            )
        return (
            f"With {years}+ years in social media marketing, I have managed "
            f"campaigns across {platforms_str} that consistently exceeded "
            f"engagement and growth targets for my clients."
        )

    if tech:
        tech_str = ", ".join(tech[:3])
        if niche:
            return (
                f"With {years}+ years of experience specializing in {tech_str}, "
                f"I have delivered several {niche} projects that are live and performing well. "
                f"I know the common pitfalls and how to avoid them."
            )
        return (
            f"With {years}+ years of experience specializing in {tech_str}, "
            f"I have delivered several similar projects that are live and performing well. "
            f"I know the common pitfalls and how to avoid them."
        )

    if category == "web_dev":
        if niche:
            return (
                f"With {years}+ years in web development, I have built and deployed "
                f"dozens of applications across different industries — including {niche}. "
                f"I write clean, maintainable code and focus on performance."
            )
        return (
            f"With {years}+ years in web development, I have built and deployed "
            f"dozens of web applications across different industries. "
            f"I write clean, maintainable code and focus on performance."
        )

    return (
        f"With {years}+ years of professional experience, I have successfully "
        f"completed projects similar to yours across various industries. "
        f"I bring both technical expertise and business understanding."
    )


def generate_approach(analysis: ProjectAnalysis, category: str, delivery_days: int) -> str:
    tech = analysis.technologies
    seo = analysis.seo_services
    content = analysis.content_types
    niche = analysis.niche

    if category == "seo":
        lines = []
        has_audit = any("audit" in s or "technical" in s for s in seo)
        has_backlinks = any("backlink" in s or "guest post" in s or "outreach" in s for s in seo)
        has_content = any("writing" in s or "article" in s or "blog" in s or "copywriting" in s for s in seo)
        has_keywords = any("keyword" in s for s in seo)
        has_local = any("local" in s for s in seo)
        has_ecommerce = any("ecommerce" in s for s in seo)
        has_smo = any("social media" in s for s in seo)

        step = 1

        if has_audit:
            lines.append(f"{step}. Technical Audit — crawl the site, identify crawl errors, Core Web Vitals issues, and quick-win fixes")
            step += 1

        if has_keywords or (not has_audit and not has_backlinks and not has_content):
            lines.append(f"{step}. Keyword Research & Strategy — identify high-volume, low-competition keywords and map them to pages")
            step += 1

        if has_backlinks:
            domains = f" in the {niche} space" if niche else ""
            lines.append(f"{step}. Link Building — targeted outreach for high-DA, niche-relevant backlinks through guest posts and niche edits{domains}")
            step += 1

        if has_content:
            ct = _join_readable(content[:2]) if content else "SEO-optimized content"
            lines.append(f"{step}. Content Creation — research-backed, engaging {ct} that targets your keywords and ranks")
            step += 1

        if has_local:
            lines.append(f"{step}. Local SEO — optimize GMB profile, build citations, manage reviews for local pack visibility")
            step += 1

        if has_ecommerce:
            lines.append(f"{step}. Ecommerce Optimization — optimize product pages, category structure, and schema markup for organic traffic")
            step += 1

        if has_smo:
            platforms = ", ".join(analysis.platforms[:2]) if analysis.platforms else "social platforms"
            lines.append(f"{step}. Social Media Optimization — optimize {platforms} profiles and sync social signals with SEO strategy")
            step += 1

        if lines:
            lines.append(f"{step}. Tracking & Reporting — provide ranking reports and traffic analytics within {delivery_days} days")
            return "\n".join(lines)

        return (
            f"1. Technical SEO Audit - identify issues, crawl errors, and quick wins\n"
            f"2. On-Page & Content Optimization - target keywords, meta tags, content improvements\n"
            f"3. Off-Page & Monitoring - build quality backlinks and track rankings - results within {delivery_days} days"
        )

    if category == "web_dev":
        base = (
            f"1. Requirements & Architecture - clarify scope, wireframes, and tech stack\n"
            f"2. Development - build and test iteratively with regular progress updates\n"
            f"3. Deployment & Handover - launch within {delivery_days} days with documentation and support"
        )
        if tech:
            tech_str = " + ".join(tech[:3])
            return f"I'll build this using {tech_str}. My process:\n{base}"
        return base

    if category == "social_media":
        platforms_str = ", ".join(analysis.platforms[:3]) if analysis.platforms else "relevant platforms"
        if niche:
            return (
                f"1. Channel Audit — review {platforms_str} and analyze {niche} competitor strategies\n"
                f"2. Content Strategy — create a tailored content calendar for the {niche} audience\n"
                f"3. Execution & Reporting — deliver content and measure engagement within {delivery_days} days"
            )
        return (
            f"1. Channel Audit - review {platforms_str} and identify growth opportunities\n"
            f"2. Content Strategy - create a tailored content calendar with engaging posts\n"
            f"3. Execution & Reporting - deliver content and measure results within {delivery_days} days"
        )

    return (
        f"1. Understand your requirements and target audience in detail\n"
        f"2. Execute with regular feedback loops and iterations\n"
        f"3. Deliver polished results within {delivery_days} days with post-delivery support"
    )


def generate_specifics(analysis: ProjectAnalysis) -> str:
    parts = []

    if analysis.seo_services:
        s = analysis.seo_services[0]
        if analysis.niche:
            parts.append(f"For the {s} in the {analysis.niche} space, I have a proven plan that has worked for similar businesses.")
        else:
            parts.append(f"For your {s} requirements, I have a clear execution plan based on what works in 2026.")

    if analysis.deliverables:
        d = analysis.deliverables[0]
        if analysis.niche:
            parts.append(f"The {d} for your {analysis.niche} project — I have delivered this exact type of work successfully before.")
        else:
            parts.append(f"For the {d} you mentioned, I have a clear implementation plan ready.")

    if analysis.goals:
        goals_str = " and ".join(analysis.goals[:2])
        parts.append(f"Your goal to {goals_str} is absolutely achievable — I have helped clients hit these exact targets.")

    if analysis.content_types:
        ct = _join_readable(analysis.content_types[:2])
        parts.append(f"I'll create {ct} that is thoroughly researched, engaging, and optimized for both readers and search engines.")

    if analysis.target_keywords:
        kw_text = ", ".join(analysis.target_keywords[:3])
        parts.append(f"I already have a keyword strategy in mind targeting terms like \"{kw_text}\".")

    if analysis.constraints.get("responsive"):
        parts.append("I'll ensure the design is fully responsive across all devices and screen sizes.")

    if analysis.constraints.get("special"):
        parts.append(f"I'll build with {analysis.constraints.get('special')} best practices from day one.")

    if analysis.constraints.get("urgency"):
        parts.append("I understand this is time-sensitive and I am ready to prioritize delivery.")

    if analysis.platforms and not analysis.seo_services:
        platforms_str = ", ".join(analysis.platforms[:3])
        parts.append(f"I have hands-on experience with {platforms_str} and know the best practices for each platform.")

    if len(parts) >= 2:
        return " ".join(parts[:3])

    if parts:
        return parts[0]

    return "I am available to start immediately and can adapt to your preferred workflow."


SMART_QUESTIONS = [
    ("backlink", "What type of backlinks are you targeting — guest posts on high-DA sites, niche edits, or HARO links?"),
    ("guest post", "Do you have specific DA/DR requirements for the sites you want guest posts on?"),
    ("link building", "Are you focused on homepage backlinks or deep links to specific pages?"),
    ("keyword research", "Do you already have a seed keyword list, or should I start fresh with competitor analysis?"),
    ("keyword", "What are your top 3 target keywords that would make this project a success?"),
    ("seo audit", "When was your last technical SEO audit, and do you have Google Search Console access?"),
    ("technical seo", "Are you seeing any specific crawl errors or Core Web Vitals issues in Search Console?"),
    ("crawl", "Do you have access to your Google Search Console and server logs for the audit?"),
    ("on-page", "Do you already have meta titles and descriptions in place, or do those need to be written from scratch?"),
    ("content writing", "How many words per article are you targeting, and do you have a preferred tone — formal, conversational, or technical?"),
    ("article", "Do you have specific topics outlined, or should I research and suggest topics based on keyword data?"),
    ("blog writing", "What's your target publishing frequency — weekly, bi-weekly, or monthly?"),
    ("blog post", "Do you need the blog post to include custom images, infographics, or data charts?"),
    ("copywriting", "Who's your target audience for this copy — B2B decision makers, consumers, or technical users?"),
    ("product description", "How many products need descriptions, and do you have a template or style guide?"),
    ("local seo", "Do you have a verified Google My Business profile already, or does that need to be set up?"),
    ("gmb", "Have you optimized your GMB listing with photos, posts, and Q&A, or is that part of what you need?"),
    ("ecommerce seo", "Which ecommerce platform are you on — Shopify, WooCommerce, or Magento?"),
    ("amazon seo", "Are you targeting Amazon-specific keywords, or do you also need off-Amazon SEO for your listings?"),
    ("ranking", "What keywords or pages are you currently ranking for, and where do you want to be?"),
    ("traffic", "What's your current monthly organic traffic, and what's your target over the next 3–6 months?"),
    ("competitor", "Which competitors are you trying to outrank? I can analyze their backlink profile and strategy."),
    ("competitor analysis", "Would you like me to do a full competitor backlink analysis as part of the strategy?"),
    ("domain authority", "What's your current DA/DR score, and do you have a target number in mind?"),
    ("serp", "Are you targeting featured snippets, People Also Ask, or standard blue links?"),
    ("social media", "Which platforms are your priority — Instagram, Facebook, or LinkedIn?"),
    ("instagram", "Are you targeting organic growth or paid promotions on Instagram?"),
    ("tiktok", "What content style fits your brand — trending short-form, educational, or behind-the-scenes?"),
    ("responsive", "Which devices and browsers are you targeting?"),
    ("mobile", "Do you need a mobile app alongside the website?"),
    ("wordpress", "Do you already have hosting and a domain, or do you need help setting those up?"),
    ("react", "Do you have Figma or XD designs ready, or do you need UI design help as well?"),
    ("api", "Do you have API documentation ready, or should I help with the API specs?"),
    ("database", "Which database do you prefer — PostgreSQL, MySQL, or MongoDB?"),
    ("design", "Do you have brand guidelines, a style guide, or design mockups ready?"),
    ("content", "Do you have content and copy ready, or do you need content creation too?"),
    ("ecommerce", "Which ecommerce platform are you using — Shopify, WooCommerce, or something else?"),
    ("shopify", "Do you already have a Shopify store or are you starting from scratch?"),
    ("migration", "Are you migrating from an existing platform or starting fresh?"),
    ("multilingual", "Do you need the site or content in multiple languages?"),
    ("analytics", "Do you need Google Analytics, Search Console, or custom analytics integration?"),
    ("seo", "Do you need on-page, off-page, technical, or all three types of SEO?"),
    ("newsletter", "Do you already have an email list, or do you need help building one alongside the newsletter?"),
    ("press release", "Do you have a distribution plan, or do you need me to handle PR distribution as well?"),
]

FALLBACK_QUESTIONS = [
    "Could you share any reference examples of what you have in mind?",
    "Do you have any specific requirements you'd like me to prioritize?",
    "What does success look like for this project from your perspective?",
    "Are there any competitors or similar projects you'd like me to look at as reference?",
    "Is there anything else about your requirements that would help me tailor the solution?",
    "What's the one thing that would make this project a success for you?",
]


def generate_question(project: ProjectCandidate, analysis: ProjectAnalysis) -> str:
    combined = (
        project.title.lower()
        + " "
        + (project.description or "").lower()[:2000]
        + " "
        + " ".join(project.skill_tags or []).lower()
    )

    matches: list[tuple[int, str]] = []
    seen_qs = set()
    for keyword, question in SMART_QUESTIONS:
        if keyword in combined and question not in seen_qs:
            matches.append((len(keyword), question))
            seen_qs.add(question)

    if matches:
        matches.sort(key=lambda x: x[0], reverse=True)
        return matches[0][1]

    if analysis.seo_services:
        svc = analysis.seo_services[0]
        if "backlink" in svc:
            return "What DA/DR range are you targeting for the backlinks, and do you prefer guest posts or niche edits?"
        if "content" in svc or "writing" in svc:
            return "Do you have a content brief or style guide, or would you like me to create one based on your niche?"
        if "audit" in svc:
            return "Do you have Google Search Console and analytics access ready for the audit?"
        if "keyword" in svc:
            return "Are you targeting a specific geographic region or is this global keyword research?"
        if "local" in svc:
            return "Do you already have a verified GMB profile, or does that need to be created?"
        if "ecommerce" in svc:
            return "How many product pages need SEO optimization, and what platform are you on?"
        return f"For the {svc}, do you have any specific deliverables or deadlines in mind?"

    if analysis.technologies and len(analysis.technologies) >= 2:
        techs = " and ".join(analysis.technologies[:2])
        return f"Do you have an existing codebase or are we building this from scratch with {techs}?"

    if analysis.platforms:
        platform = analysis.platforms[0]
        return f"For {platform}, do you have any existing assets or content I should work with?"

    if analysis.deliverables:
        d = analysis.deliverables[0]
        return f"For the {d}, do you have any specific preferences or examples in mind?"

    return random.choice(FALLBACK_QUESTIONS)


GREETINGS = [
    "Hi there,",
    "Hello,",
    "Hey,",
    "Hi,",
    "Greetings,",
]


def _join_readable(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def build_proposal_sections(
    project: ProjectCandidate,
    settings,
) -> str:
    analysis = analyze_project(project)

    greeting = random.choice(GREETINGS)
    name = (settings.freelancer_name if settings and settings.freelancer_name else "").strip()
    if not name:
        name = "there"

    style = (settings.proposal_style if settings else "medium").lower()

    understanding = generate_understanding(project, analysis)
    experience = generate_experience(
        analysis,
        project.category,
        settings.years_of_experience if settings else 3,
    )
    approach = generate_approach(
        analysis,
        project.category,
        settings.delivery_days if settings else 7,
    )
    specifics = generate_specifics(analysis)
    question = generate_question(project, analysis)

    skill_tags_str = ", ".join(project.skill_tags) if project.skill_tags else project.matched_skill or project.category.replace("_", " ")

    if style == "short":
        proposal = (
            f"{greeting} my name is {name}.\n\n"
            f"{understanding}\n\n"
            f"{experience}\n\n"
            f"My approach:\n"
            f"{approach}\n\n"
            f"{question}\n\n"
            f"I am available to start right away.\n\n"
            f"- {name}"
        )
    elif style == "long":
        proposal = (
            f"{greeting} my name is {name}.\n\n"
            f"{understanding}\n\n"
            f"{experience}\n\n"
            f"My approach for this project:\n"
            f"{approach}\n\n"
            f"Specific to your project:\n"
            f"{specifics}\n\n"
            f"{question}\n\n"
            f"I am available to start right away and would love to discuss this further. "
            f"I can provide samples of similar work and references if helpful.\n\n"
            f"- {name}\n"
            f"Skills: {skill_tags_str}"
        )
    else:
        proposal = (
            f"{greeting} my name is {name}.\n\n"
            f"{understanding}\n\n"
            f"{experience}\n\n"
            f"My approach for this project:\n"
            f"{approach}\n\n"
            f"{specifics}\n\n"
            f"{question}\n\n"
            f"I am available to start right away and would love to discuss this further.\n\n"
            f"- {name}\n"
            f"Skills: {skill_tags_str}"
        )

    return proposal


def build_proposal_from_template(
    template: str,
    project: ProjectCandidate,
    settings,
) -> str:
    analysis = analyze_project(project)

    name = (settings.freelancer_name if settings and settings.freelancer_name else "").strip()
    if not name:
        name = "there"

    years = settings.years_of_experience if settings else 3
    delivery = settings.delivery_days if settings else 7

    skills_label = project.matched_skill or project.category.replace("_", " ")
    skill_tags_str = ", ".join(project.skill_tags) if project.skill_tags else skills_label

    description_preview = (
        (project.description[:500] + "...")
        if project.description and len(project.description) > 500
        else (project.description or project.snippet)
    )

    greeting = random.choice(GREETINGS)
    understanding = generate_understanding(project, analysis)
    experience = generate_experience(analysis, project.category, years)
    approach = generate_approach(analysis, project.category, delivery)
    specifics = generate_specifics(analysis)
    question = generate_question(project, analysis)

    tech_list = ", ".join(analysis.technologies[:5]) if analysis.technologies else skills_label
    deliverables_text = ", ".join(analysis.deliverables[:3]) if analysis.deliverables else "your project requirements"
    platforms_text = ", ".join(analysis.platforms[:3]) if analysis.platforms else ""

    placeholders = {
        "freelancer_name": name,
        "project_title": project.title,
        "skills": skills_label,
        "skill_tags": skill_tags_str,
        "url": project.url,
        "description": description_preview,
        "snippet": project.snippet,
        "matched_skill": project.matched_skill or "",
        "proposal_count": project.proposal_count or "unknown",
        "posted_label": project.posted_label or "recently",
        "category": project.category.replace("_", " ").title(),
        "years_of_experience": years,
        "delivery_days": delivery,
        "question": question,
        "greeting": greeting,
        "understanding_paragraph": understanding,
        "experience_paragraph": experience,
        "approach_paragraph": approach,
        "specifics_paragraph": specifics,
        "technologies": tech_list,
        "deliverables": deliverables_text,
        "platforms": platforms_text,
    }

    try:
        return template.format(**placeholders)
    except KeyError as e:
        logger.warning("Template missing placeholder %s, falling back to smart proposal", e)
        return build_proposal_sections(project, settings)
