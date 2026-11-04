# P0 RAPORU — İskelet, sağlayıcı katmanı, kota defteri

**Tarih:** 2026-11-04 · **Sürüm:** 0.1.0 · **Durum:** ✅ tamam (CI yeşil)

## 1. Kurulum
- Python **3.13.16**, `pip install -e ".[dev]"` tek komutla temiz.
- 40 paket kuruldu (core 9 + dev 6 + transitif). Hata yok.
- `pillow` bağımlılığa eklendi: son savunma hattı görsel sağlayıcısı (`local`) Pillow olmadan DOWN'a düşüyordu.

## 2. `shortforge doctor` çıktısı

```
                                                             ShortForge doctor  (v0.1.0)                                                              
┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Saglayici    ┃ Yetenek     ┃ Durum       ┃ Gecikme ┃ Ucretsiz katman notu                          ┃ Detay                                         ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ pollinations │ gorsel      │ OK          │  379 ms │ anonim: ~1 istek/15 sn, filigran olabilir |   │ HTTP 200, 2356 bayt (anonim: filigran         │
│              │             │             │         │ kayitli: limit yuksek, filigran yok           │ olabilir)                                     │
│ pexels       │ gorsel      │ MISSING_KEY │       - │ ucretsiz API: 200 istek/saat, 20.000/ay |     │ PEXELS_API_KEY yok - yedek zincirde atlanir   │
│              │             │             │         │ lisansli stok (atif sart degil)               │                                               │
│ local        │ gorsel      │ OK          │    0 ms │ sinirsiz, anahtarsiz, filigransiz             │ Pillow hazir, dis bagimlilik yok              │
│              │             │             │         │ (prosedurel; AI modeli degil)                 │                                               │
│ edge_tts     │ seslendirme │ DOWN        │       - │ ucretsiz, anahtarsiz, filigransiz | resmi     │ edge-tts kurulu degil: pip install edge-tts   │
│              │             │             │         │ olmayan servis (blok riski)                   │ (P2'de kurulur)                               │
│ piper        │ seslendirme │ MISSING_KEY │       - │ MIT, offline, sinirsiz | ses modeli           │ piper binary yok (pip install piper-tts +     │
│              │             │             │         │ indirilirse calisir                           │ tr_TR modeli)                                 │
│ openverse    │ muzik       │ OK          │  123 ms │ ucretsiz, anahtarsiz (anonim rate-limit) |    │ HTTP 200                                      │
│              │             │             │         │ yalniz CC/CC0 icerik                          │                                               │
│ gemini       │ senaryo     │ MISSING_KEY │       - │ ucretsiz katman (gunluk istek limiti) | veri  │ GEMINI_API_KEY yok - Groq yedegine dusulur    │
│              │             │             │         │ urun gelistirmede kullanilabilir              │                                               │
│ youtube      │ yayin       │ MISSING_KEY │       - │ 10.000 birim/gun | videos.insert 1600 birim ~ │ eksik: YT_CLIENT_ID, YT_CLIENT_SECRET,        │
│              │             │             │         │ 6 yukleme/gun (2026-06'dan beri ayri kota     │ YT_REFRESH_TOKEN (OAuth P4'te kurulur)        │
│              │             │             │         │ kovasi iddiasi var - panelden dogrula)        │                                               │
└──────────────┴─────────────┴─────────────┴─────────┴───────────────────────────────────────────────┴───────────────────────────────────────────────┘
KOTA bugun 0/9600 birim | yukleme 0/6 | sifirlanma: 2026-11-05T08:00Z (~13s 59dk)
MIMARI python 3.13.16 | Linux | RAM 1.9 GiB | ffmpeg: YOK | disk 19.8 GiB bos | dry_run=True
Gizlilik: yuklemeler daima PRIVATE baslar; public'e alma yalniz insan onayiyla.
```

## 3. Kalite kapıları
| Kontrol | Yerel | GitHub CI |
|---|---|---|
| `ruff format --check` | ✅ | ✅ |
| `ruff check` | ✅ | ✅ |
| `mypy src` (strict) | ✅ 20 dosya | ✅ |
| `pytest -m "not live"` | ✅ **36 passed** | ✅ |
| Sır taraması | ✅ temiz | ✅ (`run 41882533969`) |
| Gerçek ağ testleri | 4 servis canlı | — |

## 4. Kota defteri doğrulaması
- Pasifik gün geçişi 4 senaryoda test edildi: yaz (PDT, UTC-7) ve kış (PST, UTC-8) için ayrı ayrı gece yarısı sınırı.
- 7. yükleme denemesi `QuotaExceeded` fırlatıyor; mesaj sıfırlanma saatini içeriyor.
- `YouTubeProvider.preflight_upload()` / `preflight_publish()` kota kapısını zorunlu kılıyor — P4'te yükleme kodu bu metodu atlamadan çağıramaz.

## 5. Sağlayıcı durumu (gerçek ölçüm)
| Sağlayıcı | Durum | Not |
|---|---|---|
| pollinations | **OK** (~550 ms) | anonim çalışıyor; filigran riski kayıtla kalkar |
| local (PIL) | **OK** | anahtarsız, sınırsız son savunma hattı |
| openverse | **OK** (~190 ms) | CC0 müzik araması canlı |
| pexels | MISSING_KEY | anahtar eklenince devreye girer (200 istek/saat) |
| edge_tts | DOWN | paket P2'de kurulacak — **beklenen** |
| piper | MISSING_KEY | binary + tr_TR modeli P2'de |
| gemini | MISSING_KEY | anahtar P1'de |
| youtube | MISSING_KEY | OAuth P4'te; anahtarlar gelince OK'e döner |

**Ortam notu:** bu sandbox'ta `ffmpeg` yok; P3'te `apt-get install ffmpeg` ile kurulacak (GitHub Actions `ubuntu-latest` imajında hazır geliyor).

## 6. Kararlar
Ayrıntı: [`DECISIONS.md`](DECISIONS.md) — 10 madde. Öne çıkanlar:
1. Render MoviePy değil **FFmpeg** (1.9 GB RAM'de OOM riski).
2. Görsel = **AI görsel + FFmpeg hareket**; gerçek T2V ücretsiz API'si 2026'da yok.
3. Görsel fallback zinciri: **pollinations → pexels → local(PIL)**; hat asla durmaz.
4. TTS: **edge_tts birincil, Piper yedek** (edge_tts CI IP'lerinde bloklanabilir).
5. Kota defteri **Pasifik** saat diliminde, SQLite'ta; 6 yükleme/gün muhafazakâr tavan.
6. Repo **public** → Actions dakikası sınırsız (private'ta 2.000 dk/ay).

## 7. Sapmalar
- Planlanan 8 sağlayıcıya ek olarak `pillow` bağımlılığı eklendi (zorunlu düzeltme).
- CI'a "sır taraması" adımı eklendi; ilk çalıştırmada test fixture'ındaki sahte `ya29.` literali yanlış pozitif verdi → hem desen sıkılaştırıldı hem fixture parçalandı.

## 8. Blokajlar
Yok. Uyarı: `ffmpeg` bu ortamda yok (P3'te kurulacak); `edge_tts` bilinçli olarak kurulmadı.

## 9. Sıradaki adım (P1)
`Script` şeması hazır ve test edilmiş durumda ([`schemas/script.schema.json`](schemas/script.schema.json)). P1'de:
1. `content/idea.py` — konu havuzu + tekrar kontrolü (SQLite `jobs` tablosu).
2. `content/script.py` — Gemini free tier ile JSON-mode üretim, şema doğrulaması, 2 kez retry + Groq fallback.
3. `shortforge script --topic "..." --dry-run` komutu; çıktı `out/<job_id>/script.json`.
4. `@pytest.mark.live` ile 1 gerçek Gemini çağrısı (anahtar gelince).
