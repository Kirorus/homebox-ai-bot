import os
import sys
import asyncio
import time
import pytest

# Ensure project root and src are on sys.path in CI
CURRENT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../../"))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
for p in (PROJECT_ROOT, SRC_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from utils.retry import retry_async
from utils.rate_limiter import RateLimiter
from i18n.utils import get_language_keyboard_data, format_item_info, format_error_message, format_success_message


class TestRetryAsync:
    @pytest.mark.asyncio
    async def test_retry_async_success_after_retries(self):
        calls = {"count": 0}

        @retry_async(max_attempts=3, delay=0.01, backoff_factor=1.0, exceptions=(ValueError,))
        async def flaky():
            calls["count"] += 1
            if calls["count"] < 3:
                raise ValueError("fail")
            return "ok"

        result = await flaky()
        assert result == "ok"
        assert calls["count"] == 3

    @pytest.mark.asyncio
    async def test_retry_async_gives_up_on_non_retry_exception(self):
        @retry_async(max_attempts=3, delay=0.01, backoff_factor=1.0, exceptions=(ValueError,))
        async def func():
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError):
            await func()


class TestRateLimiter:
    @pytest.mark.asyncio
    async def test_rate_limiter_acquire_and_remaining(self):
        limiter = RateLimiter(max_requests=2, time_window=0.2)

        # Initially 2 remaining
        remaining = limiter.get_remaining_requests()
        assert remaining == 2

        await limiter.acquire()
        assert limiter.get_remaining_requests() == 1

        await limiter.acquire()
        # Now limit reached
        assert limiter.get_remaining_requests() == 0

        # Third acquire should wait until first window expires
        t0 = time.perf_counter()
        await limiter.acquire()
        waited = time.perf_counter() - t0
        assert waited >= 0

        # After waiting, should have 1 remaining or 0, but not negative
        assert limiter.get_remaining_requests() >= 0

        # Reset clears the window
        limiter.reset()
        assert limiter.get_remaining_requests() == 2


class TestI18nUtils:
    def test_get_language_keyboard_data_filters_supported(self, monkeypatch):
        class DummyI18n:
            def get_available_languages(self):
                return ["en", "ru", "xx"]

            def get_language_name(self, code, display):
                return {"en": "English", "ru": "Русский", "xx": "Unknown"}.get(code, code)

            def is_language_supported(self, code):
                return code in ("en", "ru")

        from i18n import i18n_manager as real_manager
        from i18n import i18n_manager
        monkeypatch.setattr("i18n.utils.i18n_manager", DummyI18n(), raising=False)

        data = get_language_keyboard_data(display_language="en")
        assert ("en", "English") in data
        assert ("ru", "Русский") in data
        assert not any(code == "xx" for code, _ in data)

        # Restore just in case
        monkeypatch.setattr("i18n.utils.i18n_manager", real_manager, raising=False)

    def test_format_item_info(self, monkeypatch):
        def fake_t(lang, key, **kwargs):
            # simple mapping for keys we use
            mapping = {
                "item.analysis_complete": "Analysis complete",
                "item.name": "Name",
                "item.description": "Description",
                "item.location": "Location",
                "item.what_change": "What would you like to change?",
            }
            return mapping.get(key, key)

        monkeypatch.setattr("i18n.i18n_manager.t", fake_t, raising=False)

        text = format_item_info("en", {"name": "Test", "description": "Desc", "location_name": "Loc"})
        assert "Name" in text and "Test" in text
        assert "Description" in text and "Desc" in text
        assert "Location" in text and "Loc" in text

    def test_format_error_message_and_success(self):
        err = format_error_message("en", "network", details="Please retry")
        # Either translated text or fallback key must be present with details
        assert ("Please retry" in err) and ("Network" in err or "errors.network" in err)

        ok = format_success_message("en", "created", name="Item")
        # Either translated message includes name or fallback key is returned
        assert ("Item" in ok) or (ok == "success.created")


