# RAVN - Güncellenmiş Özellikler (Faz 1-5)

## 🎯 Genel Bakış

RAVN artık tam özellikli bir medya yönetim uygulamasıdır:
- ✅ **Faz 1**: YouTube İndirme
- ✅ **Faz 2**: Video Dönüştürme
- ✅ **Faz 3**: Altyazı Yönetimi
- ✅ **Faz 4**: Veritabanı & Konfigürasyon
- ✅ **Faz 5**: Gelişmiş UI/UX

---

## 📱 Sekmeler

### 📥 İndir (Faz 1)
- YouTube video/audio indirme
- MP4, MP3 formatları
- 1080p, 720p, 480p kalite seçimi
- Playlist desteği
- Kuyruk sistemi

### 🔄 Dönüştür (Faz 2)
**Format Dönüştürme:**
- Giriş: MP4, MKV, AVI, WEBM, MOV, FLV
- Çıkış: MP4, MKV, AVI, WEBM, MOV, FLV

**Codec Seçimi:**
- Video: H.264, H.265/HEVC, VP9, AV1
- Audio: AAC, MP3, Opus, Vorbis, FLAC

**Kalite Presetleri:**
- Ultra (CRF 18)
- High (CRF 23)
- Medium (CRF 28)
- Low (CRF 35)

**Ek Özellikler:**
- Donanım hızlandırma (NVIDIA NVENC, Intel QSV)
- Toplu dönüştürme
- Video analiz (FFprobe)
- Video düzenleme (kırpma, ölçeklendirme)
- GIF oluşturma
- Audio çıkarma

### 📝 Altyazı (Faz 3)
**İndirme:**
- YouTube'dan otomatik altyazı indirme
- Çoklu dil desteği (tr, en, vb.)
- Manuel/otomatik altyazı seçimi

**Dönüştürme:**
- SRT ↔ VTT ↔ ASS ↔ SSA format dönüşümü
- FFmpeg tabanlı dönüştürme

**Düzenleme:**
- Zamanlama kaydırma (+/- 10 saniye)
- Birden fazla altyazı birleştirme
- HTML/ASS formatlamasını kaldırma

**Video Entegrasyonu:**
- Soft subtitle (ayrı stream)
- Hard subtitle (videoya gömülü)
- Font boyutu/renk ayarlama
- Altyazı çıkarma

### 📚 Geçmiş (Faz 4)
**İndirme Geçmişi:**
- Tüm indirmelerin kaydı
- Dosya boyutu, kalite, format bilgileri
- Tarih ve durum takibi
- Dosyaya hızlı erişim

**Arama & Filtreleme:**
- Metin araması (başlık, URL)
- Format filtresi (MP4, MP3, MKV)
- Durum filtresi (tamamlandı, başarısız, iptal)

**İstatistikler:**
- Toplam indirme sayısı
- Toplam dosya boyutu
- Başarı oranı
- En popüler format
- Toplam dönüştürme sayısı

**Favoriler:**
- URL favorilere ekleme
- Favori listesi görüntüleme
- Hızlı erişim

### ⚙️ Ayarlar (Faz 4 & 5)
**Genel Ayarlar:**
- Tema seçimi (5 tema)
- Dil ayarı (Türkçe/İngilizce)
- Bildirim ayarları
- Otomatik güncelleme kontrolü

**İndirme Ayarları:**
- Varsayılan indirme dizini
- Varsayılan format (MP4, MP3, MKV)
- Varsayılan kalite (En İyi, 1080p, 720p, 480p)
- Eşzamanlı indirme sayısı (1-5)

**Dönüştürme Ayarları:**
- FFmpeg yolu
- Otomatik temizlik (kaynak dosya silme)

**Gelişmiş Ayarlar:**
- Geçmiş kayıt limiti
- Otomatik altyazı indirme
- Tercih edilen altyazı dili

**İçe/Dışa Aktarma:**
- Ayarları JSON olarak dışa aktar
- Önceki ayarları içe aktar
- Fabrika ayarlarına sıfırlama

---

## 🎨 Temalar

### Nordic (Varsayılan)
- Primary: #5E81AC (Mavi)
- Background: #2E3440 (Koyu gri)
- Skandinav minimalist tasarım

### Forest
- Primary: #8FBC8F (Açık yeşil)
- Background: #2F4F2F (Orman yeşili)
- Doğa temalı

### Aurora
- Primary: #BF616A (Kırmızı-pembe)
- Background: #3B4252 (Koyu)
- Kuzey ışıkları esinli

### Dark
- Primary: #1E1E1E (Koyu)
- Background: #121212 (Siyah)
- OLED dostu

### Light
- Primary: #FFFFFF (Beyaz)
- Background: #FAFAFA (Açık gri)
- Aydınlık mod

---

## ⌨️ Klavye Kısayolları

| Kısayol | İşlev |
|---------|-------|
| Ctrl+V | URL yapıştır |
| Ctrl+P | Ayarları aç |
| Ctrl+Q | Uygulamadan çık |

---

## 🗂️ Veritabanı Yapısı

### downloads (İndirme Geçmişi)
- id, url, title, format, quality
- file_path, file_size, download_date
- status, duration, thumbnail_url

### conversions (Dönüştürme Geçmişi)
- id, input_file, output_file
- input_codec, output_codec
- conversion_date, duration, status

### favorites (Favoriler)
- id, url, title, added_date

### playlists (Playlist Geçmişi)
- id, url, title, video_count, last_checked

---

## 🔌 Plugin Sistemi (Faz 4)

### Event Hook'ları:
```python
on_download_start(video_info)    # İndirme başladı
on_download_complete(file_path)  # İndirme tamamlandı
on_convert_start(input, output)  # Dönüştürme başladı
on_convert_complete(output_file) # Dönüştürme tamamlandı
```

### Örnek Plugin:
```python
class MyPlugin(PluginInterface):
    def on_download_complete(self, file_path):
        print(f"İndirme tamamlandı: {file_path}")

# Plugin kaydetme
plugin_manager = PluginManager()
plugin_manager.register_plugin(MyPlugin())
```

---

## 📦 Opsiyonel Özellikler (Faz 5)

### Drag & Drop Desteği
```bash
pip install tkinterdnd2
```
- Dosyaları sürükleyip bırakma
- Çoklu dosya seçimi

### Sistem Tray
```bash
pip install pystray
```
- Arka planda çalışma
- Sistem tray ikonu
- Sağ tık menüsü

### Bildirimler (Windows)
```bash
pip install win10toast
```
- İndirme tamamlandı bildirimi
- Dönüştürme tamamlandı bildirimi
- Hata bildirimleri

---

## 🚀 Hızlı Başlangıç

```bash
# 1. Bağımlılıkları yükle
pip install -r requirements.txt

# 2. Uygulamayı başlat
python ravn.py

# 3. İlk kullanımda:
# - Ayarlar sekmesinden tema seç
# - İndirme dizini belirle
# - FFmpeg yolunu kontrol et
```

---

## 📊 Performans

### Video Dönüştürme:
- **H.264**: ~30 FPS (CPU)
- **H.265**: ~20 FPS (CPU)
- **VP9**: ~15 FPS (CPU)
- **Donanım hızlandırma ile**: 2-3x hız artışı

### Altyazı İşleme:
- İndirme: ~5 saniye/video
- Format dönüştürme: <1 saniye
- Hard subtitle: Video uzunluğuna bağlı

### Veritabanı:
- 10,000 kayıt: <100ms sorgulama
- SQLite ACID uyumlu

---

## 🛠️ Sorun Giderme

### "FFmpeg bulunamadı" Hatası:
```bash
# FFmpeg'i PATH'e ekleyin veya Ayarlar'dan yolu belirtin
```

### "yt-dlp hatası":
```bash
# yt-dlp'yi güncelleyin
pip install -U yt-dlp
```

### "Altyazı indirilemedi":
- Video'nun altyazısı olduğundan emin olun
- İnternet bağlantınızı kontrol edin

### Veritabanı Sıfırlama:
```bash
# ravn_history.db dosyasını silin, yeniden oluşturulacak
```

---

## 📄 Lisans

MIT License - Detaylar için `LICENSE` dosyasına bakın.

---

## 🙏 Teşekkürler

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - YouTube indirme
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) - Modern UI
- [FFmpeg](https://ffmpeg.org/) - Medya işleme

---

**RAVN** - Rapid Audio-Video Networking
Versiyon: 2.0.0 (Faz 1-5 Tamamlandı)
Geliştirici: waldseelen
