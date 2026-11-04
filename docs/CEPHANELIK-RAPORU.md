# Cephanelik Raporu — Geliştirici Ortamı Ölçümü

**Tarih:** 2026-11-04 · **Ölçüm yöntemi:** komut çıktısı (tahmin yok)

## 1. Sistem

| Kalem | Değer |
|---|---|
| OS | Debian GNU/Linux 13 (trixie) x86_64 |
| Python | **3.13.16** (`/usr/local/bin/python3.13`), venv sorunsuz |
| CPU / RAM | 2 çekirdek / **1.9 GiB** (swap yok) |
| Disk | 25 GB, ~20 GB boş |
| Yetki | `sudo` NOPASSWD |
| Ağ | Dış HTTPS açık (Cloudflare/Google/Microsoft/PyPI erişildi) |
| Kalıcılık | Yalnız `/home/user` kalıcı; **apt/pip ile kurulanlar snapshot dışı** → her oturumda yeniden kurulum |

## 2. Medya araçları — ölçüldü

| Araç | Durum | Not |
|---|---|---|
| ffmpeg / ffprobe | ❌ kurulu değildi → **✅ kuruldu: 7.1.5** (`apt-get install ffmpeg`, ~14 sn) | GitHub Actions `ubuntu-latest`'te hazır geliyor; sandbox'ta her oturumda yeniden kurulur |
| Pillow / OpenCV / numpy | ✅ var | `convert`/`magick` (ImageMagick) da var |
| moviepy | ❌ yok | **kurulmayacak** (RAM gerekçesi, DECISIONS #1) |
| sox | ❌ yok | gerek yok, FFmpeg `loudnorm`/`sidechaincompress` yeterli |

ffprobe doğrulaması: `duration=8.232000, bit_rate=48000` (edge-tts çıktısı okundu).

## 3. edge-tts — canlı test (en riskli varsayımdı)

Microsoft servisine **bu IP'den erişildi**; 2 cümlelik Türkçe sentez 13.15 sn, 78.912 bayt MP3.
Kritik bulgu:

```
edge-tts 7.3.1 | Communicate(..., boundary="SentenceBoundary")  <-- VARSAYILAN
                 -> 1 olay/cümle, kelime zamanlamasi YOK

                 Communicate(..., boundary="WordBoundary")
                 -> 21 kelime olayi: Antik(0.10s,0.59s) Roma'da(0.69s,0.41s) ...
                    son kelime 'uzuyordu' @11.40s   (ses 13.15s: sonda ~1.2s sessizlik)
```

**Sonuç:** P2'de kelime senkron altyazı için `boundary="WordBoundary"` **açıkça** verilmeli.
Varsayılanla yazılırsa altyazı cümle cümle atlar ve bu ancak videoyu izleyince fark edilir.
Sondaki ~1.2 sn sessizlik, `.ass` son kare süresini hesaplarken telafi edilmeli.

## 4. Tarayıcı otomasyonu — ölçüldü

`playwright` + `chromium-headless-shell 156.0.8078.4` (120 MB) indirildi.
İlk `launch` **başarısız** (`TargetClosedError` — sistem kütüphaneleri eksik).
`playwright install-deps chromium` sonrası **`launch` çalıştı** (`h1 = merhaba` okundu).

**Yani altyapı var.** Ama proje politikası gereği (DECISIONS #9) consumer AI sitelerinin
(Kling/Runway/Pika/Sora/Vidu) arayüz otomasyonunda **kullanılmayacak**. Kullanılacağı yerler:
kendi YouTube Studio kontrolü (son çare), ücretsiz servislerin *izin verdiği* oturum gerektiren
işlemler, ve yalnızca API'si olmayan ama ToS'u otomasyona izin veren kaynaklar.

## 5. YouTube tarafı

`google-api-python-client` yok (P4'te kurulacak — pip sorunsuz). Kanal + Google Cloud projesi
**henüz yok**; `docs/INSAN-GOREVI-01.md` adımları bekliyor. Denetim (audit) onayı gelene kadar
API ile yüklenen her video **private** kalır — hat bunu baştan varsayıyor.
