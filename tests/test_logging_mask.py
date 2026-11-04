"""Sirlarin log'a sizmamasi.

DIKKAT: sahte token'lar bilerek parcalardan kurulur; boylece depoda
sir gorunumlu bir literal bulunmaz (CI'daki sir taramasi da temiz kalir).
"""

from __future__ import annotations

from shortforge.logging import REDACTED, mask_secrets, register_secrets

FAKE_GOOGLE_KEY = "AIza" + "SyD-" + "1" * 30
FAKE_GITHUB_TOKEN = "ghp_" + "a" * 36
FAKE_OAUTH_TOKEN = "ya" + "29." + "x" * 14


def test_masks_known_token_patterns() -> None:
    raw = f"{FAKE_GOOGLE_KEY} {FAKE_GITHUB_TOKEN} {FAKE_OAUTH_TOKEN}"

    masked = mask_secrets(raw)

    assert "AIzaSyD" not in masked
    assert "ghp_" not in masked
    assert ("ya" + "29.") not in masked
    assert masked.count(REDACTED) == 3


def test_masks_key_value_pairs() -> None:
    masked = mask_secrets("client_secret=supergizli&refresh_token=abc123")
    assert "supergizli" not in masked
    assert "abc123" not in masked


def test_registered_secret_is_masked() -> None:
    register_secrets(["cok-gizli-deger-123"])
    assert mask_secrets("deger: cok-gizli-deger-123") == f"deger: {REDACTED}"


def test_short_values_ignored() -> None:
    register_secrets(["abc"])
    assert mask_secrets("abc") == "abc"
