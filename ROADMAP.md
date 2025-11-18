# RAVN Geliştirme Yol Haritası
# Video Çevirici, Codec Çözücü ve Format Dönüştürücü Özellikleri

## 🎯 Genel Vizyon

RAVN'ı kapsamlı bir medya yönetim aracına dönüştürmek:
- YouTube İndirici (✅ Mevcut)
- Video Çevirici/Dönüştürücü (📋 Planlı)
- Codec Analiz Aracı (📋 Planlı)
- Ses İşleme Modülü (📋 Planlı)

---

## 📅 Geliştirme Fazları

### Faz 1: Video Dönüştürücü Modülü (Öncelik: Yüksek)

#### 1.1 Temel Format Dönüştürme
**Süre:** 2 hafta

**Özellikler:**
- MP4, AVI, MKV, MOV, WEBM, FLV arası dönüşüm
- Tek dosya dönüştürme arayüzü
- Kaynak ve hedef format seçimi

**Teknik Gereksinimler:**
```python
# video_converter.py modülü
class VideoConverter:
    def __init__(self, ffmpeg_path):
        self.ffmpeg = ffmpeg_path

    def convert(self, input_file, output_format, quality):
        """Video formatını dönüştür"""
        command = [
            self.ffmpeg,
            '-i', input_file,
            '-c:v', 'libx264',  # Video codec
            '-preset', 'medium',
            '-crf', str(quality),
            '-c:a', 'aac',      # Audio codec
            '-strict', 'experimental',
            output_file
        ]
        subprocess.run(command)
```

**UI Taslağı:**
```
┌────────────────────────────────────────┐
│  Video Dönüştürücü                     │
├────────────────────────────────────────┤
│  Kaynak Dosya: [Seç...] video.mp4     │
│  Hedef Format: [MKV ▼]                 │
│  Kalite: [Yüksek ▼]                    │
│  ─────────────────────────────         │
│  [Dönüştür] [İptal]                    │
└────────────────────────────────────────┘
```

#### 1.2 Codec Seçimi ve İleri Ayarlar
**Süre:** 1 hafta

**Codec Desteği:**
- **Video:** H.264 (x264), H.265 (x265/HEVC), VP8, VP9, AV1
- **Audio:** AAC, MP3, Opus, Vorbis, FLAC

**Ayarlar:**
- Bitrate kontrolü (CBR/VBR)
- 2-Pass encoding
- Hardware acceleration (NVENC, Quick Sync)

```python
class CodecManager:
    CODECS = {
        'h264': {'lib': 'libx264', 'ext': 'mp4'},
        'h265': {'lib': 'libx265', 'ext': 'mp4'},
        'vp9': {'lib': 'libvpx-vp9', 'ext': 'webm'},
        'av1': {'lib': 'libaom-av1', 'ext': 'mkv'},
    }

    def get_codec_command(self, codec, quality):
        """Codec için FFmpeg parametrelerini döndür"""
        pass
```

#### 1.3 Toplu Dönüştürme (Batch Processing)
**Süre:** 1 hafta

**Özellikler:**
- Çoklu dosya seçimi
- Aynı ayarları tüm dosyalara uygulama
- Sıralı işleme kuyruğu (mevcut sistemle entegre)
- İşlem sonucu raporu

```python
class BatchConverter:
    def __init__(self, converter):
        self.converter = converter
        self.queue = queue.Queue()

    def add_files(self, files, settings):
        """Dönüştürme kuyruğuna ekle"""
        for file in files:
            self.queue.put((file, settings))

    def process_queue(self):
        """Sırayla tüm dosyaları işle"""
        while not self.queue.empty():
            file, settings = self.queue.get()
            self.converter.convert(file, **settings)
```

---

### Faz 2: Codec Analiz ve Medya Bilgileri (Öncelik: Orta)

#### 2.1 Medya Dosya Analizi
**Süre:** 1 hafta

**FFprobe entegrasyonu:**
```python
import json

class MediaAnalyzer:
    def analyze_file(self, file_path):
        """Dosya hakkında detaylı bilgi al"""
        command = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            file_path
        ]

        result = subprocess.run(command, capture_output=True)
        return json.loads(result.stdout)

    def get_video_info(self, data):
        """Video stream bilgileri"""
        video_stream = next(
            s for s in data['streams']
            if s['codec_type'] == 'video'
        )
        return {
            'codec': video_stream['codec_name'],
            'width': video_stream['width'],
            'height': video_stream['height'],
            'fps': eval(video_stream['r_frame_rate']),
            'bitrate': video_stream.get('bit_rate', 'N/A'),
        }
```

**Gösterilecek Bilgiler:**
```
╔════════════════════════════════════════╗
║  Medya Dosya Bilgileri                 ║
╠════════════════════════════════════════╣
║  Dosya: video.mp4                      ║
║  Boyut: 245.8 MB                       ║
║  Süre: 10:45                           ║
╟────────────────────────────────────────╢
║  📹 Video Akışı                        ║
║  Codec: H.264 (High Profile)          ║
║  Çözünürlük: 1920x1080 (Full HD)      ║
║  FPS: 30.00                            ║
║  Bitrate: 2500 kbps                    ║
║  Renk: YUV 4:2:0                       ║
╟────────────────────────────────────────╢
║  🔊 Ses Akışı                          ║
║  Codec: AAC-LC                         ║
║  Kanal: Stereo (2.0)                   ║
║  Örnekleme: 48000 Hz                   ║
║  Bitrate: 192 kbps                     ║
╟────────────────────────────────────────╢
║  📦 Konteyner: MP4 (isom)              ║
║  Toplam Bitrate: 2692 kbps             ║
╚════════════════════════════════════════╝
```

#### 2.2 Codec Uyumluluk Kontrol
**Süre:** 3 gün

**Özellikler:**
- Hedef cihaz/platform seçimi (TV, Mobil, Web)
- Codec uyumluluk kontrolü
- Dönüştürme önerileri

```python
class CompatibilityChecker:
    DEVICES = {
        'smart_tv': {
            'video': ['h264', 'h265'],
            'audio': ['aac', 'ac3'],
            'max_resolution': (3840, 2160),
        },
        'mobile': {
            'video': ['h264'],
            'audio': ['aac'],
            'max_resolution': (1920, 1080),
        },
        'web': {
            'video': ['h264', 'vp8', 'vp9'],
            'audio': ['aac', 'opus'],
            'max_resolution': (1920, 1080),
        }
    }

    def check_compatibility(self, file_info, device):
        """Dosyanın cihazla uyumluluğunu kontrol et"""
        issues = []
        device_specs = self.DEVICES[device]

        if file_info['video_codec'] not in device_specs['video']:
            issues.append('Video codec uyumsuz')

        return issues
```

---
































### Faz 3: Gelişmiş Video Düzenleme (Öncelik: Orta)

#### 3.1 Video Kırpma (Trim)
**Süre:** 4 gün

**Özellikler:**
- Başlangıç ve bitiş zamanı seçimi
- Önizleme (thumbnail'ler)
- Frame-accurate kesim

```python
class VideoTrimmer:
    def trim(self, input_file, start_time, end_time, output_file):
        """Video'yu belirtilen zaman aralığına kırp"""
        command = [
            'ffmpeg',
            '-i', input_file,
            '-ss', start_time,      # 00:01:30
            '-to', end_time,        # 00:03:45
            '-c', 'copy',           # Yeniden encode etme
            output_file
        ]
        subprocess.run(command)
```

**UI:**
```
┌─────────────────────────────────────────┐
│  Video Kırpma                           │
├─────────────────────────────────────────┤
│  Dosya: video.mp4 (Süre: 10:45)        │
│                                         │
│  [════════▓▓▓▓▓▓▓═══════]              │
│  00:00    02:15   05:30        10:45   │
│           ↑ Başla  ↑ Bitir              │
│                                         │
│  Başlangıç: [00:02:15]                  │
│  Bitiş:     [00:05:30]                  │
│  Süre:      00:03:15                    │
│                                         │
│  [Önizle] [Kırp] [İptal]                │
└─────────────────────────────────────────┘
```

#### 3.2 Video Birleştirme (Concatenate)
**Süre:** 3 gün

```python
class VideoMerger:
    def merge(self, input_files, output_file):
        """Birden fazla videoyu birleştir"""
        # concat.txt dosyası oluştur
        with open('concat.txt', 'w') as f:
            for file in input_files:
                f.write(f"file '{file}'\n")

        command = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', 'concat.txt',
            '-c', 'copy',
            output_file
        ]
        subprocess.run(command)
```

#### 3.3 Çözünürlük Değiştirme
**Süre:** 2 gün

```python
class VideoResizer:
    PRESETS = {
        '4K': (3840, 2160),
        '1080p': (1920, 1080),
        '720p': (1280, 720),
        '480p': (854, 480),
    }

    def resize(self, input_file, width, height, output_file):
        """Video çözünürlüğünü değiştir"""
        command = [
            'ffmpeg',
            '-i', input_file,
            '-vf', f'scale={width}:{height}',
            '-c:a', 'copy',  # Ses'i kopyala
            output_file
        ]
        subprocess.run(command)
```






















---

### Faz 4: Ses İşleme Modülü (Öncelik: Düşük)

#### 4.1 Ses Çıkarma ve Dönüştürme
**Süre:** 3 gün

```python
class AudioExtractor:
    def extract_audio(self, video_file, output_format='mp3'):
        """Videodan sesi çıkar"""
        output_file = video_file.rsplit('.', 1)[0] + f'.{output_format}'

        command = [
            'ffmpeg',
            '-i', video_file,
            '-vn',  # Video'suz
            '-acodec', 'libmp3lame' if output_format == 'mp3' else 'copy',
            '-q:a', '2',  # Kalite
            output_file
        ]
        subprocess.run(command)
```

#### 4.2 Ses Normalizasyonu
**Süre:** 2 gün

```python
class AudioNormalizer:
    def normalize(self, audio_file, target_level=-16):
        """Ses seviyesini normalize et"""
        # 2-pass loudnorm filter
        # Pass 1: Analiz
        # Pass 2: Uygula
        pass
```

#### 4.3 Gürültü Azaltma
**Süre:** 4 gün

FFmpeg ile temel gürültü filtresi:
```python
def reduce_noise(self, audio_file):
    """Arka plan gürültüsünü azalt"""
    command = [
        'ffmpeg',
        '-i', audio_file,
        '-af', 'highpass=f=200,lowpass=f=3000',
        output_file
    ]
```

























---

### Faz 5: Altyazı Yönetimi (Öncelik: Düşük)

#### 5.1 Altyazı İndirme
**YouTube-dl ile otomatik altyazı:**
```python
class SubtitleDownloader:
    def download_subtitles(self, video_url, language='tr'):
        """YouTube'dan altyazı indir"""
        ydl_opts = {
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': [language],
            'skip_download': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
```

#### 5.2 Altyazı Format Dönüştürme
**SRT, VTT, ASS arası dönüşüm:**
```python
class SubtitleConverter:
    def convert(self, input_sub, output_format):
        """Altyazı formatını dönüştür"""
        # FFmpeg ile dönüştürme
        pass
```

#### 5.3 Altyazı Gömme (Hard-sub)
```python
def embed_subtitle(self, video_file, subtitle_file):
    """Altyazıyı video'ya gömülü olarak ekle"""
    command = [
        'ffmpeg',
        '-i', video_file,
        '-vf', f"subtitles={subtitle_file}",
        output_file
    ]
```

---

## 🏗️ Yeni Mimari Yapı

### Modüler Tasarım

```
ravn/
├── core/
│   ├── __init__.py
│   ├── downloader.py      # Mevcut YouTube indirici
│   ├── converter.py       # Video dönüştürücü
│   ├── analyzer.py        # Medya analiz
│   └── editor.py          # Video düzenleme
├── ui/
│   ├── __init__.py
│   ├── main_window.py     # Ana pencere
│   ├── downloader_tab.py  # İndirme sekmesi
│   ├── converter_tab.py   # Dönüştürme sekmesi
│   └── analyzer_tab.py    # Analiz sekmesi
├── utils/
│   ├── __init__.py
│   ├── ffmpeg_wrapper.py  # FFmpeg yardımcıları
│   ├── file_utils.py      # Dosya işlemleri
│   └── config.py          # Ayarlar
├── assets/
│   └── themes/
└── ravn.py                # Ana giriş noktası
```

### Sekme Tabanlı Arayüz

```
┌─────────────────────────────────────────────┐
│  RAVN - Media Manager                       │
├─────────────────────────────────────────────┤
│ [📥 İndir] [🔄 Dönüştür] [🔍 Analiz]        │
├─────────────────────────────────────────────┤
│                                             │
│  Aktif sekmeye göre içerik                  │
│                                             │
│                                             │
└─────────────────────────────────────────────┘
```

---

## 📊 Performans Hedefleri

### Dönüştürme Hızları (Tahmin)
- 1080p → 720p: ~2x gerçek zamanlı
- MP4 → MKV (remux): ~10x gerçek zamanlı
- H.264 → H.265: ~0.5x gerçek zamanlı

### Bellek Kullanımı
- İndirme: 150-200 MB
- Dönüştürme: 200-400 MB
- Analiz: 50-100 MB

---

## 🔧 Gerekli Kütüphaneler (Güncelleme)

```txt
# requirements.txt
customtkinter>=5.0.0
Pillow>=9.0.0
yt-dlp
pydub              # Ses işleme
moviepy>=1.0.3     # Video düzenleme (opsiyonel)
```

---

## 📝 Dokümantasyon Güncellemeleri

Her faz tamamlandıkça:
1. API dokümantasyonu ekle
2. Kullanım örnekleri hazırla
3. Video tutorial kayıtları
4. Changelog güncelle

---

## 🚀 Hızlı Başlangıç (Gelecek Versiyon)

```python
# Dönüştürme örneği
from ravn.core.converter import VideoConverter

converter = VideoConverter()
converter.convert(
    input_file='video.mp4',
    output_format='mkv',
    codec='h265',
    quality='high'
)

# Analiz örneği
from ravn.core.analyzer import MediaAnalyzer

analyzer = MediaAnalyzer()
info = analyzer.analyze('video.mp4')
print(f"Codec: {info.video_codec}")
print(f"Resolution: {info.resolution}")
```

---

## 📅 Zaman Çizelgesi (Tahmini)

| Faz | Özellik | Süre | Başlangıç | Bitiş |
|-----|---------|------|-----------|-------|
| 1.1 | Temel Dönüştürme | 2 hafta | Hafta 1 | Hafta 2 |
| 1.2 | Codec Seçimi | 1 hafta | Hafta 3 | Hafta 3 |
| 1.3 | Toplu İşlem | 1 hafta | Hafta 4 | Hafta 4 |
| 2.1 | Medya Analizi | 1 hafta | Hafta 5 | Hafta 5 |
| 2.2 | Uyumluluk Kontrolü | 3 gün | Hafta 6 | Hafta 6 |
| 3.1 | Video Kırpma | 4 gün | Hafta 7 | Hafta 7 |
| 3.2 | Video Birleştirme | 3 gün | Hafta 7 | Hafta 7 |
| 3.3 | Çözünürlük | 2 gün | Hafta 8 | Hafta 8 |
| 4 | Ses Modülü | 1 hafta | Hafta 9 | Hafta 9 |
| 5 | Altyazı | 1 hafta | Hafta 10 | Hafta 10 |

**Toplam Geliştirme Süresi:** ~10 hafta (2.5 ay)

---

## ✅ Kontrol Listesi

### Başlamadan Önce
- [ ] Mevcut kodu modüler yapıya taşı
- [ ] FFmpeg tüm codec'leri destekliyor mu kontrol et
- [ ] Unit test altyapısı kur
- [ ] Git branching stratejisi belirle

### Her Faz İçin
- [ ] Özellik dokümantasyonu yaz
- [ ] Kod yaz ve test et
- [ ] UI entegrasyonu yap
- [ ] Kullanıcı testleri yap
- [ ] Bug düzeltmeleri
- [ ] Versiyon güncelle

---

**Son Güncelleme:** 18 Kasım 2025
**Durum:** Yol Haritası - Planlama Aşaması
