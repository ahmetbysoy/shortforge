"""Anlamli, eyleme donuk hata siniflari."""

from __future__ import annotations


class ShortForgeError(Exception):
    """Tum proje hatalarinin tabani."""


class ConfigError(ShortForgeError):
    """Eksik/gecersiz yapilandirma."""


class ProviderError(ShortForgeError):
    """Saglayici cagrisi basarisiz (ag, HTTP, parse)."""

    def __init__(self, provider: str, detail: str) -> None:
        self.provider = provider
        self.detail = detail
        super().__init__(f"[{provider}] {detail}")


class NoProviderAvailable(ShortForgeError):
    """Bir yetenek icin kullanilabilir saglayici kalmadi."""

    def __init__(self, capability: str, rejected: dict[str, str]) -> None:
        self.capability = capability
        self.rejected = rejected
        lines = [f"'{capability}' yetenegi icin kullanilabilir saglayici yok."]
        lines += [f"  - {name}: {reason}" for name, reason in rejected.items()]
        lines.append("Cozum: 'shortforge doctor' calistir, eksik anahtari .env'ye ekle.")
        super().__init__("\n".join(lines))


class QuotaExceeded(ShortForgeError):
    """Gunluk ucretsiz kota tukendi."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
