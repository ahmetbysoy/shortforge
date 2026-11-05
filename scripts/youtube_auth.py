#!/usr/bin/env python3
"""YouTube OAuth2 yetkilendirmesi - kalici refresh_token uretir.

NEDEN BU TASARIM
----------------
`InstalledAppFlow.run_console()` google-auth-oauthlib 1.5'te KALDIRILDI ve Google'in
"oob" (kopyala-yapistir kodu) akisi 2022'de tamamen kapatildi. Bu yuzden headless
ortamda calisan iki mod var:

  1) loopback (onerilen): tarayici ve makine ayni yerdeyse / SSH tuneli varsa
        python scripts/youtube_auth.py --mode loopback
     Tarayici acilir, onay verilir, kod otomatik yakalanir.

  2) manual (bulut/headless, IKI ADIM - onerilen):
        # A) URL uret (PKCE verifier diske yazilir)
        python scripts/youtube_auth.py --auth-url
        # B) tarayicida onayla, localhost'a yonlendirilen TAM URL'yi al ve
        python scripts/youtube_auth.py --exchange "http://localhost:8765/?code=...&state=..."

     NEDEN IKI ADIM: modern akis PKCE kullanir. `code_challenge`i ureten
     code_verifier ayni surecte yasamali; sureç kapanirsa kod degistirilemez
     (invalid_grant: code_verifier mismatch). Bu yuzden verifier.
     oauth_pending.json'a yazilir ve ikinci komut onu kullanir.

CIKTI: token.json  (refresh_token + client_id + client_secret + scopes)
       Bu dosya .gitignore'da. Icerigi GitHub Secrets'a girilir.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

DEFAULT_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
DEFAULT_REDIRECT_PORT = 8765


def _fail(message: str, code: int = 2) -> None:
    print(f"\n[HATA] {message}\n", file=sys.stderr)
    raise SystemExit(code)


def load_client_secret(path: Path) -> dict:
    """client_secret.json'u dogrular ve icerdigi istemci tipini raporlar."""
    if not path.exists():
        _fail(
            f"{path} bulunamadi.\n"
            "  Google Cloud Console > APIs & Services > Credentials >\n"
            "  Create credentials > OAuth client ID > Application type: **Desktop app**\n"
            "  Indirdigin JSON'u bu konuma `client_secret.json` adiyla koy."
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        _fail(f"{path} gecerli JSON degil: {exc}")
    section = data.get("installed") or data.get("web")
    if not section:
        _fail(
            f"{path} icinde 'installed' bolumu yok. Uygulama turu **Desktop app** olmali; "
            "'Web application' olarak olusturulmussa bu akis calismaz."
        )
    for key in ("client_id", "client_secret"):
        if not section.get(key):
            _fail(f"{path} icinde {key} eksik.")
    return data


def build_flow(client_secret_path: Path, scopes: list[str], port: int):
    from google_auth_oauthlib.flow import InstalledAppFlow

    return InstalledAppFlow.from_client_secrets_file(
        str(client_secret_path), scopes, redirect_uri=f"http://localhost:{port}/"
    )


def write_auth_url(flow, port: int, pending_path: Path, scopes: list[str]) -> None:
    """Adim A: URL uretir ve PKCE verifier'ini diske yazar."""
    auth_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent",  # refresh_token'i ZORUNLU kilar
        include_granted_scopes="false",
    )
    pending = {
        "state": state,
        "code_verifier": flow.code_verifier,
        "redirect_uri": f"http://localhost:{port}/",
        "scopes": scopes,
        "created_at": __import__("datetime").datetime.now(__import__("datetime").UTC).isoformat(),
    }
    pending_path.write_text(json.dumps(pending, indent=2), encoding="utf-8")
    pending_path.chmod(0o600)
    print("\n=== 1) BU URL'YI TARAYICINDA AC (onaylamak istedigin Google hesabiyla) ===\n")
    print(auth_url)
    print(
        f"\n=== 2) Onaydan sonra tarayici http://localhost:{port}/?code=... adresine gider.\n"
        "       Sayfa ACILMAZ / 'baglanti kurulamadi' der - BU NORMALDIR.\n"
        "       Adres cubugundaki TAM URL'yi kopyala ve calistir:\n\n"
        '       python scripts/youtube_auth.py --exchange "http://localhost:%d/?code=...&state=..."\n'
        % port
    )
    print(f"[i] PKCE verifier diske yazildi: {pending_path} (0600). Kod tek kullanimliktir.")


def exchange_code(flow, pending_path: Path, pasted: str) -> None:
    """Adim B: verifier'i diskten yukler ve kodu token ile degistirir."""
    if not pending_path.exists():
        _fail(
            f"{pending_path} yok. Once `python scripts/youtube_auth.py --auth-url` calistir.\n"
            "  (PKCE verifier olmadan kod degistirilemez.)"
        )
    pending = json.loads(pending_path.read_text(encoding="utf-8"))
    verifier = pending.get("code_verifier")
    if not verifier:
        _fail("pending dosyasinda code_verifier yok; --auth-url adimini yeniden calistir.")
    flow.code_verifier = verifier

    code = pasted.strip()
    if "code=" in pasted:
        query = parse_qs(urlparse(pasted).query)
        if "error" in query:
            _fail(f"Google onayi reddetti: {query['error'][0]}")
        if "code" not in query:
            _fail("URL icinde 'code' parametresi bulunamadi.")
        if pending.get("state") and query.get("state") and query["state"][0] != pending["state"]:
            _fail("state uyusmuyor (CSRF korumasi). --auth-url adimini yeniden calistir.")
        code = query["code"][0]

    print("[..] Kod token ile degistiriliyor...")
    flow.fetch_token(code=code)
    pending_path.unlink(missing_ok=True)


def run_manual(flow, port: int) -> None:
    """Kopyala-yapistir akisi: kod, tarayicidan gelen URL'den cikarilir."""
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",  # refresh_token'i ZORUNLU kilar
        include_granted_scopes="false",
    )
    print("\n=== 1) BU URL'YI TARAYICINDA AC (onaylamak istedigin Google hesabiyla) ===\n")
    print(auth_url)
    print(
        f"\n=== 2) Onaydan sonra tarayici http://localhost:{port}/?code=... adresine gider.\n"
        "       Sayfa acilmaz / 'baglanti kurulamadi' der - BU NORMALDIR.\n"
        "       Adres cubugundaki TAM URL'yi kopyalayip asagi yapistir. ===\n"
    )
    pasted = input("Yonlendirme URL'si (veya sadece code degeri): ").strip()
    if not pasted:
        _fail("Bos girdi. Iptal edildi.")

    code = pasted
    if "code=" in pasted:
        query = parse_qs(urlparse(pasted).query)
        if "error" in query:
            _fail(f"Google onayi reddetti: {query['error'][0]}")
        if "code" not in query:
            _fail("URL icinde 'code' parametresi bulunamadi.")
        code = query["code"][0]

    print("\n[..] Kod token ile degistiriliyor...")
    flow.fetch_token(code=code)


def run_loopback(flow, port: int) -> None:
    print(f"\n[..] http://localhost:{port}/ uzerinde yerel sunucu dinleniyor...")
    print(f"     Uzak makinedeysen: ssh -L {port}:localhost:{port} kullanici@sunucu")
    flow.run_local_server(
        port=port,
        open_browser=False,
        access_type="offline",
        prompt="consent",
        authorization_prompt_message="Su URL'yi ac: {url}",
        success_message="Yetkilendirme tamam. Bu pencereyi kapatabilirsin.",
    )


def save_token(creds, client_secret: dict, token_path: Path, scopes: list[str]) -> None:
    if not creds.refresh_token:
        _fail(
            "refresh_token alinamadi.\n"
            "  Neden: hesap bu uygulamaya daha once izin vermis ve Google yeni refresh_token\n"
            "  uretmedi. Cozum: https://myaccount.google.com/permissions adresinden uygulama\n"
            "  erisimini KALDIR, sonra bu scripti tekrar calistir."
        )
    section = client_secret.get("installed") or client_secret.get("web") or {}
    payload = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id or section.get("client_id"),
        "client_secret": creds.client_secret or section.get("client_secret"),
        "scopes": scopes,
        "universe_domain": getattr(creds, "universe_domain", "googleapis.com"),
        "expiry": creds.expiry.isoformat() if creds.expiry else None,
    }
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    token_path.chmod(0o600)

    rt = payload["refresh_token"]
    print(
        "\n[OK] token.json yazildi: "
        f"{token_path} (0600)\n"
        f"     refresh_token: {rt[:6]}...{rt[-4:]}  <-- sadece ozet, tam deger gizlendi\n"
        f"     scopes: {', '.join(scopes)}\n"
        "\n=== GITHUB SECRETS (Settings > Secrets and variables > Actions) ===\n"
        f"  YT_CLIENT_ID      = {payload['client_id']}\n"
        "  YT_CLIENT_SECRET  = (client_secret.json icindeki deger)\n"
        "  YT_REFRESH_TOKEN  = (token.json icindeki refresh_token)\n"
    )
    print(
        "[!] UYARI - EN KRITIK MADDE:\n"
        "    OAuth consent screen 'Testing' modundaysa Google refresh_token'i **7 gun**\n"
        "    sonra gecersiz kilar ve 7/24 otomasyon sessizce olur.\n"
        "    Cozum: OAuth consent screen > 'PUBLISH APP' (uygulama 'In production'\n"
        "    ama dogrulanmamis olur; 100 kullanici siniri + uyari ekrani).\n"
        "    Denetlenmemis proje oldugu icin yuklemeler yine PRIVATE kalir -\n"
        "    zaten istedigimiz bu.\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="YouTube OAuth2 yetkilendirmesi")
    parser.add_argument("--client-secret", default="client_secret.json", type=Path)
    parser.add_argument("--token-out", default="token.json", type=Path)
    parser.add_argument("--mode", choices=["auto", "manual", "loopback"], default="auto")
    parser.add_argument("--port", default=DEFAULT_REDIRECT_PORT, type=int)
    parser.add_argument("--auth-url", action="store_true", help="Adim A: yetkilendirme URL'si uret")
    parser.add_argument(
        "--exchange", metavar="REDIRECT_URL", help="Adim B: kodu token ile degistir"
    )
    parser.add_argument("--pending", default=".oauth_pending.json", type=Path)
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Sadece yapilandirmayi dogrula ve yetkilendirme URL'sini bas (token alinmaz).",
    )
    parser.add_argument("--scopes", nargs="*", default=DEFAULT_SCOPES)
    args = parser.parse_args()

    print("=== ShortForge / YouTube OAuth2 ===")
    client_secret = load_client_secret(args.client_secret)
    section = client_secret.get("installed") or client_secret.get("web") or {}
    print(f"client_id: {str(section.get('client_id'))[:18]}...")
    print(f"scopes   : {', '.join(args.scopes)}")
    print(f"redirect : http://localhost:{args.port}/")

    mode = args.mode
    if mode == "auto":
        mode = "loopback" if sys.stdin.isatty() and sys.platform != "linux" else "manual"

    flow = build_flow(args.client_secret, args.scopes, args.port)

    if args.exchange:
        exchange_code(flow, args.pending, args.exchange)
        save_token(flow.credentials, client_secret, args.token_out, args.scopes)
        return 0

    if args.auth_url:
        write_auth_url(flow, args.port, args.pending, args.scopes)
        return 0

    if args.check_only:
        url, _ = flow.authorization_url(
            access_type="offline", prompt="consent", include_granted_scopes="false"
        )
        print("\n[OK] Yapilandirma gecerli. Yetkilendirme URL'si:\n")
        print(url)
        print("\n(--check-only: token alinmadi)")
        return 0

    if mode == "manual":
        write_auth_url(flow, args.port, args.pending, args.scopes)
        print("\n[i] Sonraki adim: --exchange ile kodu degistir.")
        return 0
    else:
        run_loopback(flow, args.port)

    save_token(flow.credentials, client_secret, args.token_out, args.scopes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
