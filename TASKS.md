# RAVN — Project Task Board
**TR:** Tüm geliştirme görevleri, öncelik sırasına göre fazlara ayrılmıştır.
**EN:** All development tasks are organized into phases by priority.

---

## Legend / Gösterge
- `[ ]` — Not started / Başlanmadı
- `[~]` — In progress / Devam ediyor
- `[x]` — Done / Tamamlandı
- `[!]` — Blocked / Engellenmiş

---

## Phase 1 — Stabilization & Core Rewrite
> **TR:** Mevcut tüm çekirdek fonksiyonlar gözden geçirilecek, gerekirse yeniden yazılacak ve optimize edilecek. FFmpeg + yt-dlp ile yapılabilecek her şey bu iki araç üzerinden yönetilecek.
> **EN:** All existing core functions will be reviewed, rewritten where necessary, and optimized. Everything achievable via FFmpeg + yt-dlp must go through those two tools.

- [ ] **[STAB-01]** Audit all `subprocess` calls to FFmpeg — replace with unified `FFmpegRunner` wrapper class
  _TR: Tüm FFmpeg subprocess çağrılarını tek bir `FFmpegRunner` sınıfında topla_

- [ ] **[STAB-02]** Audit all `yt-dlp` calls — replace with unified `YtDlpRunner` wrapper class
  _TR: Tüm yt-dlp çağrılarını tek bir `YtDlpRunner` sınıfında topla_

- [ ] **[STAB-03]** Rewrite `converter.py` — ensure every conversion path uses `FFmpegRunner`; remove dead code
  _TR: `converter.py` yeniden yazılsın, tüm dönüşüm yolları `FFmpegRunner` kullansın_

- [ ] **[STAB-04]** Rewrite `downloader.py` — ensure every download path uses `YtDlpRunner`; add retry logic
  _TR: `downloader.py` yeniden yazılsın, retry mekanizması eklensin_

- [ ] **[STAB-05]** Rewrite `audio_normalizer.py` — consolidate duplicate FFmpeg flag logic
  _TR: `audio_normalizer.py` içindeki tekrarlanan FFmpeg flag mantığı birleştirilsin_

- [ ] **[STAB-06]** Rewrite `subtitle_manager.py` — use FFmpeg subtitle embedding exclusively
  _TR: Altyazı gömme işlemleri tamamen FFmpeg üzerinden yapılsın_

- [ ] **[STAB-07]** Add proper queue/task manager for all long-running operations (download, convert, merge)
  _TR: İndirme, dönüştürme, birleştirme işlemleri için merkezi bir kuyruk/görev yöneticisi eklensin_

- [ ] **[STAB-08]** Ensure all background threads communicate results back via thread-safe callbacks (no direct UI calls from threads)
  _TR: Arka plan thread'lerinden UI'ya doğrudan erişim kaldırılsın, callback tabanlı iletişim kullanılsın_

- [ ] **[STAB-09]** Add structured logging system — write logs to `~/.config/ravn/logs/ravn.log`
  _TR: Yapılandırılmış loglama sistemi eklensin, loglar uygun dizine yazılsın_

- [ ] **[STAB-10]** Harden error handling — every FFmpeg/yt-dlp failure must produce a clean, human-readable error
  _TR: Her hata için anlaşılır Türkçe/İngilizce mesaj üretilsin, ham FFmpeg çıktısı kullanıcıya gösterilmesin_

---

## Phase 2 — High Priority Features
> **TR:** Kullanıcı deneyimini hemen etkileyen yüksek öncelikli özellikler.
> **EN:** High-impact features that immediately improve user experience.

### 2A — Config File Relocation / Config Dosyası Taşıma
- [ ] **[CFG-01]** Detect OS at startup and resolve config directory:
  - Linux/macOS → `~/.config/ravn/`
  - Windows → `%APPDATA%\ravn\`
  _TR: Uygulama başlangıcında işletim sistemi tespit edilsin ve config dizini buna göre belirlenmeli_

- [ ] **[CFG-02]** Migrate existing `ravn_config.json` from project root to new config dir on first run
  _TR: İlk çalıştırmada mevcut config dosyası yeni dizine taşınsın_

- [ ] **[CFG-03]** Move `ravn_history.db` to config directory as well
  _TR: Veritabanı dosyası da yeni config dizinine taşınsın_

- [ ] **[CFG-04]** Add config schema validation with sensible defaults
  _TR: Config dosyası için şema doğrulaması ve varsayılan değerler eklensin_

### 2B — FFmpeg Error Messages / FFmpeg Hata Mesajları
- [ ] **[FFE-01]** Create an `FFmpegErrorParser` class that maps common FFmpeg exit codes and stderr patterns to user-friendly messages (TR + EN)
  _TR: FFmpeg hata çıktılarını anlaşılır mesajlara çeviren bir sınıf yazılsın_

- [ ] **[FFE-02]** Replace all raw FFmpeg stderr displays in UI with parsed messages
  _TR: UI'da gösterilen tüm ham FFmpeg hataları temiz mesajlarla değiştirilsin_

- [ ] **[FFE-03]** Add "Show technical details" toggle in error dialogs for power users
  _TR: Hata diyaloglarına "Teknik detayları göster" seçeneği eklensin_

### 2C — Drag & Drop Support / Sürükle-Bırak Desteği
- [ ] **[DND-01]** Add `tkinterdnd2` to `requirements.txt` (remove comment)
  _TR: `tkinterdnd2` requirements.txt'e aktif olarak eklenmeli_

- [ ] **[DND-02]** Enable drag & drop on the Converter tab — accept video/audio file drops
  _TR: Dönüştürücü sekmesinde dosya sürükle-bırak aktif edilsin_

- [ ] **[DND-03]** Enable drag & drop on the Subtitle tab — accept subtitle and video file drops
  _TR: Altyazı sekmesinde sürükle-bırak aktif edilsin_

- [ ] **[DND-04]** Show visual drop zone highlight when dragging files over the app
  _TR: Dosya sürüklendiğinde görsel bir drop zone göstergesi eklensin_

### 2D — CLI Interface / Komut Satırı Arayüzü
- [ ] **[CLI-01]** Create `ravn/cli.py` — entry point for command-line usage
  _TR: `ravn/cli.py` oluşturulsun, komut satırı giriş noktası olsun_

- [ ] **[CLI-02]** Implement `ravn download <url> [--quality] [--format] [--output]`
  _TR: `ravn download` komutu eklensin_

- [ ] **[CLI-03]** Implement `ravn convert <file> [--format] [--quality] [--codec] [--output]`
  _TR: `ravn convert` komutu eklensin_

- [ ] **[CLI-04]** Implement `ravn info <file>` — show video metadata (duration, codec, resolution, bitrate)
  _TR: `ravn info` komutu — video bilgilerini göstersin_

- [ ] **[CLI-05]** Implement `ravn subtitle <video> --embed <subtitle-file>`
  _TR: `ravn subtitle` komutu — altyazı gömme için_

- [ ] **[CLI-06]** Implement `ravn history` — list recent operations from DB
  _TR: `ravn history` komutu — geçmiş işlemleri listelesin_

- [ ] **[CLI-07]** Add `--json` output flag to all CLI commands for scripting
  _TR: Tüm CLI komutlarına `--json` çıktı bayrağı eklensin_

- [ ] **[CLI-08]** Register `ravn` as a console script in `setup.py` / `pyproject.toml`
  _TR: `ravn` komutu sistem PATH'ine kayıt edilsin_

---

## Phase 3 — Medium Priority Features
> **TR:** Orta vadede uygulanacak özellik eklemeleri.
> **EN:** Feature additions to be implemented in the medium term.

### 3A — New Platform Support / Yeni Platform Desteği
- [ ] **[PLT-01]** Add TikTok platform handler in `platform_support.py`
  _TR: TikTok platform desteği eklensin_

- [ ] **[PLT-02]** Add Instagram platform handler (Reels, posts) in `platform_support.py`
  _TR: Instagram desteği (Reels, gönderiler) eklensin_

- [ ] **[PLT-03]** Add Twitch platform handler (VODs, clips) in `platform_support.py`
  _TR: Twitch desteği (VOD'lar, klipler) eklensin_

- [ ] **[PLT-04]** Add Twitter/X platform handler in `platform_support.py`
  _TR: Twitter/X desteği eklensin_

- [ ] **[PLT-05]** Add generic "any yt-dlp supported URL" fallback with automatic detection
  _TR: yt-dlp'nin desteklediği her URL için otomatik algılama ile genel fallback eklensin_

- [ ] **[PLT-06]** Update UI to show platform badge/icon next to detected URLs
  _TR: Algılanan URL'ler için UI'da platform rozeti/ikonu gösterilsin_

### 3B — Database Migration / Veritabanı Migrasyonu
- [ ] **[DB-01]** Add `schema_version` table to SQLite database
  _TR: SQLite veritabanına `schema_version` tablosu eklensin_

- [ ] **[DB-02]** Write migration runner that applies versioned migration scripts on startup
  _TR: Uygulama başlangıcında versiyonlu migration scriptlerini uygulayan bir sistem yazılsın_

- [ ] **[DB-03]** Write migration script: v1 → v2 (config dir relocation)
  _TR: v1→v2 migration scripti yazılsın_

- [ ] **[DB-04]** Add DB backup on each migration attempt
  _TR: Her migration öncesi otomatik veritabanı yedeği alınsın_

### 3C — UI Tests / UI Testleri
- [ ] **[TST-01]** Add unit tests for all tab widget logic (without rendering)
  _TR: Tüm sekme widget mantığı için render gerektirmeyen unit testler yazılsın_

- [ ] **[TST-02]** Add tests for `FFmpegRunner` and `YtDlpRunner` wrappers (mocked subprocess)
  _TR: `FFmpegRunner` ve `YtDlpRunner` için mocked testler yazılsın_

- [ ] **[TST-03]** Add tests for CLI commands using `click.testing.CliRunner`
  _TR: CLI komutları için `CliRunner` ile testler yazılsın_

- [ ] **[TST-04]** Add integration tests for full download → convert pipeline (using small test video)
  _TR: İndirme → dönüştürme pipeline için entegrasyon testleri eklensin_

- [ ] **[TST-05]** Achieve ≥ 95% code coverage
  _TR: Kod kapsamı ≥ %95 hedeflensin_

### 3D — System Tray / Sistem Tepsisi
- [ ] **[TRY-01]** Add `pystray` to `requirements.txt` (remove comment)
  _TR: `pystray` requirements.txt'e aktif olarak eklenmeli_

- [ ] **[TRY-02]** Implement system tray icon with right-click menu (Open, Pause Queue, Quit)
  _TR: Sistem tepsisi ikonu ve sağ tık menüsü (Aç, Kuyruğu Duraklat, Çık) eklensin_

- [ ] **[TRY-03]** Show desktop notification when download/conversion completes
  _TR: İndirme/dönüştürme tamamlandığında masaüstü bildirimi gösterilsin_

- [ ] **[TRY-04]** Allow app to minimize to tray instead of closing
  _TR: Uygulama kapatılmak yerine sistem tepsisine küçültülebilsin_

---

## Phase 4 — Long-term / Uzun Vadeli

### 4A — REST API & Web UI
- [ ] **[API-01]** Create `ravn/api/server.py` using FastAPI
  _TR: FastAPI ile `ravn/api/server.py` oluşturulsun_

- [ ] **[API-02]** Implement endpoints: `POST /download`, `POST /convert`, `GET /status/{job_id}`, `GET /history`, `DELETE /job/{job_id}`
  _TR: Temel API endpoint'leri yazılsın_

- [ ] **[API-03]** Implement WebSocket endpoint `WS /progress/{job_id}` for real-time progress
  _TR: Gerçek zamanlı ilerleme için WebSocket endpoint eklensin_

- [ ] **[API-04]** Build minimal web UI (HTML + vanilla JS or React) served by FastAPI
  _TR: FastAPI tarafından sunulan minimal web arayüzü yapılsın_

- [ ] **[API-05]** Add API key authentication for local server
  _TR: Yerel sunucu için API key doğrulaması eklensin_

- [ ] **[API-06]** Add `ravn serve [--port] [--host]` CLI command to start the API server
  _TR: API sunucusunu başlatmak için `ravn serve` CLI komutu eklensin_

### 4B — Plugin Marketplace
- [ ] **[PLG-01]** Define plugin registry schema (JSON): name, version, description, download_url, author
  _TR: Plugin kayıt defteri şeması tanımlanmış (JSON) olsun_

- [ ] **[PLG-02]** Host a `registry.json` on GitHub (or bundled) with curated plugins
  _TR: GitHub'da veya paket içinde `registry.json` barındırılsın_

- [ ] **[PLG-03]** Add "Plugin Marketplace" tab in UI — browse, install, uninstall plugins
  _TR: UI'ya "Plugin Marketi" sekmesi eklensin — tarama, kurulum, kaldırma_

- [ ] **[PLG-04]** Implement plugin sandbox — plugins run in restricted environment
  _TR: Plugin sandbox'ı — pluginler kısıtlı ortamda çalışsın_

---

## Phase 5 — Build, Package & Distribution
> **TR:** Uygulamanın tüm platformlarda derlenip dağıtılması için gereken adımlar.
> **EN:** Steps required to compile and distribute the application across all platforms.

- [ ] **[BLD-01]** Update `ravn.spec` (PyInstaller) — include FFmpeg binaries for Windows build
  _TR: `ravn.spec` güncellenmeli, Windows build için FFmpeg binary'leri dahil edilmeli_

- [ ] **[BLD-02]** Bundle FFmpeg Windows binaries (ffmpeg.exe + ffprobe.exe) in `assets/ffmpeg/win64/`
  _TR: Windows için FFmpeg binary'leri `assets/ffmpeg/win64/` klasörüne konulmalı_

- [ ] **[BLD-03]** Auto-detect bundled FFmpeg in `ffmpeg_checker.py` — prefer bundled over system PATH
  _TR: `ffmpeg_checker.py` içinde önce bundled FFmpeg aransın, yoksa PATH'e bakılsın_

- [ ] **[BLD-04]** Update `build.ps1` — full Windows build pipeline (install deps → PyInstaller → NSIS installer)
  _TR: `build.ps1` güncellenmeli: bağımlılık kurulumu → PyInstaller → NSIS kurulum dosyası_

- [ ] **[BLD-05]** Create `build.sh` — Linux build pipeline (PyInstaller → AppImage or .deb)
  _TR: Linux için `build.sh` oluşturulsun: PyInstaller → AppImage veya .deb paketi_

- [ ] **[BLD-06]** Create macOS build pipeline — PyInstaller → `.app` bundle → `.dmg`
  _TR: macOS için: PyInstaller → `.app` → `.dmg` pipeline kurulsun_

- [ ] **[BLD-07]** Update GitHub Actions `tests.yml` — add Windows/Linux/macOS artifact builds on tag push
  _TR: GitHub Actions workflow'unda tag push ile otomatik build artifact'leri eklensin_

- [ ] **[BLD-08]** Create GitHub Actions `release.yml` — auto-publish release with built binaries on `v*` tag
  _TR: `v*` tag push'unda otomatik GitHub Release yayınlayan workflow oluşturulsun_

- [ ] **[BLD-09]** Test installer on clean Windows 10/11 VM — verify FFmpeg is found, app launches, config dir created
  _TR: Temiz Windows VM'de kurulumu test et — FFmpeg bulunuyor mu, uygulama başlıyor mu, config dizini oluşuyor mu_

- [ ] **[BLD-10]** Code-sign Windows executable (self-signed cert minimum, SmartScreen warning elimination)
  _TR: Windows executable'ı imzalanmalı (en az self-signed sertifika, SmartScreen uyarısı önlensin)_

---

## Phase 6 — GUI Polish & Full Controllability
> **TR:** Tüm fonksiyonların GUI üzerinden erişilebilir ve kontrol edilebilir olması.
> **EN:** Every function must be accessible and controllable via the GUI.

- [ ] **[GUI-01]** Audit all core features — ensure every function has a corresponding UI control
  _TR: Tüm çekirdek özellikler denetlensin, her fonksiyonun bir UI kontrolü olsun_

- [ ] **[GUI-02]** Add real-time FFmpeg progress bar using `-progress pipe:1` output parsing
  _TR: FFmpeg `-progress pipe:1` çıktısı parse edilerek gerçek zamanlı ilerleme çubuğu eklensin_

- [ ] **[GUI-03]** Add download queue panel — show all queued, active, and completed jobs
  _TR: Kuyrukta bekleyen, aktif ve tamamlanan tüm işleri gösteren bir panel eklensin_

- [ ] **[GUI-04]** Add per-job cancel button in queue panel
  _TR: Kuyruk panelinde her iş için iptal butonu eklensin_

- [ ] **[GUI-05]** Add batch download — accept multiple URLs (one per line) in download tab
  _TR: İndirme sekmesinde toplu URL girişi (her satıra bir URL) desteği eklensin_

- [ ] **[GUI-06]** Add batch convert — select multiple files and convert them all with one settings profile
  _TR: Toplu dönüştürme — birden fazla dosya seçip tek ayar profiliyle dönüştürme eklensin_

- [ ] **[GUI-07]** Add settings panel for all FFmpeg advanced options (CRF, preset, audio bitrate, etc.)
  _TR: Tüm FFmpeg gelişmiş seçenekleri (CRF, preset, ses bitrate vb.) için ayar paneli eklensin_

- [ ] **[GUI-08]** Add output directory selector with "remember last used" persistence
  _TR: Çıktı dizini seçici eklensin, son kullanılan dizin hatırlanmalı_

- [ ] **[GUI-09]** Add keyboard shortcuts (Ctrl+D = download, Ctrl+O = open file, Ctrl+Q = quit, etc.)
  _TR: Klavye kısayolları eklensin_

- [ ] **[GUI-10]** Add "Open output folder" button after every successful operation
  _TR: Her başarılı işlem sonrası "Çıktı klasörünü aç" butonu gösterilsin_

---

## Notes / Notlar

- All file paths must use `pathlib.Path` — no hardcoded string separators
  _TR: Tüm dosya yollarında `pathlib.Path` kullanılmalı, hardcoded ayraç olmamalı_

- All user-facing strings must support TR/EN toggle (i18n-ready structure)
  _TR: Kullanıcıya gösterilen tüm yazılar TR/EN geçişini destekler yapıda olmalı_

- Minimum Python version: 3.9 (f-strings, type hints, pathlib all standard)
  _TR: Minimum Python sürümü 3.9 olarak belirlenmeli_

- FFmpeg minimum version: 5.0
  _TR: FFmpeg minimum sürüm 5.0_

- yt-dlp must always be the latest release (no version pin)
  _TR: yt-dlp her zaman en son sürümde olmalı, versiyon sabitlenmemeli_
