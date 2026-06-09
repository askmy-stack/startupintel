from startupintel.bots.accelerator_bot import AcceleratorBot


def test_yc_like_accelerator_ranks_high():
    bot = AcceleratorBot()
    score = bot.compute_roi_score(
        {
            "follow_on_funding_rate": 0.82,
            "median_time_to_series_a_months": 10,
            "survival_rate_3yr": 0.9,
            "unicorn_rate": 0.08,
            "acqui_hire_rate": 0.12,
            "shutdown_rate": 0.04,
        },
        cohort_count=200,
    )
    assert score > 55


def test_small_accelerator_excluded_by_minimum_cohort():
    bot = AcceleratorBot()
    assert bot.compute_roi_score({"follow_on_funding_rate": 1.0}, cohort_count=3) == 0.0


def test_confidence_interval_wider_for_small_cohort():
    bot = AcceleratorBot()
    small = bot.confidence_interval(successes=5, n=10)
    large = bot.confidence_interval(successes=50, n=100)
    assert small[1] - small[0] > large[1] - large[0]
