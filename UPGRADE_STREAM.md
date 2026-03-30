# UPGRADE_STREAM.md
## RAVN — Torrent / Magnet Akış ve İndirme Entegrasyonu

> **Bu dosya bir agent yönergesidir.**
> Kodu uygulamadan önce `AGENT.md`, `CLAUDE.md`, `ARCHITECTURE.md`, `README.md` ve `PROGRESS.md` dosyalarını tek bir bütünleşik bağlam olarak oku ve içlerindeki tüm kuralları, kısıtlamaları ve bağlamı harfiyen uygula.

---

## 1. Amaç

RAVN'ı salt YouTube/sosyal medya indirici konumundan çıkararak tam teşekküllü bir medya edinme ve yönetim istasyonuna dönüştürmek. Hedef: **magnet bağlantısı** ve **torrent dosyası** desteğini mevcut runner mimarisine entegre etmek; aynı zamanda sıralı indirme üzerinden **akış (stream)** ve **yerel HTTP oynatma** imkânı sunmak.

---

## 2. Mevcut Durum Özeti (Okumadan önce doğrula)

| Dosya | Rol |
|---|---|
| `ravn_app/core/runners.py` | `BaseRunner`, `FFmpegRunner`, `YtDlpRunner` |
| `ravn_app/core/downloader.py` | `YouTubeDownloader` → `YtDlpRunner` |
| `ravn_app/core/task_manager.py` | `TaskQueue`, `TaskType`, `Task` |
| `ravn_app/ui/main_window.py` | `_download_video()`, `url_entry`, URL yönlendirme |
| `ravn_app/ui/ui_components.py` | `ToastManager`, `Tooltip`, `InlineErrorLabel` |
| `ravn_app/core/error_handler.py` | FFmpeg/yt-dlp hata parse |
| `ravn_app/core/config_paths.py` | OS-aware yol çözümü |
| `ravn_app/ui/design_tokens.py` | `Icons`, `Colors`, `Spacing` |

**Mevcut test sayısı:** 418 toplanan, 417 geçen, 1 atlanan. Bu sayılar bozulmamalı.

---

## 3. Yeni Bağımlılıklar

### 3.1 Harici araç: `aria2c`
- `aria2c` komut satırı aracı, hem magnet hem `.torrent` dosyalarını destekler.
- Kullanıcı `PATH`'te `aria2c`'ye sahip olmalı **veya** RAVN kurulum dizininde `aria2c.exe` / `aria2c` bulunmalı.
- `BaseRunner._find_executable()` zaten bu mantığı destekliyor — doğrula ve kullan.
- `requirements.txt`'e Python paketi **ekleme**; aria2c bir sistem aracıdır.

### 3.2 İsteğe bağlı Python paketi: `python-libtorrent`
- Akış (streaming) özelliği için `python-libtorrent` veya `libtorrent` paketi kullanılabilir.
- Bu paket **zorunlu değil**; `aria2c` sıralı indirme de akış sağlar.
- Kurulu değilse özellik sessizce devre dışı kalmalı (graceful fallback).

### 3.3 `requirements.txt` güncellemesi
```
# Torrent desteği (isteğe bağlı - kurulu değilse torrent akışı devre dışı)
# libtorrent>=2.0.0  # pip install python-libtorrent
```
Sadece yorum satırı olarak ekle; zorunlu bağımlılık yapma.

---

## 4. Mimari Akış Diyagramı (Hedef)

```
URL Girişi (url_entry)
        │
        ▼
_detect_url_protocol(url)   ←── YENİ: protokol algılama yardımcısı
        │
   ┌────┴────────────────────┐
   │                         │
   ▼                         ▼
"magnet:" ile başlar     http(s):// veya diğer
"*.torrent" dosyası            │
        │                      │
        ▼                      ▼
TorrentDownloader         YouTubeDownloader
   (YENİ sınıf)          (mevcut sınıf)
        │                      │
        ▼                      ▼
  Aria2Runner             YtDlpRunner
   (YENİ runner)          (mevcut runner)
        │
   ┌────┴──────────────┐
   │                   │
   ▼                   ▼
İndirme modu       Akış modu
(tam indirme)   (sequential + yerel HTTP)
```

---
.



## 5. Güncel Dosya Haritası (Phase 0 sonrası)

```
ravn_app/core/runners/
  __init__.py        ← BaseRunner, FFmpegRunner, YtDlpRunner re-export
  base.py            ← BaseRunner, RunnerStatus, RunnerResult
  ffmpeg.py          ← FFmpegRunner
  ytdlp.py           ← YtDlpRunner
  aria2.py           ← Aria2Runner  ← PHASE 6A BURAYA

ravn_app/core/
  downloader.py      ← YouTubeDownloader (dokunma)
  torrent_downloader.py              ← PHASE 6B BURAYA
  error_handler.py   ← parse_ffmpeg_error, parse_ytdlp_error
  task_manager.py    ← TaskType: DOWNLOAD, CONVERT  ← TORRENT eklenecek

ravn_app/ui/tabs/
  download_tab.py    ← 712 satır, _download_video() L594, _start_single_download() L561
  _download_playlist.py  ← PlaylistMixin
  _download_feedback.py  ← FeedbackMixin

ravn_app/ui/components/
  url_input.py       ← url_entry widget'ı burada tanımlı
```

**Test durumu:** `pytest -q` → `417 passed, 1 skipped`. Her faz sonrası doğrula.

---

## 6. Fazlar ve Görevler

### PHASE 6A — `Aria2Runner`

**Oku:** `ravn_app/core/runners/base.py`, `ravn_app/core/runners/ytdlp.py`
**Oluştur:** `ravn_app/core/runners/aria2.py`
**Güncelle:** `ravn_app/core/runners/__init__.py`

- [x] `Aria2Runner(BaseRunner)` sınıfını yaz:
  - `__init__(self, aria2c_path: str = "aria2c")` → `super().__init__(aria2c_path)`
  - `_build_command(self, source: str, output_dir: str, sequential: bool, seed_time: int, extra_args: list) -> List[str]`
    - Sabit flag'ler: `--dir`, `--console-log-level=notice`, `--show-console-readout=false`, `--summary-interval=1`
    - `sequential=True` ise: `--file-allocation=none`, `--enable-sequential=true`, `--bt-prioritize-piece=head=5M`
    - `seed_time=0` ise: `--seed-time=0`
  - `_parse_error(self, stderr: str) -> str` — aria2c errorCode'larını map et (1=bilinmeyen, 3=kaynak yok, 6=ağ hatası, 9=disk dolu, 13=dosya var)
  - `download(self, source, output_dir, sequential=False, seed_time=0, progress_callback=None, timeout=None) -> RunnerResult`
    - `_run_torrent_with_progress()` private metodunu kullan
  - `_run_torrent_with_progress()`: `subprocess.Popen` ile stdout satır satır oku, `r'\((\d+)%\)'` ve `r'DL:(\S+)'` regex ile parse et, `progress_callback(percent, mesaj)` çağır
  - `is_available(self) -> bool` → `self._find_executable("aria2c") is not None`

- [x] `__init__.py`'ye ekle:
  ```python
  from ravn_app.core.runners.aria2 import Aria2Runner, get_aria2c_runner
  ```
  `__all__` listesine de ekle.

- [x] `get_aria2c_runner(aria2c_path: str = "aria2c") -> Aria2Runner` fabrika fonksiyonu

- [x] `tests/test_runners.py`'ye `TestAria2Runner` ekle:
  - `_build_command()` çıktı doğrulama
  - `_parse_error()` errorCode map testleri
  - `_parse_progress()` regex testleri
  - `is_available()` mock testi

**Kural:** `YtDlpRunner._run_process()` yerine kendi `_run_torrent_with_progress()` yaz — `self.status` ve `self.current_process` yönetimini `base.py`'deki `_run_process()` ile özdeş tut.

---

### PHASE 6B — `TorrentDownloader`

**Oku:** `ravn_app/core/downloader.py`, `ravn_app/core/runners/aria2.py` (6A çıktısı)
**Oluştur:** `ravn_app/core/torrent_downloader.py`

- [x] `TorrentSource(Enum)`: `MAGNET = "magnet"`, `TORRENT_FILE = "torrent_file"`

- [x] `TorrentDownloadMode(Enum)`: `FULL = "full"`, `SEQUENTIAL = "sequential"`, `STREAM = "stream"`

- [x] `TorrentDownloadResult` dataclass:
  ```python
  success: bool
  source: str
  output_files: List[str]
  error_message: str = ""
  stream_url: Optional[str] = None
  ```

- [x] `TorrentDownloader` sınıfı:
  - `__init__(self, aria2c_path: str = "aria2c")` → `self._runner = Aria2Runner(aria2c_path)`
  - `is_available(self) -> bool` → `self._runner.is_available()`
  - `detect_source_type(self, source: str) -> TorrentSource`:
    - `source.startswith("magnet:?xt=urn:")` → `MAGNET`
    - `source.lower().endswith(".torrent")` → `TORRENT_FILE`
  - `download(self, source, output_dir, mode=TorrentDownloadMode.FULL, progress_callback=None, seed_time=0) -> TorrentDownloadResult`
  - `_start_local_http_server(self, file_path: str) -> str`:
    - `http.server.HTTPServer` + `socket.bind(('127.0.0.1', 0))` ile random port
    - Daemon thread'de çalıştır
    - `"http://127.0.0.1:{port}/{filename}"` döndür
  - `_stop_local_http_server(self)`
  - `cancel(self) -> bool` → `self._runner.cancel()`

- [x] `tests/test_torrent_downloader.py` oluştur:
  - `detect_source_type()` testleri
  - `is_available()` mock testi
  - `TorrentDownloadResult` dataclass testleri

**Kural:** `downloader.py`'ye dokunma. `torrent_downloader.py` → `runners/aria2.py` import eder, başka yön import yok.

---

### PHASE 6C — Hata Yönetimi

**Oku:** `ravn_app/core/error_handler.py`
**Güncelle:** `ravn_app/core/error_handler.py`

- [x] `parse_ffmpeg_error` ve `parse_ytdlp_error` ile aynı imzada `parse_aria2c_error(stderr: str, return_code: int = 1) -> str` fonksiyonu ekle
- [x] aria2c errorCode map:
  ```
  errorCode=1  → Bilinmeyen hata
  errorCode=2  → Zaman aşımı
  errorCode=3  → Kaynak bulunamadı
  errorCode=6  → Ağ hatası
  errorCode=9  → Disk dolu
  errorCode=13 → Dosya zaten mevcut
  errorCode=24 → Kimlik doğrulama hatası
  ```
- [x] `Aria2Runner._parse_error()` içinde `parse_aria2c_error()` çağır (6A'ya geri dön ve güncelle)

---

### PHASE 6D — URL Router + Drag-Drop

**Oku:** `ravn_app/ui/tabs/download_tab.py` (tamamı), `ravn_app/core/task_manager.py`
**Güncelle:** `ravn_app/ui/tabs/download_tab.py`, `ravn_app/core/task_manager.py`

- [x] `task_manager.py` → `TaskType` enum'una `TORRENT = "torrent"` ekle

- [x] `download_tab.py` import bloğuna ekle:
  ```python
  from ravn_app.core.torrent_downloader import TorrentDownloader, TorrentDownloadMode
  ```

- [x] `__init__` içinde: `self.torrent_downloader = TorrentDownloader()`

- [x] `_detect_url_protocol(url: str) -> str` static metodu:
  - `url.startswith("magnet:?xt=urn:")` → `"magnet"`
  - `url.lower().endswith(".torrent")` → `"torrent_file"`
  - Diğer → `"standard"`

- [x] `_download_video()` (L594) içinde, `url` alındıktan hemen sonra:
  ```python
  protocol = self._detect_url_protocol(url)
  if protocol in ("magnet", "torrent_file"):
      self._start_torrent_download(url)
      return
  ```
  Mevcut akış (`standard`) hiç değişmez.

- [x] `_start_torrent_download(self, source: str)`:
  - `self.torrent_downloader.is_available()` → False ise `ToastManager` ile "aria2c bulunamadı" uyarısı, return
  - `output_dir` → config'den al (mevcut `_start_single_download()` ile aynı yöntem)
  - `self.task_queue.add_task(task_type=TaskType.TORRENT, ...)` ile kuyruğa ekle
  - `progress_callback` → `self.after(0, ...)` ile thread-safe UI güncelleme

- [x] `_on_url_focus_out()` (L394): magnet ve `.torrent` URL'lerini geçerli say — mevcut validasyona ek dal

- [x] Drag-drop `.torrent` dosyası:
  - `drop_target_register(DND_FILES)` + `dnd_bind('<<Drop>>', self._on_torrent_file_drop)`
  - `_on_torrent_file_drop(self, event)`:
    - Uzantı `.torrent` değilse toast uyarı
    - `self.url_entry.delete(0, 'end')` + `self.url_entry.insert(0, file_path)`

**Kural:** `_download_video()` içindeki `standard` dalı tek satır bile değişmez. `self.after()` olmadan UI'a dokunma.

---

### PHASE 6E — Ayarlar

**Oku:** `ravn_app/ui/tabs/settings_tab.py`
**Güncelle:** `ravn_app/ui/tabs/settings_tab.py`

- [x] Mevcut "İndirme" ayarları bölümüne ekle:
  - `aria2c_path` — `CTkEntry`, varsayılan `"aria2c"`
  - `torrent_seed_time` — `CTkSlider` veya `CTkEntry`, 0–60 dakika, varsayılan `0`
  - `torrent_max_connections` — `CTkEntry`, varsayılan `16`

- [x] Her alan `ConfigManager` üzerinden kayıt/yükle:
  ```json
  {
    "aria2c_path": "aria2c",
    "torrent_seed_time": 0,
    "torrent_max_connections": 16
  }
  ```

- [x] `download_tab.py` içinde `TorrentDownloader` oluşturulurken config'deki `aria2c_path`'i kullan

---

### PHASE 6F — CLI

**Oku:** `ravn_app/cli.py`
**Güncelle:** `ravn_app/cli.py`

- [x] `@cli.command("torrent")` ekle:
  ```
  ravn torrent <source> [--output-dir <dir>] [--sequential] [--seed-time <dk>] [--json]
  ```
  - `source`: magnet URI veya `.torrent` dosya yolu
  - `TorrentDownloader` kullan
  - `--json` flag desteği (diğer komutlarla tutarlı)
  - `is_available()` False ise hata mesajıyla çık

---

### PHASE 6G — Akış (Stream) UI  *(isteğe bağlı)*

**Oku:** `ravn_app/ui/tabs/download_tab.py`, `ravn_app/ui/tabs/_download_feedback.py`

- [x] Torrent kaynağı algılandığında (6D'den sonra) görünür hale gelen `CTkSegmentedButton`:
  - Seçenekler: `"Tam İndir"`, `"Sıralı"`, `"Akışla İzle"`
  - Widget adı: `self.torrent_mode_selector`
  - Standard URL'de gizli (`pack_forget`)

- [x] `"Akışla İzle"` seçili + indirme başlayınca:
  - `TorrentDownloadMode.STREAM` ile çağır
  - İlk %5 inince HTTP URL oluştur
  - "Oynatıcıda Aç" butonu göster

- [x] `_open_with_player(self, url: str)`:
  - Windows: `os.startfile(url)`
  - Linux/macOS: `subprocess.Popen(["xdg-open", url])`

**Not:** `TorrentDownloader.is_available()` False ise bu bölüm tamamen gizli kalır.

---

### PHASE 6H — Dökümantasyon

**Güncelle:** `AGENT.md`, `CLAUDE.md`, `PROGRESS.md`, `ARCHITECTURE.md`, `README.md`, `TASKS.md`

- [ ] `AGENT.md` → `Verified Facts` + `Start Here` güncelle
- [x] `CLAUDE.md` → `Current Reality` + `Quick Context` güncelle
- [x] `PROGRESS.md` → Phase 6 tamamlananları işaretle
- [x] `ARCHITECTURE.md` → `runners/` paketi, `torrent_downloader.py`, torrent akışı ekle
- [ ] `README.md` → özellikler listesi + `aria2c` sistem gereksinimi
- [x] `TASKS.md` → Phase 6 satırları

---

## 7. Genel Kurallar (Her Fazda Geçerli)

- `pytest -q` → her faz sonunda `417+` passed. Düşerse devam etme.
- Tüm UI güncellemeleri `self.after(0, callback)` ile — thread-safe olmayan hiçbir widget erişimi yok.
- `aria2c` yoksa uygulama çökmez — `ToastManager` uyarı + graceful return.
- Yerel HTTP sunucu yalnızca `127.0.0.1` dinler, asla `0.0.0.0` değil.
- `downloader.py` ve `YouTubeDownloader` hiç değişmez.
- Yeni dosya oluştururken import döngüsü yok: `torrent_downloader.py` → `runners/aria2.py` tek yön.



