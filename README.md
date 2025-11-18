# RAVN - Media Downloader

[![Python](https://img.shields.io/badge/Python-3.8+-3776ab.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Active%20Development-brightgreen.svg)]()

YouTube videolarını ve playlistlerini yüksek kalitede indirmek için geliştirilmiş modern bir masaüstü uygulaması.

## 📋 İçindekiler

- [Özellikler](#özellikler)
- [Kurulum](#kurulum)
- [Kullanım](#kullanım)
- [Mimari](#mimari)
- [Proje Yapısı](#proje-yapısı)
- [Test Etme](#test-etme)
- [Desktop Uygulaması Oluşturma](#desktop-uygulaması-oluşturma)
- [Gelecek Özellikler](#gelecek-özellikler-faz-2)
- [Sorun Giderme](#sorun-giderme)
- [Lisans](#lisans)

---

## 🎯 Proje Hakkında

**RAVN - Media Downloader**, YouTube videolarını ve playlistlerini yüksek kalitede indirmek için geliştirilmiş modern bir masaüstü uygulamasıdır. Kullanıcı dostu arayüzü, güçlü indirme yetenekleri ve estetik tema sistemiyle, medya içeriklerini kolayca bilgisayarınıza kaydetmenizi sağlar.

### Ana Amaç
- YouTube videolarını farklı formatlarda (MP4, MP3) indirmek
- Playlist'lerdeki birden fazla videoyu toplu olarak indirmek
- Kullanıcıya tam kontrol sağlayan, modern ve şık bir arayüz sunmak
- İndirme süreçlerini izleyebilir ve yönetebilir hale getirmek

### Hedef Kullanıcılar
- YouTube içeriklerini offline izlemek isteyen kullanıcılar
- Müzik koleksiyonu oluşturmak isteyenler
- Eğitim içeriklerini arşivlemek isteyenler
- İnternet bağlantısı olmadan medya içeriklerine erişmek isteyenler

---

## ✨ Özellikler

### 🎬 Medya İndirme Yetenekleri

#### Video İndirme (MP4)
- Çoklu kalite seçenekleri: En İyi, 1080p, 720p, 480p
- Video ve ses akışlarının otomatik birleştirilmesi
- YouTube'un 403 hatalarına karşı güvenli format seçimi

#### Ses İndirme (MP3)
- Yüksek kaliteli ses çıkarma (192 kbps)
- FFmpeg ile profesyonel ses dönüşümü
- Otomatik format dönüştürme

#### Playlist Desteği
- Tüm playlist'i veya seçili videoları indirme
- Video seçim penceresi ile kontrollü indirme
- Dosya adlarını otomatik numaralandırma seçeneği
- Playlist için otomatik klasör oluşturma

### 🎨 Kullanıcı Arayüzü

#### Tema Sistemi
- 3 farklı arka plan teması: Nordic, Forest, Aurora
- Dark mode desteği
- Dinamik arka plan yeniden boyutlandırma

#### İndirme Yönetimi
- Gerçek zamanlı ilerleme çubukları
- İndirme hızı ve tahmini süre gösterimi
- Detaylı log kayıtları (açılır/kapanır)
- Her indirme için ayrı kontrol paneli

#### Kontrol Özellikleri
- Tekli veya toplu iptal etme
- Tamamlanan indirmeleri temizleme
- Dosya ve klasör hızlı açma butonları
- İndirme kuyruğu sistemi

### 🔧 Teknik Özellikler

#### Sıralı İndirme Mimarisi
- Queue (kuyruk) tabanlı indirme sistemi
- Eşzamanlı birden fazla indirmeyi sırayla işleme
- Sistem kaynaklarını verimli kullanma

#### Thread-Safe İşlemler
- Threading ile arka plan indirmeleri
- UI thread'ini bloklamayan tasarım
- Güvenli iptal mekanizması

#### Hata Yönetimi
- FFmpeg eksikliği kontrolü
- İndirme hatalarını yakalama ve raporlama
- Kullanıcı dostu hata mesajları

---

## 📋 Gereksinimler

### Sistem Gereksinimleri
- **İşletim Sistemi:** Windows 10/11, macOS 10.14+, Linux (Ubuntu 20.04+)
- **Python:** 3.8 veya üzeri
- **RAM:** Minimum 4 GB
- **Disk Alanı:** 200 MB (uygulama) + indirme alanı

### Python Kütüphaneleri

| Kütüphane | Versiyon | Amaç |
|-----------|----------|------|
| customtkinter | ≥5.0.0 | Modern UI bileşenleri |
| Pillow | ≥9.0.0 | Görsel işleme ve tema resimleri |
| yt-dlp | Latest | YouTube video/ses indirme |

### Sistem Bağımlılıkları

#### FFmpeg Kurulumu

**Windows:**
1. [ffmpeg.org](https://ffmpeg.org/download.html) adresinden indirin
2. ZIP dosyasını çıkartın
3. `ffmpeg.exe`yi uygulama klasörüne koyun veya PATH'e ekleyin

**macOS:**
```bash
brew install ffmpeg
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install ffmpeg
```

---

## 🚀 Kurulum

### Hızlı Başlangıç

```bash
# 1. Depo klonlama
git clone https://github.com/waldseelen/ravn.git
cd ravn

# 2. Sanal ortam oluşturma (opsiyonel)
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/macOS

# 3. Bağımlılıkları yükleme
pip install -r requirements.txt

# 4. Uygulamayı başlatma
python -m ravn_app.ui.main_window
```

### PowerShell Build Script ile

```powershell
# Build script kullanarak tümünü kur
./build.ps1 all

# Veya adım adım
./build.ps1 check      # Ortam kontrolü
./build.ps1 install    # Bağımlılık kurulumu
./build.ps1 test       # Testleri çalıştır
./build.ps1 run        # Uygulamayı başlat
```

---

## 💻 Kullanım

### Temel Kullanım

#### Tekli Video İndirme
1. YouTube video URL'sini üst kısımdaki giriş alanına yapıştırın
2. **Format** seçin: MP4 (Video) veya MP3 (Ses)
3. **Kalite** seçin: En İyi, 1080p, 720p, 480p
4. **Kayıt Yeri** butonuna tıklayarak hedef klasörü seçin (varsayılan: Masaüstü)
5. **"Bilgileri Getir"** butonuna tıklayın
6. İndirme otomatik başlayacaktır

#### Playlist İndirme
1. YouTube playlist URL'sini girin
2. **"Bilgileri Getir"** butonuna tıklayın
3. Açılan pencerede:
   - İstediğiniz videoları seçin/seçimi kaldırın
   - "Dosya adlarını numaralandır" seçeneğini işaretleyin (opsiyonel)
   - **"Seçilenleri İndir"** butonuna tıklayın
4. Playlist için otomatik klasör oluşturulur ve videolar indirilir

#### İndirme Yönetimi
- **İlerlemeyi İzleme:** Her indirmenin ilerleme çubuğu gerçek zamanlı güncellenir
- **Detayları Görme:** ">" butonuna tıklayarak detaylı log kayıtlarını açın
- **İptal Etme:** "X" butonu ile tekli, "Tümünü İptal Et" ile toplu iptal
- **Temizleme:** Tamamlanan indirmeleri "Tamamlananları Temizle" ile kaldırın

#### Tema Değiştirme
Üst kısımdaki tema seçiciden istediğiniz temayı seçin:
- **Nordic:** Minimalist ve sakin mavi tonlar
- **Forest:** Doğa temalı yeşil tonlar
- **Aurora:** Canlı ve enerjetik mor-pembe tonlar

### Gelişmiş Özellikler

#### Dosya Adı Temizleme
Uygulama, indirilen dosyaların adlarındaki geçersiz karakterleri otomatik temizler:
- Kaldırılan karakterler: `\ / * ? : " < > |`
- Windows, macOS ve Linux'ta sorunsuz çalışır

#### Otomatik Format Seçimi
Uygulama, YouTube'un 403 hatalarını önlemek için akıllı format seçimi yapar:
1. Önce ayrı video (mp4) ve ses (m4a) akışlarını arar
2. Bulunamazsa önceden birleştirilmiş MP4'ü tercih eder
3. Son çare olarak mevcut en iyi kaliteyi seçer

#### Dosya Boyutu Gösterimi
Tamamlanan indirmeler için otomatik dosya boyutu gösterimi:
- Bytes, KB, MB, GB formatında
- Durum çubuğunda gösterilir

---

## 🏗️ Mimari

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

### Temel Bileşenler

#### YouTubeDownloaderApp (Ana Sınıf)
Ana uygulama penceresi ve tüm bileşenlerin yöneticisi.

**Sorumluluklar:**
- UI bileşenlerini oluşturma ve yönetme
- Tema sistemini uygulama
- İndirme kuyruğunu işleme
- Thread'leri koordine etme

#### İndirme Kuyruk Sistemi
```python
download_queue = queue.Queue()  # FIFO kuyruk
is_worker_active = False        # Eşzamanlılık kontrolü
```

**Çalışma Prensibi:**
1. Kullanıcı indirme başlatır → Kuyruğa eklenir
2. Worker thread boş ise → İlk işi alır ve başlatır
3. İndirme bitince → Sonraki işi otomatik başlatır

#### UI Güncelleme Sistemi
Thread-safe iletişim için her indirme işinin kendi `ui_queue`'su vardır:
```python
ui_queue.put(('progress', 0.5))      # İlerleme güncelleme
ui_queue.put(('status', 'text'))     # Durum mesajı
ui_queue.put(('log', 'detay'))       # Log kaydı
ui_queue.put(('finalize', ...))      # Tamamlama
```

### Veri Akışı

```
1. Kullanıcı URL girer
        ↓
2. fetch_info() → yt-dlp ile bilgi çeker
        ↓
3. Playlist mi kontrol et
        ↓
    ┌───YES─→ Seçim penceresi aç
    │            ↓
    └───NO──→ Doğrudan kuyruğa ekle
        ↓
4. download_queue'ya eklenir
        ↓
5. process_download_queue() başlatır
        ↓
6. download_video() thread'de çalışır
        ↓
7. ui_queue ile UI güncellenir
        ↓
8. FFmpeg ile format dönüştürme
        ↓
9. Sonuç kullanıcıya bildirilir
```

---

## 📂 Proje Yapısı

```
ravn/
├── ravn_app/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── converter.py       # Video/ses dönüştürme
│   │   ├── downloader.py      # İndirme ve kuyruk yönetimi
│   │   └── __pycache__/
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── main_window.py     # Ana uygulama penceresi
│   │   ├── converter_tab.py   # Dönüştürme sekmesi
│   │   └── __pycache__/
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── ffmpeg_checker.py  # FFmpeg denetimi
│   │   ├── file_utils.py      # Dosya işlemleri
│   │   ├── system_utils.py    # Sistem yardımcıları
│   │   └── __pycache__/
│   └── __pycache__/
├── tests/
│   ├── conftest.py
│   ├── test_converter.py
│   ├── test_core.py
│   └── __pycache__/
├── .github/
│   └── workflows/              # CI/CD
├── requirements.txt            # Proje bağımlılıkları
├── pytest.ini                  # Pytest konfigürasyonu
├── build.ps1                   # PowerShell build scripti
├── README.md                   # Bu dosya
├── CHANGELOG.md                # Sürüm tarihi
├── ROADMAP.md                  # Gelecek planlar
└── ravnapp.jpeg                # Proje ikonu
```

---

## 🧪 Test Etme

### Birim Testleri Çalıştırma

```bash
# Tüm testleri çalıştırma
pytest

# Belirli test dosyasını çalıştırma
pytest tests/test_converter.py

# Coverage raporu ile
pytest --cov=ravn_app tests/

# Verbose mod
pytest -v tests/
```

### Test Yapısı

```
tests/
├── conftest.py         # Pytest konfigürasyonu
├── test_converter.py   # Dönüştürme testleri
└── test_core.py        # Çekirdek işlev testleri
```

---

## 🖥️ Desktop Uygulaması Oluşturma

### PyInstaller ile EXE Oluşturma

#### 1. PyInstaller Kurulumu
```bash
pip install pyinstaller
```

#### 2. Basit EXE Oluşturma
```bash
pyinstaller --onefile --windowed --name RAVN ravn.py
```

#### 3. Gelişmiş EXE Oluşturma (Önerilen)

**build.ps1 script'i otomatik olarak yapar:**

```powershell
# Tema görselleri ve FFmpeg ile birlikte package oluştur
pyinstaller --onefile --windowed --name RAVN `
    --add-data "vgh0i1co9d18_manus_s_2025-08-01_13-14-03_5845.webp;." `
    --add-data "vgh0i1co9d18_manus_s_2025-08-01_13-14-16_3607.webp;." `
    --add-data "vgh0i1co9d18_manus_s_2025-08-01_13-14-42_1489.webp;." `
    --hidden-import=customtkinter `
    --hidden-import=PIL._tkinter_finder `
    --hidden-import=yt_dlp `
    ravn_app/ui/main_window.py
```

#### 4. Otomatik Build Script

PowerShell build script'i kullanarak:

```powershell
./build.ps1 all
```

**Parametreler:**
- `check` - Ortam kontrolü yap
- `install` - Bağımlılıkları kur
- `test` - Testleri çalıştır
- `run` - Uygulamayı başlat
- `clean` - Cache'leri temizle
- `all` - Hepsi (install→clean→test→run)

---

## 🚀 Gelecek Özellikler (Faz 2)

### 1. Video Çevirici/Dönüştürücü Modülü

**Planlanan Özellikler:**

- **Format Dönüştürme:**
  - MP4 ↔ AVI ↔ MKV ↔ MOV ↔ WEBM
  - Video → GIF animasyon
  - Video → Görsel dizisi (frame extraction)

- **Codec İşlemleri:**
  - H.264, H.265 (HEVC), VP9, AV1 codec desteği
  - Codec bilgilerini görüntüleme
  - Re-encode veya remux seçenekleri

- **Kalite Ayarları:**
  - Bitrate kontrolü (sabit/değişken)
  - Çözünürlük değiştirme (upscale/downscale)
  - FPS (frame rate) ayarlama

- **Gelişmiş Düzenleme:**
  - Video kırpma (trim)
  - Video birleştirme (concatenate)
  - Ses düzeyi normalizasyonu
  - Altyazı ekleme/çıkarma

**Planlanan UI:**
```
┌─────────────────────────────────────┐
│ Kaynak Video: [Dosya Seç]          │
├─────────────────────────────────────┤
│ Hedef Format: [MP4 ▼]              │
│ Codec:        [H.265 ▼]            │
│ Kalite:       [720p ▼]             │
│ Bitrate:      [2000 kbps]          │
├─────────────────────────────────────┤
│ [Önizleme] [Dönüştür] [İptal]      │
└─────────────────────────────────────┘
```

### 2. Batch (Toplu) İşlem Sistemi
- Birden fazla dosyayı aynı anda dönüştürme
- İşlem sırası yönetimi
- CPU/GPU kullanım optimizasyonu
- Tamamlanan işlemleri otomatik taşıma

### 3. Codec Analiz Aracı
Video dosyalarının teknik detaylarını analiz:
- Video codec, çözünürlük, FPS, bitrate
- Ses codec, kanal sayısı, örnekleme oranı
- Dosya boyutu, süre, konteyner formatı
- Metadata bilgileri

### 4. Subtitle (Altyazı) Yöneticisi
- YouTube'dan otomatik altyazı indirme
- Altyazı formatı dönüştürme (SRT, VTT, ASS)
- Altyazı senkronizasyon düzeltme
- Çoklu dil desteği

### 5. Ses İşleme Modülü
- Ses çıkarma (video → ses)
- Ses normalizasyonu
- Gürültü azaltma
- Equalizer ayarları

### 6. Playlist Yöneticisi
- Favori playlistleri kaydetme
- Otomatik güncelleme kontrolü
- İndirilmeyen videoları tespit etme
- İndirme geçmişi

### Teknik Altyapı İyileştirmeleri

#### Veritabanı Entegrasyonu
```python
# SQLite ile indirme geçmişi
import sqlite3

class DownloadHistory:
    def __init__(self):
        self.conn = sqlite3.connect('ravn_history.db')
        self.create_table()

    def create_table(self):
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS downloads (
                id INTEGER PRIMARY KEY,
                url TEXT,
                title TEXT,
                format TEXT,
                quality TEXT,
                file_path TEXT,
                file_size INTEGER,
                download_date TIMESTAMP,
                status TEXT
            )
        ''')
```

#### Konfigürasyon Sistemi
```json
// ravn_config.json
{
    "default_download_path": "C:/Users/Username/Downloads/RAVN",
    "default_format": "MP4",
    "default_quality": "1080p",
    "theme": "nordic",
    "concurrent_downloads": 3,
    "auto_cleanup": true,
    "auto_update_check": true,
    "ffmpeg_path": "ffmpeg.exe"
}
```

#### Plugin Sistemi
Gelecekte üçüncü parti eklentiler için genişletilebilir mimari

#### API Entegrasyonu
- Spotify, SoundCloud desteği
- Vimeo, Dailymotion desteği
- Twitch VOD indirme

### UI/UX İyileştirmeleri

#### Gelişmiş Önizleme
- Video thumbnail önizlemesi
- Oynatma süresi gösterimi
- Kanal bilgisi ve görüntülenme sayısı

#### Drag & Drop Desteği
- URL'leri sürükle-bırak ile ekleme
- Dosyaları dönüştürücüye sürükleme

#### Sistem Tray Entegrasyonu
- Arka planda çalışma
- Sistem tray ikonu
- Tamamlanma bildirimleri

#### Keyboard Shortcuts
- Ctrl+V: URL yapıştır ve başlat
- Ctrl+P: Ayarlar
- Ctrl+Q: Çıkış

### Performans Optimizasyonları

#### Çoklu İş Parçacığı İyileştirmesi
```python
# Eşzamanlı indirme limiti
MAX_CONCURRENT_DOWNLOADS = 3

# ThreadPoolExecutor kullanımı
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_DOWNLOADS)
```

#### Önbellekleme Sistemi
- İndirme bilgilerini önbelleğe al
- Thumbnail'leri cache'le
- FFmpeg process pool

#### Bellek Yönetimi
- Büyük dosyalar için chunk-based işleme
- Otomatik bellek temizleme
- Garbage collection optimizasyonu

---

## 🔧 Sorun Giderme

### FFmpeg Bulunamadı
**Hata:** "Eksik Bağımlılık: FFmpeg"

**Çözümler:**
1. FFmpeg'i yükleyin (yukarıda kurulum adımlarına bakın)
2. `ffmpeg.exe`yi uygulama klasörüne koyun
3. Sistem PATH'ine ekleyin

### İndirme Başlamıyor
**Olası Nedenler:**
- İnternet bağlantısı sorunu
- Geçersiz URL
- Video yaş sınırlaması

**Çözüm:** Log detaylarını kontrol edin

### CustomTkinter Hatası
**Hata:** "Module not found: customtkinter"

**Çözüm:**
```bash
pip install --upgrade customtkinter
```

### İnternet Bağlantısı Sorunu
**Hata:** "Ağ bağlantısı başarısız"

**Çözüm:**
- İnternet bağlantınızı kontrol edin
- yt-dlp'yi güncelleyin: `pip install --upgrade yt-dlp`

---

## 📊 Performans Metrikleri

**Test Sistemi:**
- CPU: Intel i5-10400
- RAM: 16 GB
- İnternet: 100 Mbps

**Sonuçlar:**

| İşlem | Süre | CPU | RAM |
|-------|------|-----|-----|
| Uygulama başlatma | ~2s | 15% | 80 MB |
| 1080p video indirme | ~30s | 25% | 150 MB |
| MP3 dönüştürme | ~10s | 40% | 100 MB |
| 10 videolu playlist | ~5m | 30% | 200 MB |

---

## 🤝 Katkı

Katkılar hoş geldiniz! Lütfen:

1. Fork yapın
2. Feature branch oluşturun (`git checkout -b feature/yeni-ozellik`)
3. Commit yapın (`git commit -m 'Yeni özellik eklendi'`)
4. Push edin (`git push origin feature/yeni-ozellik`)
5. Pull Request açın

---

## 📝 Lisans

Bu proje MIT Lisansı altında lisanslanmıştır. Detaylar için [LICENSE](LICENSE) dosyasına bakın.

---

## ❓ SSS

**S: FFmpeg bulunamıyor hatasını alıyorum.**
C: FFmpeg'i [ffmpeg.org](https://ffmpeg.org/download.html) adresinden indirip sistem PATH'ine ekleyin.

**S: İndirme çok yavaş.**
C: İnternet hızınız, video kalitesi ve sistem performansı bu konuda etkili olabilir.

**S: Hangi video formatları destekleniyor?**
C: YouTube'daki tüm formatlar (MP4, WebM, vb.) ve MP3 audio desteği var.

**S: Kaç video aynı anda indirebilirim?**
C: Varsayılan olarak sıralı indirme yapılır (sistem kaynaklarını optimize etmek için).

**S: Indirilen videoları kaldırabilir miyim?**
C: Evet, indirme tamamlandıktan sonra "Dosyayı Aç" butonuyla açılan klasörden silebilirsiniz.

---

## 📞 İletişim ve Destek

**GitHub:** [waldseelen/ravn](https://github.com/waldseelen/ravn)

**Bug Raporlama:**
- [GitHub Issues](https://github.com/waldseelen/ravn/issues) kullanın
- Detaylı açıklama ve log kayıtları ekleyin
- Sistem bilgilerini paylaşın

---

**Son Güncelleme:** 18 Kasım 2025
**Versiyon:** 1.0.0
**Durum:** Aktif Geliştirme
