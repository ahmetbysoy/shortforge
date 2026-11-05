# İNSAN GÖREVİ 01 — YouTube kanalı + Google Cloud (kod ile paralel yürür)

> Bunu **sen** yapacaksın (ajan değil). Kod tarafı arkada ilerlerken bu adımlar açılır; OAuth süreci 1 gün bekleyebildiği için erken başlıyoruz.
> Hiçbir adımda kredi kartı gerekmez.

## A. Kanal (10 dk)
1. Gmail/Google hesabı → youtube.com → **Kanal oluştur**. Kanal adı + `@handle` seç (niş: İlginç Bilgiler/Tarih/Bilim).
2. **Telefonla doğrula** (YouTube Studio → Ayarlar → Kanal → Özellik uygunluğu). Doğrulanmamış kanalda bazı özellikler kapalı; 15+ dk video ve özel kapak için de gerekir.
3. Kanal dili: Türkçe, ülke: Türkiye. `Gelişmiş ayarlar` → **Kanal doğrulaması** adımını da tamamla.

## B. Google Cloud projesi + API (10 dk)

> Bu adimlar **senin Google hesabinda** yapilmali; ajan senin yerine giris yapamaz.
> Kart gerekmez, faturalandirma kapali kalabilir.

4. console.cloud.google.com -> yeni proje: `ai-shorts-factory`.
5. `APIs & Services` -> `Library` -> **YouTube Data API v3** -> `Enable`.
6. `OAuth consent screen`:
   - User type: **External**
   - App name: `ShortForge Bot`, destek + gelistirici e-postasi.
   - **Scopes:** yalniz `https://www.googleapis.com/auth/youtube.upload`
     (daha fazlasi denetim surecini zorlastirir; okuma gerekirse sonra `youtube.readonly` eklenir).
   - Test users: kendi hesabini ekle.
7. **⚠️ KRITIK - "Testing" modunda BIRAKMA.** Google, *Testing* durumundaki uygulamalarin
   refresh_token'ini **7 gun** sonra gecersiz kilar. 7/24 otomasyonda bu, bir hafta sonra
   sessiz olum demektir. `Publish app` -> uygulama **"In production" (unverified)** olur:
   - "Google bu uygulamayi dogrulamadi" uyarisi cikar -> Gelismis -> devam et (tek seferlik).
   - 100 kullanici siniri ve 7 gun sorunu kalkar; token kalici olur.
   - Denetlenmemis proje oldugu icin API yuklemeleri yine **private** kalir - bu zaten
     istedigimiz akis (asagidaki nota bak).

## C. Kimlik bilgileri (5 dk)

8. `Credentials` -> `Create credentials` -> **OAuth client ID** ->
   Application type: **Desktop app** (Web application SECILMEZ; loopback akisi calismaz).
9. Indirilen JSON'u `client_secret.json` adiyla **proje kokune** koy (`.gitignore`'da).
10. Yetkilendirme - iki adim (PKCE nedeniyle; `run_console()` artik yok):

```bash
python scripts/youtube_auth.py --auth-url
#   -> bir URL basar. Tarayicida ac, onayla.
#   -> Google http://localhost:8765/?code=... adresine yonlendirir; sayfa ACILMAZ (normal).
#   -> Adres cubugundaki TAM URL'yi kopyala:

python scripts/youtube_auth.py --exchange "http://localhost:8765/?code=...&state=..."
#   -> token.json olusur (0600). refresh_token icinde.
```

11. GitHub repo -> `Settings` -> `Secrets and variables` -> `Actions`:
    `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN` (token.json'dan).

## D. Ilk private yukleme testi (kota: 1600 birim)

```bash
python scripts/upload_test.py --generate      # 5 sn 1080x1920 test videosu uretir + yukler
```
Beklenen: `video_id`, `https://youtu.be/...` ve **dogrulama** satirinda
`privacyStatus: private`. Public istenirse script **reddeder** (kural: once gizli -> onay -> yayin).

## E. Denetim (audit) - public yayinin tek yolu (15 dk basvuru, haftalar surebilir)

12. **YouTube API Services Audit and Quota Extension Form**: proje amaci, video akisi,
    "insan onayli iki asamali yayin" anlatimi. Onay gelene kadar tum yuklemeler private.
13. **Bana raporla:** kanal `@handle` + `UC...` ID, Cloud proje ID, consent screen durumu
    (Testing/In production), audit formu gonderildi mi.

## F. Bana getir
- [ ] Kanal `@handle` + kanal ID (`UC...`)
- [ ] Cloud proje ID
- [ ] `client_secret.json` (proje kokune; degeri chat'e **yazma**)
- [ ] Consent screen: **In production** mi? (Testing ise token 7 gunde olur)
- [ ] `token.json` uretildi mi (refresh_token degerini chat'e **yazma**)
- [ ] Audit formu: gonderildi / beklemede
