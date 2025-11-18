# RAVN - Media Downloader

## 📋 İçindekiler
- [Proje Hakkında](#proje-hakkında)
- [Özellikler](#özellikler)
- [Mimari ve Tasarım](#mimari-ve-tasarım)
- [Kurulum ve Gereksinimler](#kurulum-ve-gereksinimler)
- [Kullanım Kılavuzu](#kullanım-kılavuzu)
- [Desktop Uygulaması Oluşturma](#desktop-uygulaması-oluşturma)
- [Gelecek Geliştirmeler](#gelecek-geliştirmeler)
- [Teknik Detaylar](#teknik-detaylar)

---

## 🎯 Proje Hakkında

**RAVN - Media Downloader**, YouTube videolarını ve playlistlerini yüksek kalitede indirmek için geliştirilmiş modern bir masaüstü uygulamasıdır. Kullanıcı dostu arayüzü, güçlü indirme yetenekleri ve estetik tema sistemiyle, medya içeriklerini kolayca bilgisayarınıza kaydetmenizi sağlar.

### Ana Amaç
- YouTube videolarını farklı formatlarda (MP4, MP3) indirmek
- Playlist'lerdeki birden fazla videoyu toplu olarak indirmek
- Kullanıcıya tam kontrol sağlayan, modern ve şık bir arayüz sunmak
- İndirme süreçlerini izleyebilir ve yönetebilir hale getirmek

---

## ✨ Özellikler

### 🎬 Medya İndirme Yetenekleri
1. **Video İndirme (MP4)**
   - Çoklu kalite seçenekleri: En İyi, 1080p, 720p, 480p
   - Video ve ses akışlarının otomatik birleştirilmesi
   - YouTube'un 403 hatalarına karşı güvenli format seçimi

2. **Ses İndirme (MP3)**
   - Yüksek kaliteli ses çıkarma (192 kbps)
   - FFmpeg ile profesyonel ses dönüşümü
   - Otomatik format dönüştürme

3. **Playlist Desteği**
   - Tüm playlist'i veya seçili videoları indirme
   - Video seçim penceresi ile kontrollü indirme
   - Dosya adlarını otomatik numaralandırma seçeneği
   - Playlist için otomatik klasör oluşturma

### 🎨 Kullanıcı Arayüzü
1. **Tema Sistemi**
   - 3 farklı arka plan teması: Nordic, Forest, Aurora
   - Dark mode desteği
   - Dinamik arka plan yeniden boyutlandırma

2. **İndirme Yönetimi**
   - Gerçek zamanlı ilerleme çubukları
   - İndirme hızı ve tahmini süre gösterimi
   - Detaylı log kayıtları (açılır/kapanır)
   - Her indirme için ayrı kontrol paneli

3. **Kontrol Özellikleri**
   - Tekli veya toplu iptal etme
   - Tamamlanan indirmeleri temizleme
   - Dosya ve klasör hızlı açma butonları
   - İndirme kuyruğu sistemi

### 🔧 Teknik Özellikler
1. **Sıralı İndirme Mimarisi**
   - Queue (kuyruk) tabanlı indirme sistemi
   - Eşzamanlı birden fazla indirmeyi sırayla işleme
   - Sistem kaynaklarını verimli kullanma

2. **Thread-Safe İşlemler**
   - Threading ile arka plan indirmeleri
   - UI thread'ini bloklamayan tasarım
   - Güvenli iptal mekanizması

3. **Hata Yönetimi**
   - FFmpeg eksikliği kontrolü
   - İndirme hatalarını yakalama ve raporlama
   - Kullanıcı dostu hata mesajları

---

## 🏗️ Mimari ve Tasarım

### Katmanlı Mimari

```
┌─────────────────────────────────────┐
│     Kullanıcı Arayüzü (UI)         │
│  (CustomTkinter + PIL)              │
├─────────────────────────────────────┤
│    İş Mantığı Katmanı               │
│  - İndirme Yönetimi                 │
│  - Kuyruk Sistemi                   │
│  - Thread Yönetimi                  │
├─────────────────────────────────────┤
│    Medya İşleme Katmanı             │
│  - yt-dlp (YouTube indirme)         │
│  - FFmpeg (format dönüştürme)       │
├─────────────────────────────────────┤
│      Sistem Katmanı                 │
│  - Dosya Sistemi İşlemleri          │
│  - Platform Algılama                │
└─────────────────────────────────────┘
```

---

## 💻 Kurulum ve Gereksinimler

### Sistem Gereksinimleri
- **İşletim Sistemi:** Windows 10/11, macOS 10.14+, Linux (Ubuntu 20.04+)
- **Python:** 3.8 veya üzeri
- **RAM:** Minimum 4 GB
- **Disk Alanı:** 200 MB (uygulama) + indirme alanı

### Python Kütüphaneleri

```bash
pip install customtkinter
pip install Pillow
pip install yt-dlp
```

**Kütüphane Detayları:**

| Kütüphane | Versiyon | Amaç |
|-----------|----------|------|
| customtkinter | ≥5.0.0 | Modern UI bileşenleri |
| Pillow | ≥9.0.0 | Görsel işleme ve tema resimleri |
| yt-dlp | Latest | YouTube video/ses indirme |

---

## 📖 Kullanım Kılavuzu

### Temel Kullanım

#### 1. Tekli Video İndirme
1. YouTube video URL'sini üst kısımdaki giriş alanına yapıştırın
2. **Format** seçin: MP4 (Video) veya MP3 (Ses)
3. **Kalite** seçin: En İyi, 1080p, 720p, 480p
4. **Kayıt Yeri** butonuna tıklayarak hedef klasörü seçin (varsayılan: Masaüstü)
5. **"Bilgileri Getir"** butonuna tıklayın
6. İndirme otomatik başlayacaktır

---

## 📁 Kod Organizasyonu

```
ravn/
├── ravn.py                 # Ana uygulama
├── requirements.txt        # Python bağımlılıkları
├── README.md              # Kullanıcı dokümantasyonu
├── RAVN_DOKUMENTASYON.md  # Teknik dokümantasyon
├── assets/                # Görseller ve kaynaklar
│   ├── themes/
│   │   ├── nordic.webp
│   │   ├── forest.webp
│   │   └── aurora.webp
│   └── icons/
│       └── ravn_icon.ico
├── build/                 # Build çıktıları (geçici)
├── dist/                  # EXE çıktıları
└── release/               # Dağıtım paketi
```
