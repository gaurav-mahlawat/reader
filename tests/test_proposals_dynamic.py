"""Test that proposals are dynamic and project-specific across different project types."""
import sys
sys.path.insert(0, ".")

from app.bot.proposal_engine import (
    analyze_project, generate_understanding, generate_experience,
    generate_approach, generate_question, generate_specifics,
)
from app.bot.discovery import ProjectCandidate


class FS:
    freelancer_name = "Gaurav"
    years_of_experience = 4
    delivery_days = 7
    proposal_style = "medium"


def pc(pid, title, cat, skill, desc, tags):
    return ProjectCandidate(
        project_id=pid, title=title, url="", category=cat,
        snippet=desc[:100], matched_skill=skill, description=desc,
        skill_tags=tags,
    )


projects = [
    (
        "BACKLINKS",
        pc("p1", "Need 50 High DA Backlinks for Travel Blog", "seo", "SEO",
           "Looking for 50 DA30+ guest posts and niche edits from travel niche. "
           "White-hat only. My travel site is 2 years old, want to rank for "
           "safari tours and adventure travel. Budget 500. Need weekly reports.",
           ["SEO", "Link Building"]),
    ),
    (
        "CONTENT",
        pc("p2", "SEO Blog Writer for SaaS Tech Site", "seo", "SEO",
           "Need 4 blog posts per month, 1500-2000 words each. Topics: cloud "
           "computing, AI, SaaS trends. Must include keyword research, heading "
           "structure, internal linking. Target audience: CTOs and founders. "
           "Content needed within 7 days.",
           ["SEO", "Content Writing"]),
    ),
    (
        "AUDIT",
        pc("p3", "Full Technical SEO Audit for Ecommerce Store", "seo", "SEO",
           "Need a complete technical SEO audit for my Shopify store. Check crawl "
           "errors, Core Web Vitals, duplicate content, site speed. I have Search "
           "Console access. 500 products. Want a prioritized action plan with "
           "fixes ranked by impact.",
           ["SEO", "Technical SEO"]),
    ),
    (
        "LOCAL",
        pc("p4", "Local SEO for Dental Clinic in Mumbai", "seo", "SEO",
           "Need local SEO for my dental clinic. Optimize GMB profile, build "
           "citations, get more reviews. Want to rank in Mumbai local 3-pack "
           "for keywords like dentist Mumbai, dental clinic near me, best dentist.",
           ["SEO", "Local SEO"]),
    ),
    (
        "SOCIAL",
        pc("p5", "Instagram Growth for Fashion Brand", "social_media", "Social Media",
           "Need Instagram manager for fashion brand. Create 20 posts per month, "
           "reels strategy, influencer outreach program. Target organic growth "
           "from 5k to 20k followers in 6 months. Need to increase engagement rate by 3x.",
           ["Social Media", "Instagram"]),
    ),
    (
        "WEBDEV",
        pc("p6", "Build React Dashboard for Analytics", "web_dev", "React",
           "Need a React dashboard with real-time charts and filters. Use Chart.js, "
           "WebSocket for live updates. Must be responsive across all devices. "
           "Data from REST API. Login with JWT authentication. Figma designs ready.",
           ["React", "JavaScript", "API"]),
    ),
]


def test_all_proposals_are_unique():
    """Each project type should produce a demonstrably different proposal."""
    proposals = []
    for label, p in projects:
        a = analyze_project(p)
        proposal = "|".join([
            generate_understanding(p, a),
            generate_experience(a, p.category, 4),
            generate_approach(a, p.category, 7),
            generate_question(p, a),
        ])
        proposals.append((label, proposal))

    for i, (label_a, pa) in enumerate(proposals):
        for j, (label_b, pb) in enumerate(proposals):
            if i >= j:
                continue
            assert pa != pb, f"{label_a} and {label_b} proposals should differ"
    print("OK: All 6 project types produce unique proposals")


def test_backlinks_detects_services():
    _, p = projects[0]
    a = analyze_project(p)
    assert "backlink building" in a.seo_services
    assert a.niche == "travel blog"


def test_content_detects_services():
    _, p = projects[1]
    a = analyze_project(p)
    assert "keyword research" in a.seo_services, f"got: {a.seo_services}"
    assert "blog writing" in a.seo_services, f"got: {a.seo_services}"


def test_audit_detects_services():
    _, p = projects[2]
    a = analyze_project(p)
    assert "technical SEO audit" in a.seo_services


def test_local_detects_services_and_niche():
    _, p = projects[3]
    a = analyze_project(p)
    assert "local SEO" in a.seo_services
    assert "dental" in a.niche


def test_backlinks_experience_mentions_link_building():
    _, p = projects[0]
    a = analyze_project(p)
    exp = generate_experience(a, "seo", 4)
    assert "backlink" in exp.lower()


def test_content_experience_mentions_content_writing():
    _, p = projects[1]
    a = analyze_project(p)
    exp = generate_experience(a, "seo", 4)
    assert "content" in exp.lower() or "writing" in exp.lower()


def test_backlinks_approach_has_link_building_step():
    _, p = projects[0]
    a = analyze_project(p)
    approach = generate_approach(a, "seo", 7)
    assert "Link Building" in approach or "Backlink" in approach


def test_content_approach_has_content_creation_step():
    _, p = projects[1]
    a = analyze_project(p)
    approach = generate_approach(a, "seo", 7)
    assert "Content" in approach


def test_backlinks_question_is_link_specific():
    _, p = projects[0]
    a = analyze_project(p)
    q = generate_question(p, a).lower()
    assert "backlink" in q or "guest post" in q or "niche edit" in q or "link" in q, f"got: {q}"


def test_content_question_is_writing_specific():
    _, p = projects[1]
    a = analyze_project(p)
    q = generate_question(p, a).lower()
    assert "keyword" in q or "content" in q or "writing" in q or "blog" in q, f"got: {q}"


def test_social_media_detects_platform():
    _, p = projects[4]
    a = analyze_project(p)
    assert "Instagram" in a.platforms


def test_social_media_approach_mentions_platform():
    _, p = projects[4]
    a = analyze_project(p)
    approach = generate_approach(a, "social_media", 7)
    assert "Instagram" in approach


def test_webdev_detects_react():
    _, p = projects[5]
    a = analyze_project(p)
    assert "React" in a.technologies


def test_webdev_approach_mentions_react():
    _, p = projects[5]
    a = analyze_project(p)
    approach = generate_approach(a, "web_dev", 7)
    assert "React" in approach


if __name__ == "__main__":
    for label, p in projects:
        a = analyze_project(p)
        print("=" * 72)
        print(f"  {label}")
        print(f"  services:  {a.seo_services}")
        print(f"  niche:     {a.niche or '-'}")
        print(f"  content:   {a.content_types}")
        print(f"  keywords:  {a.target_keywords}")
        print(f"  goals:     {a.goals}")
        print(f"  tech:      {a.technologies}")
        print(f"  platforms: {a.platforms}")
        print()
        u = generate_understanding(p, a)
        e = generate_experience(a, p.category, 4)
        ap = generate_approach(a, p.category, 7)
        q = generate_question(p, a)
        s = generate_specifics(a)
        print(f"  Undrstnd: {u[:150]}")
        print(f"  Experien: {e[:150]}")
        for line in ap.split("\n")[:5]:
            print(f"  Step: {line}")
        print(f"  Question: {q[:120]}")
        print(f"  Specific: {s[:120]}")
        print()
