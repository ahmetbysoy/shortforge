# ShortForge

Ücretsiz katmanlarla **dikey YouTube Shorts** üreten, ürettiğini **önce `private`** yükleyen, insan onayından sonra `public`'e alan uçtan uca Python hattı.

> **Tek cümlelik tasarım kararı:** Ücretli API yok, başkasının videosu yok, tek sağlayıcıya bağımlılık yok. Görsel AI ile üretilir, hareket FFmpeg'den gelir, ses edge-tts'ten, altyazı kelime bazlı zamanlanır, yayın YouTube Data API v3 ile yapılır.

```
Senaryo (Gemini free)  →  Ses (edge-tts → Piper)  →  Görsel (Pollinations → Pexels → Local)
        →  Altyazı (WordBoundary → .ass)  →  FFmpeg render (1080x1920)
        →  YouTube upload (PRIVATE)  →  insan onayı  →  publish (PUBLIC)
```

## Durum

| Aşama | Kapsam | Durum |
|---|---|---|
| **P0** | iskelet, sağlayıcı katmanı, kota defteri, `doctor`, CI | ✅ tamam |
| **P0.5** | iki P0 birleştirme + kota/kapsam sertleştirme | ✅ tamam |
| P1 | senaryo şeması + LLM üretimi + hook | ⏳ |
| P2 | TTS + kelime senkron altyazı | ⏳ |
| P3 | görsel + Ken Burns + render | ⏳ |
| P4 | OAuth + private yükleme | ⏳ |
| P5 | onay (Issue etiketi) + cron otomasyonu | ⏳ |
| P6 | kapak, açıklama şablonu, A/B başlık | ⏳ |

Mimari ve araç matrisi: [`docs/00-MIMARI.md`](docs/00-MIMARI.md) · Kararlar: [`docs/DECISIONS.md`](docs/DECISIONS.md) · Elle yapılacaklar: [`docs/INSAN-GOREVI-01.md`](docs/INSAN-GOREVI-01.md)

## Hızlı başlangıç

```bash
git clone https://github.com/ahmetbysoy/shortforge.git
cd shortforge

python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pre-commit install            # ilk kurulumda bir kez
cp .env.example .env          # anahtarları doldur (hiçbiri zorunlu değil)

shortforge doctor             # sağlayıcı + kota + ortam raporu
shortforge doctor --json      # makine-okur
shortforge doctor --strict    # kullanılabilir görsel sağlayıcı yoksa exit 1
```

`doctor` çıktısı tek bakışta şunu söyler: hangi sağlayıcı ayakta, hangisi anahtar bekliyor, bugün kotadan ne kadar kaldı, bir sonraki sıfırlanma ne zaman.

## Ücretsiz katman sınırları

| Katman | Sağlayıcı | Limit | Filigran | Yedek |
|---|---|---|---|---|
| Görsel | Pollinations (Flux) | anonim ~1 istek/15 sn; kayıtta yükselir | anonimde olabilir, kayıtta kalkar | Pexels → Local (PIL) |
| Görsel | Pexels | 200 istek/saat | yok | Local |
| Ses | edge-tts | ücretsiz, anahtarsız | yok | Piper (MIT, offline) |
| Müzik | Openverse | anonim rate-limit, yalnız CC/CC0 | yok | gömülü CC0 kitaplık |
| Senaryo | Gemini API | günlük istek limiti, kart gerekmez | yok | Groq → Pollinations text |
| Yayın | YouTube Data API v3 | 10.000 birim/gün, `videos.insert` 1600 birim ≈ **6 yükleme/gün** | platform | — |

**Kota gerçeği:** denetlenmemiş (unverified) bir Google Cloud projesinde API ile yüklenen video **private kalır**; `videos.update` ile public'e çekilemez. Proje bu yüzden iki aşamalı tasarlandı: `upload(private)` → onay → `publish(public)`.

## Komutlar

```bash
make install      # geliştirme ortamı
make doctor       # sağlık raporu
make test         # ağa çıkmayan unit testler
make test-live    # gerçek ağ testleri (kapalı)
make lint type    # ruff + mypy strict
make schema       # docs/schemas/script.schema.json üret
make check        # CI ile aynı kontroller (ruff + mypy + pytest + kapsam eşiği)
```

Kalite kapıları: `ruff` (format+lint), `mypy --strict`, `pytest` **%80 kapsam eşiği kilitli**
(ölçülen: %95), sır taraması. Sürümler `requirements-lock.txt` ile sabit.

## Depo yapısı

```
src/shortforge/
├─ cli.py          # typer CLI (doctor, version)
├─ config.py       # pydantic-settings, eksik anahtar çökertmez
├─ quota.py        # Pasifik günlük kota defteri (SQLite)
├─ state.py        # SQLite şema (quota_usage, jobs)
├─ models.py       # Script / Scene / VideoJob + durum makinesi
├─ logging.py      # structlog + sır maskeleme
└─ providers/      # base + registry + 8 sağlayıcı (hepsi health() yazar)
```

**Değişmez kural:** iş modülleri somut sağlayıcıyı import etmez; `registry.resolve(capability)` çağırır. Bir sağlayıcı ölürse yalnızca `providers/` altındaki dosya değişir.

## Yasal çerçeve

- Yalnızca **kendi ürettiğimiz AI içeriği** ve **lisanslı/CC stok** kullanılır; her dış varlık `assets/license/manifest.json`'a işlenir.
- Başkasının videosu indirilmez, consumer AI sitelerinin (Kling/Runway/Pika/Sora) arayüzü tarayıcı otomasyonuyla sürülmez — ToS ihlali.
- AI ile üretilmiş gerçekçi içerik YouTube'ta beyan edilir; gerçekçi insan yüzü üretilmez.

## Lisans

MIT
