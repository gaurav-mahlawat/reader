from app.bot.project_meta import parse_posted_age_days, passes_filters, ProjectMeta


def test_parse_posted_recent():
    assert parse_posted_age_days("Posted 2 hours ago") is not None
    assert parse_posted_age_days("Posted 2 days ago") == 2.0
    assert parse_posted_age_days("Posted 21 minutes ago") < 1


def test_passes_filters():
    ok, _ = passes_filters(
        ProjectMeta(proposal_count=10, posted_age_days=1.0, posted_label="Posted 1 day ago"),
        max_age_days=3,
        max_proposals=50,
    )
    assert ok

    ok, reason = passes_filters(
        ProjectMeta(proposal_count=50, posted_age_days=1.0, posted_label="Posted 1 day ago"),
        max_age_days=3,
        max_proposals=50,
    )
    assert not ok
    assert "50" in reason

    ok, reason = passes_filters(
        ProjectMeta(proposal_count=5, posted_age_days=5.0, posted_label="Posted 5 days ago"),
        max_age_days=3,
        max_proposals=50,
    )
    assert not ok
    assert "old" in reason.lower()
