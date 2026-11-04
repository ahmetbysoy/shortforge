# PROMPT P0 — İskelet, Sağlayıcı Katmanı ve Kota Defteri

> Ajan için: bu promptu olduğu gibi uygula. Kapsam dışına çıkma. Bitince **"Rapor Formatı"** bölümündeki şablonla dön.

---

## 0. Bağlam ve sabit kurallar

Proje: **shortforge** — dikey YouTube Shorts (1080x1920, 30–60 sn) üreten, ürettiğini YouTube'a **önce `private`** yükleyen, insan onayından sonra `public` yapan uçtan uca Python hattı.
Ortam: Debian 13, Python 3.13, root var, **RAM 1.9 GB** (bellek cimrisi ol). Üretim: GitHub Actions `ubuntu-latest`.

Değişmez kurallar:
1. **Sadece ücretsiz katman.** Ücretli API, kredi kartı, trial yok. Limit/kredi tüketen hiçbir çağrı `quota.py` defterinden geçmeden yapılmaz.
2. **Tek sağlayıcıya bağımlılık yok.** Her yetenek (`image`, `tts`, `music`, `llm`, `publish`) için en az 2 uygulama; seçim `health()` ile runtime'da yapılır.
3. **Başkasının içeriği indirilmez.** Stok kullanılırsa yalnızca Pexels/Pixabay/Openverse gibi lisanslı API'lerden; her varlığın lisans kaydı `assets/license/manifest.json`'a yazılır.
4. **Consumer AI sitelerinin (Kling, Runway, Pika, Sora vb.) Playwright/Selenium ile otomasyonu YASAK.** ToS ihlali. Playwright sadece ileride, izin verilen yerlerde kullanılacak; bu aşamada hiç kurulmayacak.
5. **Sır yok.** Anahtar sadece `.env`/env değişkeni; `.env` git'e girmez. Loglarda token/anahtar maskelenir.
6. Python 3.13'te bir wheel yoksa **3.12'ye düşme** — dur, bana sor, alternatif paket öner.

## 1. Kapsam (yalnızca bunlar)

### 1.1 Repo iskeleti
`docs/00-MIMARI.md`'deki dizin yapısını kur. `pyproject.toml` tek kaynak (PEP 621, `hatchling`), entrypoint: `shortforge = shortforge.cli:app`.
Bağımlılıkları **pinle** (`==`). Bu aşamada yalnızca: `typer`, `rich`, `pydantic`, `pydantic-settings`, `httpx`, `tenacity`, `structlog`, `python-dotenv`. Dev: `pytest`, `pytest-asyncio`, `respx`, `ruff`, `mypy`, `pre-commit`. **moviepy / opencv kurma.** `edge_tts` ve `piper` de bu aşamada kurulmaz (yalnızca protokol + health stub'ı).
Kurulum `pip install -e ".[dev]"` ile tek komutta çalışmalı. `Makefile`: `doctor`, `test`, `test-live`, `lint`, `fmt`, `type`.

### 1.2 `config.py`
`pydantic-settings` ile: `log_level`, `env`, `dry_run: bool = True`, `daily_video_limit: int = 1`, `yt_client_id/secret/refresh_token`, `gemini_api_key`, `pexels_api_key`, `pollinations_token` (opsiyonel), `tts_voice_tr` (varsayılan `tr-TR-AhmetNeural`), `paths`. Eksik zorunlu anahtar → uygulama **çökmez**, `doctor`'da `MISSING` gösterir. `.env.example` tüm anahtarları yorumlu yazar.

### 1.3 `providers/base.py` + `registry.py`
```python
class Capability(StrEnum): IMAGE, TTS, MUSIC, LLM, PUBLISH
@dataclass Health: status: Literal["OK","DEGRADED","DOWN","MISSING_KEY"]
                    latency_ms: int|None, detail: str, free_tier_note: str
class Provider(Protocol):
    name: str; capability: Capability; cost_units: int
    async def health(self) -> Health: ...
```
`registry.resolve(capability)` → öncelik listesine göre ilk `OK`/`DEGRADED` sağlayıcı; hiçbiri yoksa `NoProviderAvailable` (anlamlı, eyleme dönük mesajla). `resolve` sonucu loglanır: `chosen`, `rejected[] + neden`.
Ortam değişkeniyle override: `SHORTFORGE_IMAGE_PROVIDER=pexels`.

### 1.4 Sağlayıcı stub'ları (bu aşamada gerçek üretim yok, **sadece health**)
- `image_pollinations.py` — `HEAD/GET` ile `image.pollinations.ai` erişilebilirliği (gerçek görsel indirme yok; 1 küçük istek, 10 sn timeout). Ücretsiz not: "anonim ~1 istek/15 sn, filigran olabilir; auth ile kalkar".
- `image_pexels.py` — anahtar yoksa `MISSING_KEY`; varsa `GET /v1/search?per_page=1`.
- `image_local.py` — **her zaman OK**, bağımlılık yok (PIL ile prosedürel fallback; bu aşamada yalnızca `health()`).
- `tts_edge.py` — import edilebilirlik + servis erişimi kontrolü (`edge_tts` kurulu değilse `DOWN` + nasıl kurulacağı). `piper` için `tts_piper.py` aynı mantık, binary yoksa `MISSING_KEY`.
- `music_openverse.py` — `GET /v1/audio/?q=ambient&page_size=1`.
- `llm_gemini.py` — anahtar yoksa `MISSING_KEY`; varsa `models` listesi.
- `youtube.py` — **sadece kota/health**: `refresh_token` yoksa `MISSING_KEY`; varsa token yenileme denemesi **yapma**, sadece yapılandırma varlığını raporla (gerçek OAuth P4'te). `cost_units=1600`, `free_tier_note="10k birim/gün; 6 yükleme/gün varsayımı — panelden doğrula"`.

Tüm ağ çağrıları `httpx.AsyncClient(timeout=10)` + `tenacity` (3 deneme, exponential+jitter).

### 1.5 `quota.py` — kota defteri (bu aşamanın kalbi)
- SQLite `state/state.db`, tablo `quota_usage(date_pt TEXT, provider TEXT, units INT)`.
- `date_pt` = **Pasifik saatine göre** gün (kota sıfırlanma kuralı). `zoneinfo` ile, hard-coded offset yok.
- API: `reserve(provider, units)`, `spend(provider, units)`, `remaining(provider)`, `assert_can_afford(...)`.
- YouTube için tavan varsayılan **6 yükleme/gün** (muhafazakâr); `YT_DAILY_UPLOAD_CAP` ile ayarlanabilir.
- Aşımda `QuotaExceeded` — mesaj net olmalı: "Bugünkü yükleme hakkı bitti (Pasifik 00:00'da yenilenir)".
- YouTube'a dair tüm çağrılar **zorunlu** olarak `quota.assert_can_afford()` üzerinden geçer (bu aşamada çağrı yok; kural kodla ve testle kilitlenir).

### 1.6 `models.py`
`Script`, `Scene`, `VideoJob` şemaları (MIMARI §2'deki alanlar). `Script` doğrulaması: 3–7 sahne, hook ≤ 90 karakter, `hashtags` 3–5 adet, `sources` zorunlu (boşsa uyarı). JSON şeması `docs/schemas/script.schema.json` olarak export edilsin.

### 1.7 `doctor` CLI
`shortforge doctor [--json]` → rich tablo + `--json` ile makine-okur çıktı:
```
Sağlayıcı        Yetenek  Durum       Gecikme  Ücretsiz katman notu
pollinations     image    OK          412 ms   1 istek/15 sn, filigran olabilir
pexels           image    MISSING_KEY    -     anahtar yok → fallback atlanır
local            image    OK            0 ms    sınırsız, filigransız
edge_tts         tts      DOWN           -     paket kurulu değil
youtube          publish  MISSING_KEY    -     10k birim/gün ≈ 6 yükleme
KOTA: bugün 0/10000 birim | yükleme 0/6 | sıfırlanma: 2026-11-05 00:00 PT (7s 12dk)
MİMARİ: python 3.13.16 | RAM 1.9 GiB | ffmpeg: var/yok | disk: 21 GiB boş
```
`doctor` **ağ hatası yüzünden sıfırdan farklı kodla çıkmaz** (exit 0, durum tabloda). `--strict` ile DOWN varsa exit 1.

### 1.8 Testler
- Unit: registry seçim/fallback mantığı, quota defteri (Pasifik gün geçişi **fake clock** ile test edilir; PST/PDT farkı), `Script` doğrulama, config eksik anahtar davranışı, log maskeleme.
- Hiçbir unit test ağa çıkmaz (`respx` mock). Ağa çıkan testler `@pytest.mark.live`, varsayılan **deselect**.
- Kapsam hedefi: çekirdek modüllerde ≥ %80 (`quota`, `registry`, `models`, `config`).

### 1.9 CI (`.github/workflows/ci.yml`)
`ubuntu-latest`, matrix: py3.13. Adımlar: `ruff format --check`, `ruff check`, `mypy src`, `pytest -m "not live"`. Sır gerektirmez. Ayrı `keepalive.yml`: her 3 günde bir `state/keepalive.txt`'e tarih yazan commit (60 gün hareketsizlik iptaline karşı).

### 1.10 `docs/DECISIONS.md`
Bu aşamada verdiğin her teknik kararı (paket seçimi, quota modeli, fallback sıralaması) 1 satır gerekçeyle yaz. `assets/license/manifest.json` boş şablon olarak dursun.

## 2. Açıkça YAPMA
- Video render, TTS ses üretimi, görsel indirme, YouTube OAuth akışı, Playwright, MoviePy.
- `requests` (sadece `httpx`), `print` (sadece `structlog`/`rich`).
- `git push` / commit — **sadece yerel dosyalar**. Repo/secret işlemleri bende.
- Anahtar uydurma; eksikse `MISSING_KEY` döndür.

## 3. Bitirme kontrol listesi (kendi kendine doğrula)
- [ ] `pip install -e ".[dev]"` temiz kurulum (venv içinde)
- [ ] `shortforge doctor` çalışıyor, tablo + `--json` doğru
- [ ] `pytest -m "not live"` yeşil, `ruff`/`mypy` temiz
- [ ] `quota` gün geçişi testi geçiyor (PDT/PST)
- [ ] `.env.example` tüm anahtarları içeriyor, `.gitignore` `state/`, `out/`, `.env` kapsıyor
- [ ] Hiçbir dosyada gerçek anahtar yok (`grep -rE "AIza|sk-|ya29\." .` → boş)
- [ ] `docs/DECISIONS.md` dolu

## 4. Rapor Formatı (bunu doldurup bana gönder)
```
## P0 RAPORU
1) Kurulum: python sürümü | kurulan paket sayısı | süre | hata var mı
2) doctor çıktısı: (tablo aynen yapıştır) + --json'dan 3 satır
3) Test sonucu: passed/failed | kapsam %'si | atlanan live testler
4) Kota defteri: gün geçişi testinin çıktısı (1-2 satır)
5) Kararlar: DECISIONS.md'deki 3-5 madde
6) Sapmalar: promptan saptığın her nokta + gerekçe
7) Blokajlar: 3.13'te wheel sorunu, eksik anahtar, RAM uyarısı vb.
8) Sıradaki adım için önerin: (tek paragraf)
```
Raporunda **abartılı iyimserlik yok**: çalışmayan şeyi "çalışıyor" deme, DOWN olan sağlayıcıyı DOWN yaz.
