# ShortForge — Mimari ve Araç Matrisi (v1.0)

> Proje: Ücretsiz katmanlarla dikey YouTube Shorts üretimi + **private** yükleme + insan onayıyla public'e alma.
> Hedef ortam: Debian 13 (geliştirme/test) → GitHub Actions `ubuntu-latest` (7/24 üretim, `schedule` cron).
> Format: 1080x1920, 30–60 sn, ilk 3 sn hook, kelime senkronlu gömülü altyazı.

---

## 1. Araç Matrisi (ücretsiz katman, limit, filigran, kredi)

| Katman | Birincil | Ücretsiz limit / kredi | Filigran | Yedek (fallback) | Risk |
|---|---|---|---|---|---|
| **Senaryo (LLM)** | Gemini API (free tier) | Günlük istek/dakika limiti var, kredi kartı gerekmez; ücretsiz katmanda veri ürün geliştirmeye kullanılabilir | Yok | Groq free → Pollinations `text` endpoint | Limit değişimi |
| **Görsel üretimi (AI)** | Pollinations `image.pollinations.ai` (Flux) | Anonim: ~15 sn'de 1 istek, günlük tavan belirsiz; `auth.pollinations.ai` kaydı limiti artırır | Anonimde **olabilir**; kayıtta kalkar | Pexels/Pixabay API (lisanslı stok, 200 istek/saat) → **yerel prosedürel** (PIL/OpenCV, sınırsız) | Anonim kuyruk/429 |
| **Gerçek text-to-video** | **KAPSAM DIŞI** (ücretsiz API yok) | HF ücretsiz Inference kredileri 07.10.2026'da kaldırıldı; kalan "free" T2V'ler consumer web + filigran | — | Opsiyonel: self-host Wan/LTX (GPU gerekir) | Sıfır maliyetle üretimde sürdürülemez |
| **Hareket / efekt** | FFmpeg `zoompan` (Ken Burns), parallax, `xfade` | Sınırsız, yerel | Yok | OpenCV kare üretimi | CPU süresi |
| **Seslendirme (TTS)** | `edge-tts` (tr-TR Ahmet/Emel) | Ücretsiz, anahtarsız, resmî olmayan servis | Yok | **Piper** (MIT, offline, `tr_TR` modelleri) | GitHub Actions IP'lerinde 403/403-benzeri blok riski → yedek zorunlu |
| **Altyazı zamanlaması** | `edge-tts` **WordBoundary** olayları — `boundary="WordBoundary"` **zorunlu** (varsayılan `SentenceBoundary`), ASR gerekmez | Ücretsiz | Yok | `faster-whisper` (CPU, int8, MIT) | edge-tts yedeğe düşerse ASR gerekir |
| **Altyazı yakma** | FFmpeg `ass` filtresi (burn-in) + `.srt` yedeği | Sınırsız | Yok | — | Font/emoji desteği |
| **Müzik** | Openverse API (CC lisanslı, anahtarsız) | Ücretsiz, rate-limit'li | Yok | Repoya gömülü CC0 parça kütüphanesi (10–20 parça) | Lisans kaydı zorunlu |
| **Kapak (thumbnail)** | PIL ile yerel kompozisyon | Sınırsız | Yok | — | — |
| **Yükleme** | YouTube Data API v3 `videos.insert` | 10.000 birim/gün; `videos.insert` klasik tabloda **1.600 birim (≈6 yükleme/gün)**. 2026 Haziran'dan itibaren `videos.insert` ve `search.list` için ayrı ~100 çağrı/gün kovası bildiren kaynaklar da var → **panelden doğrulanacak** | Platform filigranı yok | Playwright ile YouTube Studio otomasyonu (son çare, kırılgan) | Kota + denetim |
| **Public'e alma** | `videos.update` (privacyStatus=public) | 50 birim/çağrı | — | — | **Denetimsiz projede private kalır** |

### Kota bütçesi (muhafazakâr varsayım)
```
videos.insert       1.600
thumbnails.set         50
videos.update (public) 50
videos.list            1
──────────────────────────
1 video tam döngü ≈ 1.701 birim  →  10.000 / 1.701 ≈ 5 video/gün (teorik)
Operasyonel hedef: 1–2 video/gün, `state/quota.json` defteri ile hard-stop.
```
Kota **Pasifik gece yarısı** sıfırlanır → cron UTC 06:00 ≈ Pasifik 22:00–23:00, gün sınırına yakın; bu yüzden cron **UTC 09:00** (Pasifik ~01:00) seçilir, kota günün başında taze olur.

### Denetim (audit) gerçeği
- Denetlenmemiş (unverified) API projesi → `videos.insert` ile gelen video **private kalır**, `videos.update` ile public'e çekilemez. `privacyStatus` public gönderilse bile YouTube private'a düşürür.
- Bu yüzden üretim hattı **baştan** iki aşamalı: `upload(private)` → insan onayı → `publish(public)`.
- Onay mekanizması: GitHub Issue'ya `approve` etiketi (veya Issue'ya `approved` yorumu) → `publish.yml` workflow'u tetiklenir. Kota dostu (50 birim).

---

## 2. Katmanlı mimari

```
┌──────────────────────────────────────────────────────────────────┐
│  ORKESTRASYON  (pipeline/runner.py — async, retry + dead-letter)  │
└──────────────────────────────────────────────────────────────────┘
        │                    │                    │
┌───────────────┐   ┌────────────────┐   ┌──────────────────────┐
│ 1. İÇERİK     │   │ 2. MEDYA       │   │ 3. YAYIN             │
│ topic → script│   │ tts → görsel   │   │ upload(private)      │
│ hook, sahne   │   │ → altyazı →    │   │ → onay → publish     │
│ JSON şeması   │   │ ffmpeg render  │   │ → kota defteri       │
└───────────────┘   └────────────────┘   └──────────────────────┘
        └────────────────┬───────────────────────┘
┌──────────────────────────────────────────────────────────────────┐
│  ÇEKİRDEK: providers/registry (capability + health), quota.py,    │
│  state.py (SQLite), config.py (pydantic-settings), logging.py     │
└──────────────────────────────────────────────────────────────────┘
```

**Bağımlılık tersine çevirme:** Pipeline asla `import edge_tts` / `requests.pollinations` yapmaz. Sadece `TTSProvider`, `ImageProvider`, `MusicProvider`, `Publisher` protokollerini bilir. Yedek seçim `registry.resolve(capability)` + `health()` sonucu ile yapılır. Bir sağlayıcı düşerse sadece `providers/` altındaki dosya değişir.

### Dizin yapısı
```
shortforge/
├─ pyproject.toml            # tek kaynak: deps + tool config + CLI entrypoint
├─ .env.example              # tüm anahtarlar, değersiz
├─ Makefile                  # doctor / test / render / upload / publish
├─ .github/workflows/
│  ├─ ci.yml                 # lint + type + unit (network yok)
│  ├─ produce.yml            # cron: üret → private yükle → artifact+Issue
│  ├─ publish.yml            # issue etiketi → public
│  └─ keepalive.yml          # 60 gün hareketsizlik iptaline karşı
├─ src/shortforge/
│  ├─ cli.py  __main__.py    # typer CLI
│  ├─ config.py  errors.py  logging.py  models.py  state.py  quota.py
│  ├─ content/    (idea.py, script.py, prompts/)
│  ├─ media/      (tts.py, visuals.py, subtitles.py, music.py, render.py, thumbnail.py)
│  ├─ providers/  (base.py, registry.py, image_pollinations.py, image_pexels.py,
│  │               image_local.py, tts_edge.py, tts_piper.py,
│  │               music_openverse.py, llm_gemini.py, youtube.py)
│  ├─ publish/    (uploader.py, privacy.py, approve.py)
│  └─ pipeline/   (runner.py, stages.py)
├─ assets/fonts/  assets/music/  assets/license/
├─ state/         (gitignore: *.db, quota.json, render cache)
├─ out/           (gitignore: üretilen mp4 + preview)
├─ tests/         (unit + `@pytest.mark.live` ayrı)
└─ docs/          (MIMARI, DECISIONS.md, PROMPT geçmişi)
```

### Veri modeli (pydantic, tek doğruluk kaynağı)
```python
Scene   = {index, narration, image_prompt, motion, duration_hint}
Script  = {topic, hook, scenes[3..7], cta, hashtags[], sources[]}
VideoJob= {job_id, script, audio_path, image_paths[], ass_path, mp4_path,
           privacy:"private", status: draft|rendered|uploaded|approved|published}
```
`Script` **JSON şemasına zorlanır** (LLM çıktısı parse edilemezse 2 kez retry, sonra fallback model). Bu, "video yarıda patlıyor" hatalarının %80'ini keser.

### Render hattı (tek FFmpeg geçişi, bellek dostu — 1.9 GB RAM sınırı)
```
görsel N → scale/crop 1080x1920 → zoompan (Ken Burns) → xfade zinciri
        + narration.wav (loudnorm) + music.mp3 (sidechaincompress ≈ ducking)
        → subtitles=out.ass → libx264 -crf 21 -preset veryfast → +faststart
```
MoviePy kullanılmaz (RAM/CPU şişirir). Her sahne ayrı ara dosya olarak render edilip `concat` demuxer ile birleştirilir → OOM riski minimal, kaldığı yerden devam edilebilir.

### Dayanıklılık kuralları
- Her sağlayıcı çağrısı: `timeout` + exponential backoff (jitter) + 3 deneme + anlamlı hata sınıfı.
- Her aşama çıktısı diske **atomik** yazılır (`*.tmp` → `rename`); job durumu SQLite'ta → yarıda kesilen iş tekrar çalıştığında kaldığı yerden devam eder (idempotency anahtarı: `topic+date`).
- Günlük üretim limiti: 1 video. Hata olursa Issue açılır, sessizce yutulmaz.

---

## 3. Risk kaydı ve önlemler

| # | Risk | Etki | Önlem |
|---|---|---|---|
| R1 | Denetimsiz proje → video private kalır | Public yayın imkânsız | Baştan private→onay→publish akışı; audit formu erken gönderilir |
| R2 | `edge-tts` GitHub Actions IP'lerinde bloklanır | Seslendirme yok | Piper offline yedeği + CI'da ilk iş "tts canary" |
| R3 | Pollinations anonim limit/429 | Görsel üretimi durur | Pexels → yerel prosedürel yedek zinciri |
| R4 | Scheduled workflow 60 gün hareketsizlikte devre dışı | Otomasyon sessizce ölür | `keepalive.yml` her 3 günde bir commit/issue; ayrıca başarısızlıkta Issue |
| R5 | YouTube kota (6/gün varsayımı vs 100/gün iddiası) | Toplu üretimde 403 | `quota.py` defteri + panelden doğrulama; günlük 1–2 video |
| R6 | GitHub Actions ücretsiz dakika (private repo 2.000 dk/ay) | Kota aşımı | **public repo** (sınırsız) + `concurrency` kilidi + 1 video/gün ≈ 5–8 dk |
| R7 | Telif/ToS: consumer AI sitelerinin (Kling/Runway) Playwright ile otomasyonu | Hesap banı, kural ihlali | **Yapılmayacak.** Sadece API'si olan ücretsiz servisler + lisanslı stok |
| R8 | AI ile üretilmiş gerçekçi içerik beyanı (YouTube "altered content") | Politika uyarısı | Stüdyo'da beyan alanı + açıklamada `#AI` notu; gerçekçi insan yüzü üretilmez |
| R9 | 1.9 GB RAM'de OOM | Render çöker | Sahne bazlı render + `-threads 2` + `nice`; CI'da 4 GB rahat |
| R10 | Python 3.13 wheel eksikliği (piper/whisper) | Kurulum kırılır | Eksik wheel varsa **bana sor**, 3.12'ye düşürme kararını ben veririm |

---

## 4. Yol haritası (aşama kapıları)

| Aşama | Çıktı | Kapı (bitiş şartı) |
|---|---|---|
| **P0 — İskelet** | repo, config, provider protokolleri, `quota.py`, `doctor` CLI, CI | `shortforge doctor` tüm sağlayıcılar için OK/DOWN raporu verir; testler yeşil |
| **P1 — İçerik** | `Script` şeması + LLM ile senaryo + hook | 5 farklı konuda geçerli `script.json` üretir |
| **P2 — Ses + Altyazı** | edge-tts TTS + WordBoundary → `.ass`, Piper yedeği | 45 sn Türkçe seslendirme + kelime senkron altyazı |
| **P3 — Görsel + Render** | görsel zinciri + Ken Burns + miksaj + 1080x1920 mp4 | Tek komutla 1080x1920, 30–60 sn, sesi hizalı mp4 |
| **P4 — YouTube** | OAuth, `uploader`, kota defteri, private yükleme | Kanalda private video görünür + kota raporu |
| **P5 — Onay + Otomasyon** | Issue tabanlı approve, cron, keepalive | Etiket → public; 3 gün üst üste cron başarılı |
| **P6 — Cila** | kapak, açıklama şablonu, hashtag, A/B başlık | İlk gerçek yayın |

**Kural:** Her aşama kapısı geçilmeden sonrakine geçilmez. Her aşama sonunda ajan `docs/DECISIONS.md`'ye "ne, neden, neyi riske attı" notu düşer.
