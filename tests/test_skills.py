from app.bot.utils import (
    build_project_search_urls,
    matches_user_skill,
    parse_skills_list,
)


def test_parse_skills():
    assert parse_skills_list("React, SEO\nWordPress") == ["React", "SEO", "WordPress"]


def test_build_project_search_urls():
    urls = build_project_search_urls(["React", "SEO"])
    assert all("/search/projects?" in u for u in urls)
    assert all("projectSort=latest" in u for u in urls)
    assert len(urls) == 2


def test_matches_user_skill():
    text = "Need a React developer for dashboard UI"
    assert matches_user_skill(text, ["React", "PHP"]) == "React"
    assert matches_user_skill(text, ["Java"]) is None
