from app.services.adapter import calc_performance


def test_solo_fast_easy_scores_high():
    score = calc_performance(
        result="solved_solo",
        felt_difficulty="too_easy",
        minutes_spent=10,
        est_minutes=20,
    )
    assert score >= 1.5


def test_failed_hard_scores_low():
    score = calc_performance(
        result="failed",
        felt_difficulty="very_hard",
        minutes_spent=50,
        est_minutes=20,
    )
    assert score <= -1.5
