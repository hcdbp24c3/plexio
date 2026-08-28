"""Shared fixtures for plexio test suite."""

# Never ship telemetry from tests: the app calls sentry_sdk.init() at import
# time, which installs an ASGI middleware that captures 5xx exceptions. That
# capture path is incompatible with Python 3.13 (it tries to pickle
# FrameLocalsProxy), so disable it up front, before any test module imports
# the app.
import sentry_sdk  # noqa: E402

sentry_sdk.init = lambda *args, **kwargs: None  # type: ignore[assignment]
