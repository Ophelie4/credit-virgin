from app.routers.marketplace import SAMPLE_LISTINGS, classify, sample_media_files
from app.routers.media import NAME

HOME = {"monthly_rent": 1500, "max_rent_to_income": 0.4, "min_score": 70}


def test_qualifies_when_score_and_income_are_enough():
    assert classify(HOME, 75, 4000) == ("within_reach", None)


def test_close_score_is_almost_with_the_gap_spelled_out():
    match, gap = classify(HOME, 62, 4000)
    assert match == "almost" and "8" in gap


def test_income_is_checked_before_score():
    match, gap = classify(HOME, 99, 3000)  # needs 1500 / 0.4 = 3750
    assert match == "not_yet" and "3,750" in gap


def test_unknown_income_falls_back_to_score_only():
    assert classify(HOME, 75, None)[0] == "within_reach"


def test_sample_portfolio_spans_every_score_bracket():
    mins = sorted(s["min_score"] for s in SAMPLE_LISTINGS)
    assert mins == [40, 50, 60, 70, 80, 85]


def test_every_sample_home_has_photos_and_a_tour_served_locally():
    for s in SAMPLE_LISTINGS:
        assert len(s["photo_urls"]) == 3 and s["tour_url"].endswith(".mp4"), s["title"]
        assert all(u.startswith("/api/media/") for u in [*s["photo_urls"], s["tour_url"]])
    assert all(NAME.match(n) for n in sample_media_files())


def test_media_route_rejects_anything_but_cdn_file_names():
    for bad in ("../../.env", "x.mp4", "051351_9761b3ec.png", "051351_9761b3ec-6de7-4157-9f04-64eeaa16fe9e.exe"):
        assert not NAME.match(bad)


def test_a_failed_check_becomes_the_first_thing_to_fix():
    from types import SimpleNamespace as NS
    from app.models import Check, ScoreFactor
    from app.routers.marketplace import _weakest_tip
    factors = [ScoreFactor(key="savings", label="Savings behaviour", points=11, max_points=15, detail=""),
               ScoreFactor(key="history", label="History length", points=15, max_points=15, detail="")]
    clean = NS(score=26, factors=factors, checks=[Check(key="rent_match", label="Rent", status="pass", detail="")])
    capped = NS(score=26, factors=factors, checks=[Check(key="rent_match", label="Rent", status="fail", detail="")])
    assert _weakest_tip(clean)["factor"] == "savings"
    tip = _weakest_tip(capped)
    assert tip["factor"] == "verification" and tip["check"] == "rent_match"
