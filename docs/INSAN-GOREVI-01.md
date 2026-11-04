# İNSAN GÖREVİ 01 — YouTube kanalı + Google Cloud (kod ile paralel yürür)

> Bunu **sen** yapacaksın (ajan değil). Kod tarafı arkada ilerlerken bu adımlar açılır; OAuth süreci 1 gün bekleyebildiği için erken başlıyoruz.
> Hiçbir adımda kredi kartı gerekmez.

## A. Kanal (10 dk)
1. Gmail/Google hesabı → youtube.com → **Kanal oluştur**. Kanal adı + `@handle` seç (niş: İlginç Bilgiler/Tarih/Bilim).
2. **Telefonla doğrula** (YouTube Studio → Ayarlar → Kanal → Özellik uygunluğu). Doğrulanmamış kanalda bazı özellikler kapalı; 15+ dk video ve özel kapak için de gerekir.
3. Kanal dili: Türkçe, ülke: Türkiye. `Gelişmiş ayarlar` → **Kanal doğrulaması** adımını da tamamla.

## B. Google Cloud projesi + API (10 dk)
4. console.cloud.google.com → yeni proje: `shortforge-prod` (kart istemez, billing **kapalı** kalsın).
5. `APIs & Services` → `Library` → **YouTube Data API v3** → `Enable`.
6. `OAuth consent screen`:
   - User type: **External**
   - App name: `ShortForge Bot`, destek e-postası, developer e-postası.
   - **Scopes:** `.../auth/youtube.upload` ve `.../auth/youtube.readonly`. (Daha fazlası denetim sürecini zorlaştırır, gereksiz.)
   - **Test kullanıcıları:** kendi Google hesabını ekle.
   - ⚠️ **Kritik:** App "Testing" modunda kalırsa `refresh_token` **7 günde** ölür. Bu yüzden `Publish app` (yayınla) → uygulama "unverified" olarak çalışır, "Google bu uygulamayı doğrulamadı" uyarısı çıkar (Gelişmiş → devam et). Unverified modda da yükleme çalışır; **ama video private kalır** — zaten istediğimiz akış bu.

## C. Kimlik bilgileri (10 dk)
7. `Credentials` → `Create credentials` → **OAuth client ID** → Application type: **Desktop app** → indir: `client_secret.json`.
8. İlk yetkilendirme yerel makinede bir kez yapılır (kodu P1 aşamasında vereceğim) → `refresh_token` üretilir.
9. GitHub repo → `Settings` → `Secrets and variables` → `Actions`:
   - `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`

## D. Denetim (audit) — public yayının tek yolu (15 dk başvuru, aylar sürebilir)
10. **YouTube API Services Audit and Quota Extension Form**'u doldur: proje amacı, video akışı, "insan onaylı iki aşamalı yayın" anlatımı, gizlilik politikası URL'i (GitHub Pages'te 1 sayfa yeter).
11. **Bana raporla:** form gönderildi mi, tahmini süre, Google'dan gelen e-posta.
12. Onay gelene kadar: **tüm yüklemeler private.** Bu bir hata değil, tasarım.

## E. Bana getir
- [ ] Kanal `@handle` ve kanal ID (`UC...`)
- [ ] Cloud proje ID
- [ ] Audit formu: gönderildi / beklemede
- [ ] `refresh_token` üretildi mi (değerini **chat'e yazma**, sadece "üretildi")
