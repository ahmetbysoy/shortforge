# Karar Kaydi (ADR-lite)

Her satir: **karar — gerekce — risk**. Yeni kararlar en uste eklenir.

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
