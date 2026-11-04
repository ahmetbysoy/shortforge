"""ShortForge CLI: `shortforge doctor` ile tum saglayici/kota durumunu raporlar."""

from __future__ import annotations

import asyncio
import json
import platform
import shutil
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from shortforge import __version__
from shortforge.config import Settings, get_settings
from shortforge.logging import configure_logging, register_secrets
from shortforge.models import HealthStatus
from shortforge.providers.registry import CAPABILITY_LABELS, build_default_registry
from shortforge.quota import QuotaLedger

app = typer.Typer(add_completion=False, help="ShortForge - ucretsiz katman Shorts hatti")
console = Console()

STATUS_STYLE: dict[HealthStatus, str] = {
    HealthStatus.OK: "bold green",
    HealthStatus.DEGRADED: "bold yellow",
    HealthStatus.DOWN: "bold red",
    HealthStatus.MISSING_KEY: "dim",
}


def _ram_gib() -> float | None:
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"):
                return round(int(line.split()[1]) / 1024**2, 1)
    except OSError:
        return None
    return None


def _arch_info(settings: Settings) -> dict[str, Any]:
    usage = shutil.disk_usage(Path.cwd())
    return {
        "python": platform.python_version(),
        "platform": platform.system(),
        "ram_gib": _ram_gib(),
        "ffmpeg": shutil.which("ffmpeg") or None,
        "disk_free_gib": round(usage.free / 1024**3, 1),
        "dry_run": settings.dry_run,
        "daily_video_limit": settings.daily_video_limit,
    }


async def _collect(settings: Settings, ledger: QuotaLedger) -> list[dict[str, Any]]:
    registry = build_default_registry(settings, ledger)
    rows: list[dict[str, Any]] = []
    for provider, health in await registry.health_all():
        rows.append(
            {
                "provider": provider.name,
                "capability": CAPABILITY_LABELS[provider.capability],
                "status": health.status.value,
                "latency_ms": health.latency_ms,
                "detail": health.detail,
                "free_tier_note": health.free_tier_note or provider.free_tier_note,
                "cost_units": provider.cost_units,
            }
        )
    return rows


def _render_table(rows: list[dict[str, Any]], quota: dict[str, Any], arch: dict[str, Any]) -> None:
    table = Table(title=f"ShortForge doctor  (v{__version__})", show_lines=False)
    table.add_column("Saglayici", style="cyan", no_wrap=True)
    table.add_column("Yetenek")
    table.add_column("Durum", no_wrap=True)
    table.add_column("Gecikme", justify="right")
    table.add_column("Ucretsiz katman notu", overflow="fold")
    table.add_column("Detay", overflow="fold", style="dim")
    for row in rows:
        status = HealthStatus(row["status"])
        latency = row["latency_ms"]
        table.add_row(
            str(row["provider"]),
            str(row["capability"]),
            f"[{STATUS_STYLE[status]}]{status.value}[/]",
            f"{latency} ms" if latency is not None else "-",
            str(row["free_tier_note"] or "-"),
            str(row["detail"] or "-"),
        )
    console.print(table)

    yt = quota["youtube"]
    console.print(
        f"[bold]KOTA[/] bugun [cyan]{yt['units_spent']}[/]/{yt['units_cap']} birim | "
        f"yukleme [cyan]{yt['uploads_spent']}[/]/{yt['uploads_cap']} | "
        f"sifirlanma: {quota['reset_at_utc'][:16]}Z (~{quota['reset_in']})"
    )
    console.print(
        f"[bold]MIMARI[/] python {arch['python']} | {arch['platform']} | "
        f"RAM {arch['ram_gib']} GiB | ffmpeg: {'var' if arch['ffmpeg'] else 'YOK'} | "
        f"disk {arch['disk_free_gib']} GiB bos | dry_run={arch['dry_run']}"
    )
    console.print(
        "[dim]Gizlilik: yuklemeler daima PRIVATE baslar; public'e alma yalniz insan onayiyla.[/]"
    )


@app.command()
def doctor(
    json_output: bool = typer.Option(False, "--json", help="Makine-okur JSON cikti"),
    strict: bool = typer.Option(False, "--strict", help="Kritik saglayici DOWN ise exit 1"),
) -> None:
    """Tum saglayicilarin, kotanin ve ortamin durumunu raporlar."""
    settings = get_settings()
    configure_logging(settings.log_level)
    register_secrets(settings.secret_values)
    settings.ensure_dirs()

    ledger = QuotaLedger(settings.db_path, upload_daily_cap=settings.yt_daily_upload_cap)
    try:
        rows = asyncio.run(_collect(settings, ledger))
        quota = ledger.summary()
    finally:
        ledger.close()
    arch = _arch_info(settings)

    if json_output:
        payload = {"version": __version__, "providers": rows, "quota": quota, "arch": arch}
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        _render_table(rows, quota, arch)

    if strict:
        blocking = [
            row
            for row in rows
            if row["status"] == HealthStatus.DOWN.value and row["capability"] in {"gorsel"}
        ]
        if blocking:
            console.print("[red]--strict: kullanilabilir gorsel saglayici yok.[/]")
            raise typer.Exit(code=1)


@app.command()
def version() -> None:
    """Surum bilgisi."""
    typer.echo(f"shortforge {__version__}")


def main() -> None:  # pragma: no cover
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
