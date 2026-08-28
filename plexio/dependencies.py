import base64
import json

from aiohttp import ClientSession
from fastapi import Request
from sentry_sdk import set_user

from plexio.models.addon import AddonConfiguration


def decode_base64_cfg(base64_cfg: str) -> str:
    """Decode a URL-safe (or legacy standard) base64 config string.

    Configs travel in URL paths, so new installs are encoded with the
    URL-safe alphabet and no padding (``-``/``_``, no ``+``/``/``/``=``).
    Older installs used the standard alphabet; ``urlsafe_b64decode`` accepts
    both alphabets, so we only need to restore the padding.
    """
    padding = '=' * (-len(base64_cfg.rstrip('=')) % 4)
    return base64.urlsafe_b64decode(base64_cfg.rstrip('=') + padding).decode()


def get_http_client(request: Request) -> ClientSession:
    return request.state.plex_client


def get_cache(request: Request):
    return request.state.cache


def get_addon_configuration(base64_cfg: str | None = None) -> AddonConfiguration | None:
    if base64_cfg is None:
        return None
    decoded = decode_base64_cfg(base64_cfg)
    configuration = AddonConfiguration(**json.loads(decoded))
    return configuration


def set_sentry_user(installation_id: str | None = None) -> None:
    if installation_id:
        set_user({'id': installation_id})
