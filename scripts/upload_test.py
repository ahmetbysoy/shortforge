#!/usr/bin/env python3
"""Ilk PRIVATE yukleme testi - kurallarin kodla zorlanmasi.

Bu script:
  1. token.json'dan kimlik bilgilerini okur (yoksa anlamli hata),
  2. KOTA KAPISI: QuotaLedger.assert_can_afford(1600, "upload") - atlanamaz,
  3. videos.insert ile yukler; privacyStatus yalnizca "private" kabul edilir,
  4. yukleme sonrasi videos.list ile YouTube'un GERCEK gizlilik durumunu okur
     (denetlenmemis projede public istense bile private doner - kanit),
  5. basarili yuklemeden SONRA kotadan dusur.

Kullanim:
    python scripts/upload_test.py --generate          # 5 sn test videosu uret + yukle
    python scripts/upload_test.py --video out/test.mp4
    python scripts/upload_test.py --dry-run           # hicbir sey yuklemeden kontroller
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shortforge.config import get_settings
from shortforge.quota import UPLOAD_UNITS, QuotaLedger

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CATEGORY_EDUCATION = "27"


def fail(message: str, code: int = 2) -> None:
    print(f"\n[HATA] {message}\n", file=sys.stderr)
    raise SystemExit(code)


def generate_test_video(path: Path, seconds: int = 5) -> None:
    """FFmpeg ile 1080x1920 dikey, sesli test videosu uretir (telifsiz, kendi uretimimiz)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "lavfi",
        "-i",
        f"color=c=0x101820:s=1080x1920:d={seconds}:r=30",
        "-f",
        "lavfi",
        "-i",
        f"sine=frequency=440:duration={seconds}",
        "-vf",
        (
            "drawtext=text='ShortForge':fontcolor=white:fontsize=110:"
            "x=(w-text_w)/2:y=(h-text_h)/2-120,"
            "drawtext=text='private yukleme testi':fontcolor=0x7FD1FF:fontsize=54:"
            "x=(w-text_w)/2:y=(h-text_h)/2+40,"
            "drawtext=text='%{eif\\:t\\:d} sn':fontcolor=white:fontsize=64:x=(w-text_w)/2:y=h-320"
        ),
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "96k",
        "-shortest",
        str(path),
    ]
    print(f"[..] Test videosu uretiliyor: {path}")
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        fail(f"ffmpeg basarisiz:\n{result.stderr[-1500:]}")


def probe_video(path: Path) -> dict[str, str]:
    out = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,duration,codec_name",
            "-of",
            "default=nw=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    info: dict[str, str] = {}
    for line in out.stdout.splitlines():
        if "=" in line:
            key, _, value = line.partition("=")
            info[key] = value
    return info


def build_client(token_path: Path):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    if not token_path.exists():
        fail(
            f"{token_path} bulunamadi. Once yetkilendirme yap:\n"
            "  python scripts/youtube_auth.py --mode manual\n"
            "  (client_secret.json olmadan bu adim tamamlanamaz - Google Cloud projesi gerekli)"
        )
    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            print("[..] Erisim tokeni suresi dolmus, refresh_token ile yenileniyor...")
            try:
                creds.refresh(Request())
            except Exception as exc:
                text = str(exc)
                if "invalid_grant" in text:
                    fail(
                        "refresh_token GECERSIZ (invalid_grant).\n"
                        "  En yaygin neden: consent screen 'Testing' modunda\n"
                        "  ve 7 gun gecmis.\n"
                        "  Cozum: consent screen'i 'In production' durumuna al ve\n"
                        "  `youtube_auth.py --auth-url` ile YENI token uret."
                    )
                fail(f"Token yenilenemedi: {text[:400]}")
        else:
            fail("Kimlik bilgisi gecersiz ve yenilenemiyor. Yeniden yetkilendir.")
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def upload(client, video: Path, title: str, description: str, privacy: str) -> str:
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "categoryId": CATEGORY_EDUCATION,
            "defaultLanguage": "tr",
            "defaultAudioLanguage": "tr",
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
            "license": "youtube",
            "embeddable": True,
        },
    }
    media = MediaFileUpload(str(video), chunksize=1024 * 1024, resumable=True, mimetype="video/mp4")
    request = client.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    print("[..] Yukleme basladi (resumable)...")
    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                print(f"     %{int(status.progress() * 100)}")
        except HttpError as exc:
            reason = ""
            try:
                reason = exc.error_details[0].get("reason", "")  # type: ignore[index]
            except Exception:
                reason = str(exc)[:200]
            if "quotaExceeded" in str(exc) or "uploadLimitExceeded" in str(exc):
                fail(f"Kota asildi (Google tarafi): {reason}. Pasifik 00:00'da yenilenir.")
            if "youtubeSignupRequired" in str(exc):
                fail("Bu Google hesabinda YouTube kanali yok. Once kanal olustur.")
            fail(
                f"Yukleme hatasi: {exc.status_code if hasattr(exc, 'status_code') else ''} {reason}"
            )
    return response["id"]


def verify_privacy(client, video_id: str) -> dict[str, object]:
    """YouTube'un gercekte uyguladigi gizlilik durumunu okur (kota: 1 birim)."""
    data = client.videos().list(part="status,snippet", id=video_id).execute()
    items = data.get("items", [])
    if not items:
        return {"found": False}
    return {
        "found": True,
        "privacyStatus": items[0]["status"]["privacyStatus"],
        "uploadStatus": items[0]["status"].get("uploadStatus"),
        "title": items[0]["snippet"]["title"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Ilk private yukleme testi")
    parser.add_argument("--video", type=Path, default=Path("out/test.mp4"))
    parser.add_argument("--token", type=Path, default=Path("token.json"))
    parser.add_argument("--title", default="Test Video 01")
    parser.add_argument(
        "--description", default="ShortForge otomasyon hatti test yuklemesi. #Shorts"
    )
    parser.add_argument("--privacy", default="private", choices=["private", "unlisted", "public"])
    parser.add_argument(
        "--generate", action="store_true", help="Test videosu yoksa ffmpeg ile uret"
    )
    parser.add_argument("--dry-run", action="store_true", help="Yukleme yapma, sadece kontroller")
    args = parser.parse_args()

    settings = get_settings()
    settings.ensure_dirs()
    ledger = QuotaLedger(settings.db_path, upload_daily_cap=settings.yt_daily_upload_cap)

    print("=== ShortForge / Ilk yukleme testi ===")
    print(f"video     : {args.video}")
    print(f"privacy   : {args.privacy}")
    print(f"kota      : {ledger.uploads_spent()}/{settings.yt_daily_upload_cap} yukleme bugun")

    # KURAL 5: public'e cikis yalnizca insan onayindan sonra. Bu script onay araci degil.
    if args.privacy != "private":
        fail(
            f"Bu test scripti yalnizca 'private' yukler (istenen: {args.privacy}).\n"
            "  Kural: once gizli yukle -> insan onayi -> yayinla. Onay akisi P5'te geliyor."
        )

    if not args.video.exists():
        if args.generate:
            generate_test_video(args.video)
        else:
            fail(f"{args.video} yok. `--generate` ile uretebilirsin.")

    info = probe_video(args.video)
    print(
        f"video bilgisi: {info.get('width')}x{info.get('height')} "
        f"{info.get('codec_name')} {float(info.get('duration', 0)):.2f} sn"
    )
    if info.get("width") and info.get("height") and info["width"] == info["height"]:
        print("[!] Kare video: Shorts icin dikey (9:16) olmali.")

    # KOTA KAPISI - atlanamaz
    try:
        ledger.assert_can_afford("youtube", UPLOAD_UNITS, "upload")
    except Exception as exc:
        fail(str(exc))
    print(f"[OK] Kota kapisi gecildi (maliyet {UPLOAD_UNITS} birim)")

    if args.dry_run:
        print("[dry-run] Kimlik bilgisi kontrolu...")
        if not args.token.exists():
            print("[dry-run] token.json YOK - gercek yukleme icin once yetkilendirme gerekli")
            return 0
        client = build_client(args.token)
        print("[dry-run] Kimlik bilgisi gecerli ve istemci kuruldu. Yukleme yapilmadi.")
        return 0

    client = build_client(args.token)
    video_id = upload(client, args.video, args.title, args.description, "private")
    ledger.charge("youtube", UPLOAD_UNITS, "upload")  # basaridan SONRA dus

    print(f"\n[OK] Yuklendi. video_id = {video_id}")
    print(f"     https://youtu.be/{video_id}")
    print(f"     https://studio.youtube.com/video/{video_id}/edit")

    state = verify_privacy(client, video_id)
    print(f"\n[DOGRULAMA] YouTube'un raporladigi durum: {state}")
    if state.get("privacyStatus") == "private":
        print("  -> PRIVATE dogrulandi. Denetlenmemis proje icin beklenen sonuc.")
    print(f"\nKalan yukleme hakki: {ledger.uploads_remaining()}/{settings.yt_daily_upload_cap}")
    ledger.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
