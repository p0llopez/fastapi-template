import time

import pytest

from src.contexts.shared.infrastructure.http.rate_limit_middleware import (
    SlidingWindowRateLimiter,
)


@pytest.mark.unit
class TestSlidingWindowRateLimiter:
    def test_allows_requests_under_limit(self) -> None:
        limiter = SlidingWindowRateLimiter(max_requests=5, window_seconds=60.0)

        for _ in range(5):
            assert limiter.is_allowed("192.168.1.1") is True

    def test_blocks_requests_over_limit(self) -> None:
        limiter = SlidingWindowRateLimiter(max_requests=3, window_seconds=60.0)

        for _ in range(3):
            limiter.is_allowed("10.0.0.1")

        assert limiter.is_allowed("10.0.0.1") is False

    def test_separate_limits_per_ip(self) -> None:
        limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=60.0)

        limiter.is_allowed("1.1.1.1")
        limiter.is_allowed("1.1.1.1")
        assert limiter.is_allowed("1.1.1.1") is False

        assert limiter.is_allowed("2.2.2.2") is True

    def test_remaining_returns_correct_count(self) -> None:
        limiter = SlidingWindowRateLimiter(max_requests=5, window_seconds=60.0)

        assert limiter.remaining("10.0.0.1") == 5

        limiter.is_allowed("10.0.0.1")
        assert limiter.remaining("10.0.0.1") == 4

        limiter.is_allowed("10.0.0.1")
        limiter.is_allowed("10.0.0.1")
        assert limiter.remaining("10.0.0.1") == 2

    def test_expired_entries_are_cleaned(self) -> None:
        limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=0.1)

        limiter.is_allowed("172.16.0.1")
        limiter.is_allowed("172.16.0.1")
        assert limiter.is_allowed("172.16.0.1") is False

        time.sleep(0.15)

        assert limiter.is_allowed("172.16.0.1") is True

    def test_reset_time_returns_window_end(self) -> None:
        limiter = SlidingWindowRateLimiter(max_requests=5, window_seconds=60.0)

        before = time.time()
        reset = limiter.reset_time("10.0.0.1")
        after = time.time()

        assert before + 60.0 <= reset <= after + 60.0

        limiter.is_allowed("10.0.0.1")
        reset_after_request = limiter.reset_time("10.0.0.1")

        assert reset_after_request > before
        assert reset_after_request <= after + 60.0 + 1.0
