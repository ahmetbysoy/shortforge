# PROMPT P1 — Senaryo Üretimi (LLM + şema + kota)

> **Ön koşul:** `git clone https://github.com/ahmetbysoy/shortforge` · branch: `p1`
> Kanonik kod tabanı budur (bkz. `docs/P0.5-BIRLESTIRME.md`). Kendi P0'ını ayrı yerde sürdürme.
> Push için Drive'daki `github/github_erisim.json` token'ını kullan; push sonrası
> `git remote set-url origin https://github.com/ahmetbysoy/shortforge.git` ile token'ı remote'tan **sil**.

## 0. Bağlam

`main` durumu: P0.5 kapalı — 78 test, kapsam %95.4 kilitli, kota defteri action-aware,
`Script` şeması (`docs/schemas/script.schema.json`) hazır ve test edilmiş.
Bu aşamada **video üretilmez**; yalnızca *senaryo* üretilir.

Değişmez kurallar (P0'dan devralınan): sadece ücretsiz katman · tek sağlayıcıya bağımlılık yok ·
başkasının içeriği yok · sır sızıntısı yok · kaynak kod ASCII, doküman Türkçe · kapsam eşiği %80.

## 1. Kapsam

### 1.1 `providers/base.py` — LLM üretim yeteneği
`BaseProvider`'a **opsiyonel** bir yetenek ekle (yalnız LLM sağlayıcıları uygular):
```python
class LLMProvider(BaseProvider, Protocol):
    async def complete_json(
        self, *, system: str, user: str, schema: dict[str, Any], max_tokens: int = 2000
    ) -> str: ...
```
`health()` sözleşmesi değişmez. JSON modu zorunlu: sağlayıcı serbest metin dönerse
`ProviderError` fırlatır (parse `content/script.py`'de tek yerde yapılır).

### 1.2 `providers/llm_gemini.py` — gerçek üretim
`complete_json`: `POST /v1beta/models/gemini-2.0-flash:generateContent`·
`generationConfig.responseMimeType="application/json"` + `responseSchema` (şemadan sadeleştirilmiş).
Zaman aşımı 60 sn, `tenacity` ile 3 deneme (429/5xx'te retry, 400/401'de **retry yok**).
Ücretsiz katman notu loglanır: veri ürün geliştirmede kullanılabilir.

### 1.3 `providers/llm_groq.py` — **yeni yedek**
Groq free tier, OpenAI-uyumlu `POST /openai/v1/chat/completions` + `response_format={"type":"json_object"}`.
`priority=50`, `GEMINI_API_KEY` yoksa registry otomatik buna düşer. Anahtar yoksa `MISSING_KEY`.

### 1.4 `providers/llm_template.py` — **son savunma hattı**
Ağ yok, anahtar yok, %100 deterministik: konu havuzundan şablonla 3–5 sahnelik `Script`
üretir (hook + sahne anlatıları + görsel istemleri). Kalitesi düşük ama **hat asla durmaz**.
`shortforge doctor`'da daima `OK`. Çıktıya `warnings` içine `"sablon uretimi: LLM kullanilamadi"` eklenir.

### 1.5 `content/topics.py` — konu havuzu
`assets/topics.json`: niş (İlginç Bilgiler / Tarih / Bilim) için ≥30 konu, her biri
`{"id", "topic", "angle", "tags"}`. Seçim: **en uzun süredir kullanılmayan** (jobs tablosundan),
deterministik tie-break (`id`). `--topic` verilirse havuz atlanır.

### 1.6 `content/prompts.py` — istem şablonları
- Sistem: "Türkçe, dikey Shorts senaristisin; ilk 3 saniyede kanca; abartı yok; iddialar için kaynak notu."
- Kurallar: hook ≤ 90 karakter · 3–7 sahne · sahne anlatısı 1–2 cümle (≤ 400 karakter) ·
  `image_prompt` **İngilizce** ve görsel-işlenebilir olmalı (AI görsel motoru için) ·
  3–5 hashtag · `sources` boş bırakılamaz.
- Şema `docs/schemas/script.schema.json`'dan **okunur** (elle kopyalanmaz).

### 1.7 `content/script.py` — üretim hattı
```
topic → prompt → registry.resolve(LLM) → complete_json → json.loads → Script(**data)
      ↑______________________ hata geri bildirimi (2 retry) ______________________|
      → yedek sağlayıcı → şablon
```
- Şema hatası: hata mesajı + önceki çıktı **istem içine geri beslenir** (en fazla 2 deneme).
- Yedek zinciri: gemini → groq → template. Her adım loglanır (sağlayıcı, deneme, hata sınıfı).
- Sonuç: `Script` + `meta{"provider", "attempts", "duration_ms"}`.
- **Kota**: LLM çağrısı başına `ledger.charge("gemini"|"groq", 0, "script")` → birim 0 ama
  **çağrı sayısı defterde görünür**. (Kota tavrı: sıfır birimli olsa da iz bırakır.)

### 1.8 `state.py` — `jobs` tablosuna yazma
`save_script(job: VideoJob)` / `load_job(job_id)` / `recent_topics(days=30) -> set[str]`.
Aynı `topic` son 30 günde üretildiyse `--allow-duplicate` verilmedikçe `DuplicateTopic` hatası.

### 1.9 CLI
```bash
shortforge script                          # havuzdan sıradaki konu
shortforge script --topic "Antik Roma'da gün 24 saat değildi"
shortforge script --topic "..." --json     # script.json stdout'a (pipe'lanabilir)
shortforge script --topic "..." --allow-duplicate
shortforge topics                          # havuzu ve son kullanım tarihlerini listeler
```
Çıktı dosyası: `out/<job_id>/script.json` (+ `jobs` tablosunda `status=draft` satırı).
`DRY_RUN=true` iken de aynı davranış (LLM'e gidilir, disk yazılır; yalnız yükleme engellenir).

### 1.10 Testler (ağa çıkmadan)
- `Script` doğrulaması: hook 91 karakter, 2/8 sahne, 2/6 hashtag, boş `sources` → uyarı.
- Gemini: geçerli JSON (mutlu yol), bozuk JSON (→ retry → şablon), 429 (retry), 400 (retry yok).
- Yedek zinciri: gemini DOWN → groq kullanıldı; ikisi de DOWN → template; `meta.provider` doğru.
- `topics`: en eski kullanılmamış konu seçilir; 30 gün içinde tekrar → `DuplicateTopic`.
- Kota defteri: 3 script çağrısı → `spent("gemini", "script") == 3` (0 birim olsa da kayıt).
- `--json` çıktısı geçerli JSON ve stdout'ta tek başına (log satırı yok — stderr'e gider).
- Kapsam ≥ %80 (mevcut %95.4'ün altına düşmeyecek şekilde test ekle).

## 2. Yapma
- Ses/görsel/render/YouTube kodu (P2–P4).
- `time.sleep` ile bekleme; retry `tenacity` ile.
- Prompt'u koda gömme: `content/prompts.py` dışında istem metni olmaz.
- Gerçek API anahtarını repoya yazma; testler `respx`/sahte sağlayıcı kullanır.
- `main`'e doğrudan push. Branch `p1` → CI yeşil → merge.

## 3. Bitirme kontrolü
- [ ] `shortforge script --topic "..."` gerçek LLM ile geçerli `script.json` üretir (anahtar varsa)
- [ ] Anahtar yokken zincir şablona düşer ve **komut başarılı olur** (exit 0)
- [ ] `pytest -m "not live"` yeşil, kapsam ≥ %80, `ruff` + `mypy --strict` temiz
- [ ] `shortforge doctor` yeni sağlayıcıları (groq, template) doğru raporluyor
- [ ] `git grep -nE "AIza|gsk_|sk-"` → boş
- [ ] `docs/DECISIONS.md`'ye P1 kararları eklendi

## 4. Rapor formatı
```
## P1 RAPORU
1) Komut çıktısı: shortforge script --topic "..." (sağlayıcı, deneme sayısı, süre)
2) script.json (kısaltılmış: hook + sahne sayısı + hashtag'ler)
3) Yedek zinciri kanıtı: 3 senaryo (gemini var / gemini yok / ikisi de yok) ve hangi sağlayıcı seçildi
4) Test + kapsam: passed/failed | %kapsam | eklenen test dosyaları
5) Kararlar (DECISIONS'taki yeni maddeler)
6) Sapmalar + gerekçe
7) Blokajlar
8) P2 için öneri
```
Abartısız yaz: çalışmayan şeyi "çalışıyor" deme, şablon yedeğine düşüldüyse bunu açıkça yaz.
