"""Shared fixtures for plexio test suite."""

# Never ship telemetry from tests: the app calls sentry_sdk.init() at import
# time, which installs an ASGI middleware that captures 5xx exceptions. That
# capture path is incompatible with Python 3.13 (it tries to pickle
# FrameLocalsProxy), so disable it up front, before any test module imports
# the app.
import sentry_sdk  # noqa: E402

sentry_sdk.init = lambda *args, **kwargs: None  # type: ignore[assignment]

import pytest  # noqa: E402

from plexio.security import RateLimiter  # noqa: E402


@pytest.fixture(autouse=True)
def public_rate_limit(monkeypatch):
    """The app-wide per-IP limiter (60/min) otherwise trips across files."""
    import plexio.main as main_module

    monkeypatch.setattr(
        main_module,
        '_public_limiter',
        RateLimiter(max_requests=100_000),
    )
