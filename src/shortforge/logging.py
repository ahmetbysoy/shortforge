"""structlog yapilandirmasi + sir maskeleme.

Kural: anahtar/token log'a asla ham dusmez. Hem desen bazli hem de
deger bazli (settings icindeki gizli alanlar) maskeleme yapilir.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable, MutableMapping
from typing import Any

import structlog

REDACTED = "***REDACTED***"

_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"AIza[0-9A-Za-z_\-]{30,}"), REDACTED),
    (re.compile(r"ghp_[0-9A-Za-z]{30,}"), REDACTED),
    (re.compile(r"github_pat_[0-9A-Za-z_]{20,}"), REDACTED),
    (re.compile(r"sk-[0-9A-Za-z_\-]{16,}"), REDACTED),
    (re.compile(r"ya29\.[0-9A-Za-z_\-]+"), REDACTED),
    (
        re.compile(r"(?i)\b(client_secret|refresh_token|api_key|token)=([^&\s\"']+)"),
        rf"\1={REDACTED}",
    ),
)

_EXTRA_SECRETS: set[str] = set()


def mask_secrets(value: str) -> str:
    """Bilinen sir desenlerini ve kayitli gizli degerleri maskeler."""
    masked = value
    for secret in _EXTRA_SECRETS:
        if secret and len(secret) >= 8:
            masked = masked.replace(secret, REDACTED)
    for pattern, replacement in _PATTERNS:
        masked = pattern.sub(replacement, masked)
    return masked


def register_secrets(values: Iterable[str | None]) -> None:
    """Sozluk/ayar katmanindaki gizli degerleri maskeleme listesine ekler."""
    for value in values:
        if value:
            _EXTRA_SECRETS.add(value)


def _mask_processor(
    _logger: Any, _name: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    for key, value in list(event_dict.items()):
        if isinstance(value, str):
            event_dict[key] = mask_secrets(value)
        elif isinstance(value, dict):
            event_dict[key] = {
                k: (mask_secrets(v) if isinstance(v, str) else v) for k, v in value.items()
            }
    return event_dict


def configure_logging(level: str = "INFO", *, json_output: bool = False) -> None:
    """Uygulama genelinde structlog'u yapilandirir."""
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(level=numeric_level, format="%(message)s")
    # httpx her istegi INFO seviyesinde loglar; gurultuyu kesiyoruz.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        _mask_processor,
    ]
    if json_output:
        processors.append(structlog.processors.JSONRenderer(ensure_ascii=False))
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> Any:
    return structlog.get_logger(name)
