# RAVN - Media Downloader

## ­şôï ─░├ğindekiler
- [Proje Hakk─▒nda](#proje-hakk─▒nda)
- [├ûzellikler](#├Âzellikler)
- [Mimari ve Tasar─▒m](#mimari-ve-tasar─▒m)
- [Kurulum ve Gereksinimler](#kurulum-ve-gereksinimler)
- [Kullan─▒m K─▒lavuzu](#kullan─▒m-k─▒lavuzu)
- [Desktop Uygulamas─▒ Olu┼şturma](#desktop-uygulamas─▒-olu┼şturma)
- [Gelecek Geli┼ştirmeler](#gelecek-geli┼ştirmeler)
- [Teknik Detaylar](#teknik-detaylar)

---

## ­şÄ» Proje Hakk─▒nda

**RAVN - Media Downloader**, YouTube videolar─▒n─▒ ve playlistlerini y├╝ksek kalitede indirmek i├ğin geli┼ştirilmi┼ş modern bir masa├╝st├╝ uygulamas─▒d─▒r. Kullan─▒c─▒ dostu aray├╝z├╝, g├╝├ğl├╝ indirme yetenekleri ve estetik tema sistemiyle, medya i├ğeriklerini kolayca bilgisayar─▒n─▒za kaydetmenizi sa─şlar.

### Ana Ama├ğ
- YouTube videolar─▒n─▒ farkl─▒ formatlarda (MP4, MP3) indirmek
- Playlist'lerdeki birden fazla videoyu toplu olarak indirmek
- Kullan─▒c─▒ya tam kontrol sa─şlayan, modern ve ┼ş─▒k bir aray├╝z sunmak
- ─░ndirme s├╝re├ğlerini izleyebilir ve y├Ânetebilir hale getirmek

---

## Ô£¿ ├ûzellikler

### ­şÄ¼ Medya ─░ndirme Yetenekleri
1. **Video ─░ndirme (MP4)**
   - ├çoklu kalite se├ğenekleri: En ─░yi, 1080p, 720p, 480p
   - Video ve ses ak─▒┼şlar─▒n─▒n otomatik birle┼ştirilmesi
   - YouTube'un 403 hatalar─▒na kar┼ş─▒ g├╝venli format se├ğimi

2. **Ses ─░ndirme (MP3)**
   - Y├╝ksek kaliteli ses ├ğ─▒karma (192 kbps)
   - FFmpeg ile profesyonel ses d├Ân├╝┼ş├╝m├╝
   - Otomatik format d├Ân├╝┼şt├╝rme

3. **Playlist Deste─şi**
   - T├╝m playlist'i veya se├ğili videolar─▒ indirme
   - Video se├ğim penceresi ile kontroll├╝ indirme
   - Dosya adlar─▒n─▒ otomatik numaraland─▒rma se├ğene─şi
   - Playlist i├ğin otomatik klas├Âr olu┼şturma

### ­şÄ¿ Kullan─▒c─▒ Aray├╝z├╝
1. **Tema Sistemi**
   - 3 farkl─▒ arka plan temas─▒: Nordic, Forest, Aurora
   - Dark mode deste─şi
   - Dinamik arka plan yeniden boyutland─▒rma

2. **─░ndirme Y├Ânetimi**
   - Ger├ğek zamanl─▒ ilerleme ├ğubuklar─▒
   - ─░ndirme h─▒z─▒ ve tahmini s├╝re g├Âsterimi
   - Detayl─▒ log kay─▒tlar─▒ (a├ğ─▒l─▒r/kapan─▒r)
   - Her indirme i├ğin ayr─▒ kontrol paneli

3. **Kontrol ├ûzellikleri**
   - Tekli veya toplu iptal etme
   - Tamamlanan indirmeleri temizleme
   - Dosya ve klas├Âr h─▒zl─▒ a├ğma butonlar─▒
   - ─░ndirme kuyru─şu sistemi

### ­şöğ Teknik ├ûzellikler
1. **S─▒ral─▒ ─░ndirme Mimarisi**
   - Queue (kuyruk) tabanl─▒ indirme sistemi
   - E┼şzamanl─▒ birden fazla indirmeyi s─▒rayla i┼şleme
   - Sistem kaynaklar─▒n─▒ verimli kullanma

2. **Thread-Safe ─░┼şlemler**
   - Threading ile arka plan indirmeleri
   - UI thread'ini bloklamayan tasar─▒m
   - G├╝venli iptal mekanizmas─▒

3. **Hata Y├Ânetimi**
   - FFmpeg eksikli─şi kontrol├╝
   - ─░ndirme hatalar─▒n─▒ yakalama ve raporlama
   - Kullan─▒c─▒ dostu hata mesajlar─▒

---

## ­şÅù´©Å Mimari ve Tasar─▒m

### Katmanl─▒ Mimari

```
ÔöîÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÉ
Ôöé     Kullan─▒c─▒ Aray├╝z├╝ (UI)         Ôöé
Ôöé  (CustomTkinter + PIL)              Ôöé
Ôö£ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöñ
Ôöé    ─░┼ş Mant─▒─ş─▒ Katman─▒               Ôöé
Ôöé  - ─░ndirme Y├Ânetimi                 Ôöé
Ôöé  - Kuyruk Sistemi                   Ôöé
Ôöé  - Thread Y├Ânetimi                  Ôöé
Ôö£ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöñ
Ôöé    Medya ─░┼şleme Katman─▒             Ôöé
Ôöé  - yt-dlp (YouTube indirme)         Ôöé
Ôöé  - FFmpeg (format d├Ân├╝┼şt├╝rme)       Ôöé
Ôö£ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöñ
Ôöé      Sistem Katman─▒                 Ôöé
Ôöé  - Dosya Sistemi ─░┼şlemleri          Ôöé
Ôöé  - Platform Alg─▒lama                Ôöé
ÔööÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöİ
```

---

## ­şÆ╗ Kurulum ve Gereksinimler

### Sistem Gereksinimleri
- **─░┼şletim Sistemi:** Windows 10/11, macOS 10.14+, Linux (Ubuntu 20.04+)
- **Python:** 3.8 veya ├╝zeri
- **RAM:** Minimum 4 GB
- **Disk Alan─▒:** 200 MB (uygulama) + indirme alan─▒

### Python K├╝t├╝phaneleri

```bash
pip install customtkinter
pip install Pillow
pip install yt-dlp
```

**K├╝t├╝phane Detaylar─▒:**

| K├╝t├╝phane | Versiyon | Ama├ğ |
|-----------|----------|------|
| customtkinter | ÔëÑ5.0.0 | Modern UI bile┼şenleri |
| Pillow | ÔëÑ9.0.0 | G├Ârsel i┼şleme ve tema resimleri |
| yt-dlp | Latest | YouTube video/ses indirme |

---

## ­şôû Kullan─▒m K─▒lavuzu

### Temel Kullan─▒m

#### 1. Tekli Video ─░ndirme
1. YouTube video URL'sini ├╝st k─▒s─▒mdaki giri┼ş alan─▒na yap─▒┼şt─▒r─▒n
2. **Format** se├ğin: MP4 (Video) veya MP3 (Ses)
3. **Kalite** se├ğin: En ─░yi, 1080p, 720p, 480p
4. **Kay─▒t Yeri** butonuna t─▒klayarak hedef klas├Âr├╝ se├ğin (varsay─▒lan: Masa├╝st├╝)
5. **"Bilgileri Getir"** butonuna t─▒klay─▒n
6. ─░ndirme otomatik ba┼şlayacakt─▒r

---

## ­şôü Kod Organizasyonu

```
ravn/
Ôö£ÔöÇÔöÇ ravn.py                 # Ana uygulama
Ôö£ÔöÇÔöÇ requirements.txt        # Python ba─ş─▒ml─▒l─▒klar─▒
Ôö£ÔöÇÔöÇ README.md              # Kullan─▒c─▒ dok├╝mantasyonu
Ôö£ÔöÇÔöÇ RAVN_DOKUMENTASYON.md  # Teknik dok├╝mantasyon
Ôö£ÔöÇÔöÇ assets/                # G├Ârseller ve kaynaklar
Ôöé   Ôö£ÔöÇÔöÇ themes/
Ôöé   Ôöé   Ôö£ÔöÇÔöÇ nordic.webp
Ôöé   Ôöé   Ôö£ÔöÇÔöÇ forest.webp
Ôöé   Ôöé   ÔööÔöÇÔöÇ aurora.webp
Ôöé   ÔööÔöÇÔöÇ icons/
Ôöé       ÔööÔöÇÔöÇ ravn_icon.ico
Ôö£ÔöÇÔöÇ build/                 # Build ├ğ─▒kt─▒lar─▒ (ge├ğici)
Ôö£ÔöÇÔöÇ dist/                  # EXE ├ğ─▒kt─▒lar─▒
ÔööÔöÇÔöÇ release/               # Da─ş─▒t─▒m paketi
```
