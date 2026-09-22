from app.bot.utils import extract_project_id, category_from_search_url


def test_slug_project_id():
    url = "https://www.freelancer.in/projects/react-js/drag-drop-sld-data-visualizer"
    assert extract_project_id(url) == "react-js/drag-drop-sld-data-visualizer"


def test_numeric_project_id():
    url = "https://www.freelancer.in/projects/simple-website-12345678"
    assert extract_project_id(url) is not None


def test_category_from_url():
    assert category_from_search_url("https://www.freelancer.in/jobs/seo/") == "seo"
    assert category_from_search_url("https://www.freelancer.in/jobs/web-development/") == "web_dev"
