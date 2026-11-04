# Karar Kaydi (ADR-lite)

Her satir: **karar — gerekce — risk**. Yeni kararlar en uste eklenir.

## P0.5 (2026-11-04) — ajan raporu denetimi ve birles.

11. **Kota defterine `action` kolonu** (kabul) — "yukleme = birim/1600" turetimi kapak/guncelleme
    birimleriyle yanlis sayiyordu. Artik `(date_pt, provider, action)` PK'si ve ayri yukleme sayaci.
12. **Birim tavani ve islem tavani bagimsiz** (kabul) — YouTube 10.000 birim/gun API kotasi;
    6 yukleme/gun ayri bir kural. 6x1600=9600 gibi turetilmis tavan yanlisti, kaldirildi.
13. **Sifirlanma suresinde UTC normalizasyonu** (kabul) — ayni tzinfo'lu aware datetime farki
    duvar saatiyle hesaplanir; DST gunlerinde 1 saat kayar. `_as_utc()` + 4 DST testi.
14. **Override = pin** (davranis degisikligi) — pinli saglayici dusukse sessiz fallback YOK.
    Gerekce: sabitlenen saglayici dusunce baskasina kaymak olcumu gecersiz kilar.
15. **Tek env adi, cift ad reddedildi** — `GEMINI_API_KEY` ve `SHORTFORGE_GEMINI_API_KEY`
    birlikte kabul edilmez; hangi degerin kazandigi belirsizligi yanlis anahtarin sessizce
    kullanilmasina yol acar. GitHub Secrets adlari ciplak addir.
16. **Kaynak kod ASCII, dokumanlar Turkce** — ruff RUF001-003 kapatilmaz. String'ler FFmpeg
    filtre argumani, .ass altyazi ve YouTube metadata'sina gidiyor; `i/İ/s` karakterlerinde
    ASS/font/konsol kodlamasi Kirilma riski tasir. Estetik degil, kirilganlik karari.
17. **Kapsam esigi %80 kilitli** (`--cov-fail-under=80`, su an %95.4) — olculmeyen kapsam iddiadir.
18. **`--strict` yalniz bugun uretimi durduran yetenegi denetler** (gorsel). P2'de `tts` eklenir;
    bilincli DOWN olan bir saglayici yuzunden CI'i surekli kirmizi tutmak alarm yorgunlugu yaratir.

## P0 (2026-11-04)

1. **Render icin MoviePy degil FFmpeg filtre zinciri** — 1.9 GB RAM'de MoviePy kareleri
   bellekte tutup OOM'a giriyor; FFmpeg sahne bazli akis halinde calisir. Risk: filtre
   zinciri karmasik, hata ayiklama CLI uzerinden.
2. **Gorsel motoru = AI gorsel + FFmpeg hareket (gercek T2V degil)** — 2026 itibariyla
   ucretsiz T2V API'si yok (HF ucretsiz inference kredileri 07.10.2026'da kaldirildi).
   Risk: "video" hissi hareket/kurgu kalitesine bagli.
3. **Uc katmanli gorsel fallback: pollinations -> pexels -> local(PIL)** — tek servise
   bagimlilik kural 2'yi ihlal eder; `local` anahtarsiz/sinirsiz oldugu icin hat asla durmaz.
   Risk: son katmanda estetik kalite dusuk.
4. **TTS: edge_tts birincil, Piper yedek** — edge_tts Turkce kalitesi yuksek ve WordBoundary
   ile kelime zamanlamasi veriyor (ASR maliyeti sifir). Resmi olmayan servis oldugu icin
   CI IP'lerinde bloklanabilir; bu yuzden Piper (MIT, offline) zorunlu yedek.
5. **Kota defteri Pasifik saat diliminde, SQLite uzerinde** — YouTube kotasi Pasifik gece
   yarisinda sifirlanir; UTC kullanmak gun sinirini 7-8 saat kaydirir. `zoneinfo` ile
   PST/PDT otomatik. Risk: yok (testlerle kilitli).
6. **YouTube yukleme tavani 6/gun varsayildi** — 2026-06'dan beri `videos.insert` icin ayri
   ~100 cagri/gun kovasi oldugunu iddia eden kaynaklar var; panelden dogrulanana kadar
   muhafazakar tavan (`YT_DAILY_UPLOAD_CAP=6`) kullanilir.
7. **Saglayici secimi runtime `health()` ile, override env ile** — imleme/anlasma yerine
   gercek erisim testi; override acil durumda elle mudahale saglar.
8. **Public repo tercih edildi** — GitHub Actions ucretsiz dakika limiti public repolarda
   sinirsiz; private repoda 2.000 dk/ay. Sir yok (yalnizca Secrets). Risk: kod herkese acik.
9. **Consumer AI sitelerinin (Kling/Runway/Pika/Sora) tarayici otomasyonu yasak** — ToS
   ihlali ve hesap banı riski; kural 3'un ruhuna aykiri. Bu yuzden Playwright P0'da kurulmadi.
10. **`docker`/`systemd` yok, GitHub Actions cron hedef** — 7/24 sifir maliyet, cihaz
    bagimsiz. Risk: 60 gun hareketsizlikte cron devre disi -> `keepalive.yml`.
