# RAVN Roadmap

This file tracks the **public-facing roadmap** for RAVN. It is intentionally shorter and cleaner than an internal sprint board.

## Current release focus

RAVN already covers its core product loop. The near-term goal is to make the public release feel as polished as the feature set itself.

##







### Önem Derecesi 1: Sürüm Öncesi Kritik Kararlılık ve Paket Doğrulama

sorun; Upstream bağımlılık olan `yt-dlp` kütüphanesinin hedef platform kaynaklı sık değişmesi indirme işlevini bozmaktadır ve paketli desktop çalışma zamanında dinamik güncelleme mekanizması yoktur.
çözüm/agent talimatı; Paket içerisindeki gömülü `yt-dlp` binary'sinin sürümünü runtime esnasında kontrol edecek ve gerektiğinde arka planda dinamik self-update tetikleyecek bir kontrol katmanı entegre et.

sorun; PyInstaller paketleme sürecinde (`ravn.spec` ve `build.ps1`), derleme yapılan makine dışındaki temiz/izole Windows ortamlarında bulunmayabilecek C++ Runtime bağımlılıkları (`vcruntime140.dll` vb.) pakete dahil edilmemiştir.
çözüm/agent talimatı; `ravn.spec` dosyasına evrensel CRT (C Runtime) ve Visual C++ bağımlılıklarını açıkça toplayacak adımları ekle; paket içeriğinin bağımsız OS kütüphanelerini barındırmasını sağla.

sorun; `tools/windows_package_smoke.ps1` betiğinin temiz ve harici araçlardan arındırılmış izole bir işletim sistemi ortamında otomatik olarak test edilmesini sağlayan bir mekanizma yoktur.
çözüm/agent talimatı; Bir Windows Sandbox (`.wsb`) konfigürasyon dosyası tanımla; paketlenen `ravn.exe` dosyasını, global sistemde hiçbir FFmpeg veya aria2 bağımlılığı yokken bu izole sanal imajda çalıştırıp lookup doğruluğunu test eden bir otomasyon akışı kur.

---

### Önem Derecesi 2: Dağıtım Güvenliği ve Karakter Seti Güvenilirliği

sorun; GitHub Actions release akışında binary imzalama adımı bulunmadığı için paketlenen Windows sürümü dağıtımda SmartScreen engeline takılmaktadır.
çözüm/agent talimatı; `windows-release.yml` iş akışına `SignTool` imzalama adımını ekle; sürüm çıktıları (artifacts) üretildiği anda SHA-256 sağlama toplamı (checksum) dosyalarını otomatik oluşturup release sayfasına yazdır.

sorun; Çift dilli yapı (`en.json`, `tr.json`) altındaki CLI ve UI girdilerinde Türkçe karakterler içeren dosya yolları veya şablonlar kullanıldığında indirme ve dönüştürme (subprocess) süreçlerinde kodlama (encoding) çökme riski mevcuttur.
çözüm/agent talimatı; Girdi yakalama noktalarına ve alt süreç (subprocess) I/O yönetimlerine katı UTF-8 zorunluluğu ve yerel OS encoding korumaları ekle.

---

### Önem Derecesi 3: Onboarding Dokümantasyonu ve Sınır Optimizasyonu

sorun; İlk kurulum aşamasında kullanıcının karşılaşacağı SmartScreen uyarılarının nasıl geçileceği, gömülü FFmpeg arama hiyerarşisi ve isteğe bağlı `aria2c` bağımlılığının kapsam sınırları dokümantasyonda eksiktir.
çözüm/agent talimatı; `DEPENDENCIES.md` ve `README.md` dosyalarını güncelleyerek SmartScreen bypass yönergelerini, `aria2c` aracının sadece torrent/magnet için gerekli olduğunu ve FFmpeg'in öncelikli lookup dizin mantığını dökümante et.

sorun; `YouTubeDownloader.download()` fonksiyonunun barındırdığı 27 adet parametre kodun sürdürülebilirliğini zorlaştırmaktadır.
çözüm/agent talimatı; Sınıf yapısını bozmadan veya radikal refactor yapmadan, bu parametre yığınını sarmalayan tek bir `DownloadRequest` dataclass yapısı oluştur ve API imzasını bu nesne üzerinden standardize et.


### Dİğer



sorun; Medya indirme ve işleme sonrasında ses dosyalarına etiket/metadata yazmak için projenin kullandığı `mutagen` kütüphanesi `requirements.txt` üzerinde tanımlanmamıştır. Temiz kurulumlarda çalışma zamanı hatası (ModuleNotFoundError) riski vardır.
çözüm/agent talimatı; `requirements.txt` dosyasına `mutagen>=1.45.0` bağımlılığını ekle.

sorun; `ravn.spec` dosyasındaki `EXE` bloğunda Windows sürüm kaynak dosyası (`version`) belirtilmemiştir. Dağıtılan `.exe` dosyasına sağ tıklandığında Dosya Sürümü, Ürün Adı ve Telif Hakkı gibi Windows Gezgini meta bilgileri boş kalmaktadır, bu durum sürüm güvenilirliğini zedeler.
çözüm/agent talimatı; PyInstaller uyumlu bir `version_info.txt` dosyası oluştur; Şirket, Versiyon ve Ürün detaylarını buraya işle ve `ravn.spec` içindeki `EXE` çağrısına `version='version_info.txt'` parametresi olarak bağla.

sorun; `ravn.spec` dosyasında `excludes` parametresi boş bırakılmıştır. `pytest` gibi sadece test ortamında gereken kütüphaneler ile kullanılmayan standart Python modülleri klasör modundaki (`COLLECT`) son dağıtım boyutunu gereksiz büyütmektedir.
çözüm/agent talimatı; `ravn.spec` içerisindeki `excludes` listesine `['pytest', 'unittest', 'pdb', 'distutils']` modüllerini ekleyerek paket boyutunu optimize et.

~~sorun; Torrent ve magnet iş akışları için `aria2p` kütüphanesinin alt modülleri `ravn.spec` `hiddenimports` listesinde değil.~~
**GEÇERSİZ (v1.4.0'da düzeltildi).** Bu madde yanlış bir varsayıma dayanıyordu: `aria2p`
bir bağımlılık **değildir** ve `requirements.txt` içinde yer almaz — torrent desteği
`aria2c` ikilisini `subprocess` ile çalıştırır (bkz. `ravn_app/core/runners/aria2.py` ve
`requirements.in` içindeki açıklama). `ravn.spec` içinde bulunan
`*collect_submodules("aria2p")` satırı, kurulu olmayan bir paketi import etmeye çalıştığı
için temiz bir ortamdaki her build'i riske atıyordu; **kaldırıldı**. Tekrar eklemeyin.

sorun; Uygulama başlangıçta veritabanı migrasyonu ve `tool_health` kontrolü gibi senkron G/Ç (I/O) işlemleri yapmaktadır. `console=False` modu aktif olduğundan, zayıf sistemlerde ana pencere yüklenene kadar uygulama kilitlenmiş veya açılmıyor algısı oluşmaktadır.
çözüm/agent talimatı; `ravn.spec` mimarisine PyInstaller `Splash` bileşenini dahil et; `ravn.py` giriş noktasında ana arayüz yüklenene kadar ekranda geçici bir yükleme görseli (splash screen) gösterilmesini sağla.

---

### Cross-platform: sıradaki adımlar

RAVN artık Linux ve macOS'ta CI test matrisiyle (`tests.yml`) doğrulanıyor ve `yt-dlp`
self-update / medya oynatıcı açma gibi gerçek platform hataları giderildi (bkz.
ARCHITECTURE.md §3.6).

**v1.4.0'da tamamlananlar:**

- ✅ Linux paketleme workflow'u eklendi (`.github/workflows/linux-package.yml`): PyInstaller
  onedir + `tar.gz` + SHA-256, `workflow_dispatch` ile tetiklenir. Bilinçli olarak tagged
  release'e **bağlı değildir** — gerçek bir runner'da yeşil çalıştığı görülmeden bağlanmayacak.
  Doğrulama sadece "derlendi" değil: headless CLI smoke testi + `xvfb` altında GUI başlatma
  kontrolü içeriyor (test suite hiçbir zaman gerçek bir `Tk()` kökü oluşturmadığı için
  GUI'nin Linux'ta açılabildiği başka hiçbir yerde kanıtlanmıyor).
- ✅ `tool_installer.py` artık `apt`/`dnf`/`pacman` tespiti yapıyor. **Karar:** otomatik
  kurulum yerine çalıştırılacak komut gösteriliyor — GUI uygulamasının `sudo` parolası
  soracak bir TTY'si yoktur, `sudo`'ya shell out etmek uygulamayı kilitlerdi.
- ✅ Harici araçlar (ffmpeg/ffprobe, yt-dlp, aria2c) artık pakete gömülüyor ve uygulama
  kendi dizininden otomatik buluyor (`ravn_app/utils/bundled_tools.py`). Ayarlardaki
  "eksikleri yükle" artık **B planı**; A planı, aracın zaten zip içinde gelmesi.

**Kalan takip işleri:**

sorun; macOS için paketlenmiş, indirilebilir bir dağıtım (`.app`/`.dmg`) yoktur.
çözüm/agent talimatı; Linux workflow'unu (`linux-package.yml`) şablon alarak `workflow_dispatch` ile tetiklenen bir macOS paketleme workflow'u ekle; `ravn.spec` içindeki koşulsuz `Splash()` çağrısının macOS'ta desteklenmediği durumları kontrol et; gerçek bir runner'da doğrulanmadan tagged release'e bağlama.

sorun; `tool_installer.py` macOS'ta (`brew`) kurulum komutu üretmez — `TOOL_ASSET_SUBDIRS` ve Linux backend'i hazır, sadece brew eşlemesi eksik (kodda `TODO(macos-followup)` işaretli).
çözüm/agent talimatı; `BREW_PACKAGE_IDS` ekleyip `_LINUX_PACKAGE_MANAGERS` ile aynı desende bir brew backend'i yaz; `detect_linux_package_manager()`'ı platformdan bağımsız bir `detect_package_manager()`'a genelleştir.

sorun; Linux paketi `ffmpeg`/`aria2c` ikililerini gömmez (yalnızca `yt-dlp` gömülür); kullanıcı bunları dağıtım paket yöneticisinden kurmak zorundadır.
çözüm/agent talimatı; statik bir Linux ffmpeg build'i gömmenin GPL yükümlülükleri ve ikinci bir binary-provenance hattı bakımı anlamına geldiğini göz önünde tut; yalnızca kullanıcı geri bildirimi bunun gerçek bir benimseme engeli olduğunu gösterirse ele al.

sorun; Linux onedir build'i `ubuntu-latest`'in glibc sürümüne bağlıdır; daha eski dağıtımlarda çalışmayabilir.
çözüm/agent talimatı; şimdilik release notlarında minimum desteklenen dağıtımı belgele; manylinux tarzı bir konteyner ile çözmek bu turun kapsamı dışında.

---
---

# 🔴 TAURI FRONTEND MİGRASYON — TAM GÖREV LİSTESİ

> **Kaynak:** `ravn_app/ui/` altındaki 1444+ satırlık CustomTkinter masaüstü uygulaması.
> **Hedef:** `frontend/src/` altındaki Vue 3 + Tauri desktop uygulaması.
> **Mevcut Durum:** Portun ~%13'ü tamamlandı. Geri kalan %87 stub, placeholder veya tamamen eksik.
> **Denetim Tarihi:** 2026-08-05

---

## ⛔ MUTLAKİ KURALLAR — BU KURALLARI İHLAL EDEN HER COMMIT REDDEDİLİR

### KURAL-1: RENK PALETİ KANUNU
Tüm Vue bileşenlerinde **YALNIZCA** `style.css` içindeki CSS değişkenleri (`var(--bg-primary)`, `var(--accent-brass)`, vb.) kullanılacak.
**YASAK:** Tailwind renk sınıfları (`bg-slate-900`, `text-purple-400`, `bg-rose-600`, `bg-cyan-600`, `bg-teal-600`, `bg-indigo-600` vb.) ile sabit HEX kodu (`#334155`, `#7c3aed` vb.) kullanmak.
**İSTİSNA YOK.** Her bileşen Nordic Brass temasına uyacak. Hatırla: CustomTkinter'daki palette eşdeğer CSS token'lar zaten `style.css`'te tanımlı:
- `--bg-primary: #141414` ← `BG_PRIMARY #1E1B1B`'ye en yakın dark variant
- `--bg-surface: #1E1E1E` ← `BG_SURFACE #262222`
- `--bg-card: #252525` ← `BG_CARD #2D2828`
- `--bg-hover: #2A2A2A` ← `BG_HOVER #363030`
- `--bg-input: #2D2D2D` ← `BG_INPUT #181515`
- `--accent-brass: #C99A5B` ← `ACCENT #C99A5B` (BİREBİR AYNI)
- `--text-primary: #E8E0D8` ← `TEXT_PRIMARY #EAE4E1`
- `--text-secondary: #B8A99A` ← `TEXT_SECONDARY #B5ADA7`
- `--text-muted: #A09080` ← `TEXT_MUTED #8A8078`
- `--border-subtle: #3A3330` ← `BORDER #3D3535`
- `--status-success: #22c55e` ← `SUCCESS #5B8A67`
- `--status-error: #ef4444` ← `ERROR #A84B4B`
- `--status-warning: #f59e0b` ← `WARNING #C98A5B`

### KURAL-2: STUB/ALERT YASAĞI
Hiçbir buton `alert()`, `console.log()`, `setTimeout` mock veya "Coming soon" placeholder KULLANMAYACAK.
Her buton ya gerçek backend API çağrısı yapacak, ya da çağrılacak endpoint yoksa **butonu devre dışı bırakıp `title="API bağlantısı bekleniyor"` tooltip gösterecek**.
Asla kullanıcıya boş `alert()` gösterme. Bu rezalet bir UX.

### KURAL-3: BACKEND API EŞLEŞMESİ
Her Vue bileşeni için kullanılacak API endpoint'leri `frontend/src/services/apiClient.ts` içinde tanımlanacak.
Endpoint yoksa **önce backend'e endpoint ekle**, sonra frontend'i bağla.
Backend endpoint'leri: `ravn_app/api/routers/` altındaki modüller.

### KURAL-4: BİR İŞ BİTMEDEN DİĞERİNE GEÇME
Her Phase kendi içinde sıralı çalışılacak. Bir subtask tamamlanmadan sonrakine geçme.
Her subtask bitiminde **o bileşeni tarayıcıda kontrol et** (`npm run dev`).
Kırık UI = o subtask tamamlanmamıştır.

### KURAL-5: UNICODE İKON SETİ
CustomTkinter'daki `Icons` sınıfındaki Unicode ikonlar bire bir kullanılacak:
`⌂` Home, `❖` Studio/Logo, `↓` Download, `⇄` Convert, `≡` Subtitle/Playlist, `◷` History, `⚙` Settings, `☰` Queue, `⊕` Torrent, `∿` Mixer, `◫` Filters, `▦` Library, `🔍` Search, `📁` Browse, `✕` Close, `↻` Retry, `▶` Play, `⏹` Stop, `⟳` Spinner, `✓` Success, `⚠` Warning, `ℹ` Info, `◐` Theme Toggle.

### KURAL-6: i18n HAZIRLIĞI
Tüm kullanıcıya görünen stringler (buton text, label, placeholder, tooltip, hata mesajı) şimdilik sabit string olabilir AMA ileride i18n'e çevrilebilir yapıda olacak: bileşen içinde `const t = { ... }` objesi olarak tutulacak.

### KURAL-7: GIT İŞLEMLERİ
**`git commit`, `git push`, `git tag` YAPMA.** Kullanıcı açıkça "commit at" veya "gönder" demedikçe bu komutları çalıştırma. İhlal = güven kaybı.

### KURAL-8: CUSTOMTKINTER REFERANSI
Her bileşeni kodlarken **orijinal Python dosyasını MUTLAKA oku**. Ezberden yazma. Dosya yolları:
- Shell: `ravn_app/ui/main_window.py`
- Home: `ravn_app/ui/tabs/home_workspace.py`
- Download: `ravn_app/ui/tabs/download_tab.py`
- Torrent: `ravn_app/ui/tabs/torrent_tab.py`
- Converter: `ravn_app/ui/tabs/converter_tab.py`
- Subtitle: `ravn_app/ui/tabs/subtitle_tab.py`
- Filters: `ravn_app/ui/tabs/filters_tab.py`
- Mixer: `ravn_app/ui/tabs/mixer_tab.py`
- Utilities: `ravn_app/ui/tabs/utilities_tab.py`
- Library: `ravn_app/ui/tabs/library_tab.py`
- History: `ravn_app/ui/tabs/history_tab.py`
- Settings: `ravn_app/ui/tabs/settings_tab.py`
- Queue: `ravn_app/ui/queue_panel.py`
- Design Tokens: `ravn_app/ui/design_tokens.py`
- Components: `ravn_app/ui/components/`
- UI Widgets: `ravn_app/ui/ui_components.py`

---

## PHASE 0 — TEMİZLİK VE ALTYAPI (Öncelik: İLK)

> Her şeyden önce mevcut kodu düzelt. Yanlış renk kullanan 6 bileşeni Nordic Brass'e çevir.
> Eksik CSS token'ları `style.css`'e ekle. Tailwind yapılandırmasını kontrol et.

### P0-T1: style.css Token Genişletmesi
Eksik olan CustomTkinter renkleri CSS token olarak ekle:
- [x] `--success-bg: #1B291F` (CustomTkinter SUCCESS_BG)
- [x] `--warning-bg: #2B2018` (CustomTkinter WARNING_BG)
- [x] `--error-bg: #281A1A` (CustomTkinter ERROR_BG)
- [x] `--info-bg: #262222` (CustomTkinter INFO_BG)
- [x] `--accent-hover: #D4A86A` (CustomTkinter ACCENT_HOVER)
- [x] `--accent-beige: #D4C5B9` (CustomTkinter ACCENT_BEIGE)
- [x] `--success-hover: #6B9A77`
- [x] `--error-hover: #B85B5B`
- [x] `--status-queued: #8A8078`
- [x] `--status-running: #C99A5B`
- [x] `--status-done: #5B8A67`
- [x] `--status-cancelled: #C98A5B`
- [x] `--status-paused: #8A8078`
- [x] Light tema token'ları (`:root[data-theme="light"]` altında): `--bg-primary: #F5F2F0`, `--bg-surface: #EFEAE6`, `--bg-card: #E8E2DD`, `--bg-hover: #DDD6D0`, `--bg-input: #FFFFFF`, `--text-primary: #2A2421`, `--text-secondary: #665C54`, `--text-muted: #948A82`, `--border-subtle: #D4CBC4`, `--border-strong: #BDB2A9`

**Doğrulama:** `style.css`'te `slate`, `purple`, `rose`, `cyan`, `teal`, `indigo`, `amber` kelimelerinden HİÇBİRİ bulunmamalı. (TAMAMLANDI)

### P0-T2: ConverterTab.vue — Nordic Brass'e Çevir
- [x] Tüm Tailwind `slate-*`, `purple-*` sınıflarını CSS değişkenlerine dönüştür.
- [x] Arka plan: `var(--bg-surface)`, kart: `var(--bg-card)`, girdi: `var(--bg-input)`, vurgu: `var(--accent-brass)`.

### P0-T3: SubtitleTab.vue — Nordic Brass'e Çevir
- [x] Tüm `slate-*`, `amber-*` sınıflarını CSS değişkenlerine dönüştür.

### P0-T4: FiltersTab.vue — Nordic Brass'e Çevir
- [x] Tüm `slate-*`, `rose-*` sınıflarını CSS değişkenlerine dönüştür.

### P0-T5: MixerTab.vue — Nordic Brass'e Çevir
- [x] Tüm `slate-*`, `cyan-*` sınıflarını CSS değişkenlerine dönüştür.

### P0-T6: UtilitiesTab.vue — Nordic Brass'e Çevir
- [x] Tüm `slate-*`, `teal-*` sınıflarını CSS değişkenlerine dönüştür.

### P0-T7: QueuePanel.vue — Nordic Brass'e Çevir
- [x] Tüm `slate-*`, `blue-*`, `indigo-*` sınıflarını CSS değişkenlerine dönüştür.

### P0-T8: Dashboard.vue Temizliği
- [x] `Dashboard.vue` dosyasını sil veya `legacy/` klasörüne taşı. Router'da kullanılmıyor, kafa karıştırıyor.

**P0 Doğrulama Kapısı:** `grep -r "bg-slate\|bg-purple\|bg-rose\|bg-cyan\|bg-teal\|bg-indigo\|bg-amber" frontend/src/components/` → **0 sonuç** olmalı. (DOĞRULANDI - 0 sonuç)

---

## PHASE 1 — UYGULAMA KABUĞU (App Shell) TAM EŞLEŞMESİ

> Kaynak: `ravn_app/ui/main_window.py` (1444 satır). MUTLAKA oku.

### P1-T1: Üst Gezinme Çubuğu Yeniden Yapılandırması
Mevcut sidebar navigasyonu korunabilir AMA üst çubuğa şu kontroller eklenecek:
- [x] Marka Başlığı: `❖ RAVN Media Suite` — brass accent renkte, sol üst.
- [x] Tema Toggle Butonu: `◐` ikonu, tıklandığında `document.documentElement.dataset.theme` değiştirir (`dark`↔`light`).
- [x] Dil Toggle Butonu: `TR` / `EN` — tıklandığında dil değiştirir.
- [x] Komut Paleti Butonu: `🔍 Ctrl+K` — açıklama: P1-T4'te implement edilecek.

### P1-T2: Hızlı Eylem Çubuğu (Quick Action Bar)
Header alanına 4 hızlı erişim butonu:
- [x] `↓ Paste URL` — clipboard'dan URL'yi Download tab'ına yapıştırır.
- [x] `⊕ Add Torrent` — Download workspace torrent moduna geçer.
- [x] `⇄ Convert File` — Studio → Converter sekmesine gider.
- [x] `▦ Open Library` — Library workspace'e gider.

### P1-T3: Kuyruk Paneli Yeniden Konumlandırma
- [x] Alt çekmece yerine **sağdan açılan 380px panel (drawer)** yap — CustomTkinter'daki gibi.
- [x] Panel başlığı: `☰ Task Queue` + Stats: `Active: A • Queued: Q • Completed: C`.
- [x] Sidebar'daki Queue butonunda aktif görev sayısı rozeti (badge).
- [x] Boş durum widget'ı: `📂 Kuyruk boş` illüstrasyonu.
- [x] `Clear Completed` butonu.

### P1-T4: Komut Paleti (Command Palette)
Yeni bileşen: `frontend/src/components/CommandPalette.vue`
- [x] `Ctrl+K` kısayolu ile modal açılır.
- [x] Arama girişi — canlı fuzzy filtreleme.
- [x] Komut listesi: her komutta başlık, alt başlık, kategori rozeti (home, download, convert, library, settings, queue).
- [x] `Up`/`Down` ok tuşları ile gezinme, `Enter` ile çalıştırma, `Escape` ile kapama.
- [x] Kaynak: `ravn_app/ui/components/command_palette.py` — MUTLAKA OKU.

### P1-T5: Global Klavye Kısayolları
`App.vue` içinde `onMounted` ile window keydown dinleyicisi:
- [x] `Ctrl+Enter` → Aktif workspace'e göre varsayılan eylem (Download/Convert/Search).
- [x] `Escape` → Aktif modal/panel kapatma.
- [x] `Ctrl+L` → Girdi alanlarını temizleme.
- [x] `Ctrl+K` → Komut Paleti açma.
- [x] `Ctrl+,` veya `Ctrl+P` → Settings'e gitme.

### P1-T6: Toast Bildirim Sistemi
Yeni bileşen: `frontend/src/components/ToastManager.vue`
- [x] Sağ üstten kayan bildirim kutuları.
- [x] Türler: `success` (3s), `warning` (4s), `error` (5s), `info` (3s).
- [x] Otomatik kapanma + elle kapatma (✕).
- [x] Pinia store veya provide/inject ile global erişim.

### P1-T7: ErrorPanel Bileşeni
Yeni bileşen: `frontend/src/components/ErrorPanel.vue`
- [x] Kırmızı uyarı paneli. Kullanıcıya temiz hata mesajı gösterir.
- [x] "Technical Details" toggle → mono font raw traceback kutusu.
- [x] Retry butonu.
- [x] Kaynak: `ravn_app/ui/components/error_panel.py` — OKU.

**P1 Doğrulama Kapısı:**
- [x] Tema toggle çalışıyor (dark↔light CSS değişiyor).
- [x] `Ctrl+K` ile Command Palette açılıyor.
- [x] Queue paneli sağdan 380px olarak kayıyor.
- [x] Toast bildirimleri gösteriliyor (test: `toast.success("Test")` çağrısı).

---

## PHASE 2 — HOME WORKSPACE TAM EŞLEŞMESİ

> Kaynak: `ravn_app/ui/tabs/home_workspace.py` — MUTLAKA OKU.

### P2-T1: Araç Sağlık Bannerı
- [x] Backend'den `GET /api/v1/health` çağır.
- [x] Eksik araçlar varsa (ffmpeg, yt-dlp, aria2c) sarı/kırmızı uyarı bannerı göster.
- [x] Devre dışı kalan özellikler listesi.
- [x] "Fix in Settings" butonu → Settings'e yönlendir.
- [x] Tüm araçlar hazırsa banner gizli.

### P2-T2: 6 Hızlı Eylem Kartı
Mevcut 2 link kartı yerine **6 tıklanabilir kart**:
- [x] `↓ Paste URL & Download` → Download workspace, URL odaklı.
- [x] `≡ Playlist Downloader` → Download workspace, playlist modu.
- [x] `⊕ Torrent / Magnet` → Download workspace, torrent modu.
- [x] `⇄ Convert Format` → Studio → Converter.
- [x] `◫ Apply Filters` → Studio → Filters.
- [x] `▦ Media Library` → Library workspace.
Her kart: ikon, başlık, alt açıklama, hover efekti, tıklama ile yönlendirme.

### P2-T3: 4 İstatistik Kartı
Backend API'den çekilecek veriler:
- [x] Total Downloads sayısı.
- [x] Total Conversions sayısı.
- [x] Total Operations sayısı.
- [x] Queue Tasks sayısı (Pinia store'dan).

### P2-T4: Son Aktivite Paneli
- [x] Son 6 işlemi listele (başlık, zaman damgası, durum rozeti: completed/failed/running).
- [x] "Open Queue" butonu — Queue panelini açar.

**P2 Doğrulama Kapısı:**
- [x] Eksik araç simüle edildiğinde uyarı bannerı görünüyor.
- [x] 6 kart tıklanabilir ve doğru yere yönlendiriyor.
- [x] İstatistikler gerçek backend verisinden geliyor (fake data değil).

---

## PHASE 3 — DOWNLOAD WORKSPACE TAM EŞLEŞMESİ

> Kaynak: `ravn_app/ui/tabs/download_tab.py`, `torrent_tab.py`, `download_workspace.py` — HEPSİNİ OKU.

### P3-T1: Kaynak Sınıflandırma Kartı
- [x] URL/Magnet/Torrent otomatik algılama (regex).
- [x] Dinamik rozet gösterimi: "Media URL", "Playlist", "Batch URLs", "Torrent / Magnet".
- [x] `.torrent` dosya tarayıcı butonu (Tauri `dialog.open`).

### P3-T2: Medya Çıktı Seçici
- [x] `Video` / `Audio` segmented button — tıklandığında alt form alanlarını değiştirir.
- [x] Video seçildiğinde: Video Quality + Video Format göster.
- [x] Audio seçildiğinde: Audio Format + Bitrate göster.

### P3-T3: Platform Seçici & Profil Presetleri
- [x] Platform Dropdown: YouTube, Twitter/X, Instagram, TikTok, Vimeo, Twitch, SoundCloud, Facebook, Rumble, Direct.
- [x] Seçilen platform rozeti (ikon + renk).
- [x] Profil Dropdown: Custom, Music (MP3 320k), Podcast (AAC 192k), Archive (Lossless FLAC), Social Clip (MP4 1080p).
- [x] Profil seçildiğinde format/kalite/bitrate otomatik doldurulur.

### P3-T4: URL Doğrulama & Boyut Tahmini
- [x] Canlı URL doğrulama ikonu: `✓` (geçerli), `⚠` (geçersiz).
- [x] Metadata çekildikten sonra `~MB` boyut tahmini etiketi.

### P3-T5: Sürükle & Bırak (DND) Desteği
- [x] Tüm dosya girişlerine `@dragover`, `@drop` event handler ekle.
- [x] Drop zone görsel efekti (border glow, ikon değişimi).

### P3-T6: İki Sütunlu Video/Audio Düzeni
CustomTkinter'daki gibi:
- [x] **Video Sütunu**: Quality Combobox (Best/1080p/720p/480p/360p), Format (MP4/WebM/MKV), Fetch Data butonu, Playlist paneli, Download Video butonu, Progress bar.
- [x] **Audio Sütunu**: Format (MP3/AAC/FLAC/OPUS/WAV/M4A), Bitrate (Best 320k/320k/192k/128k/VBR 0), Fetch Data butonu, Playlist paneli, Download Audio butonu, Progress bar.

### P3-T7: Playlist Paneli & PlaylistSortDialog
Yeni bileşen: `frontend/src/components/PlaylistSortDialog.vue`
- [x] Select All / Clear Selection checkbox.
- [x] Approve & Sort butonu → modal dialog açar.
- [x] Modal (980x660): Başlık filtresi, Min/Max süre, Popülerlik filtresi, Aralık seçici.
- [x] 7 sütunlu tablo: Kapak, Seç, Başlık, Boyut, Süre, Albüm, Kanal.
- [x] Sütun başlığına tıklayarak sıralama.
- [x] Download Selected butonu.
- [x] Kaynak: `ravn_app/ui/components/playlist_sort_dialog.py` — OKU.

### P3-T8: İndirme İlerleme Sistemi
- [x] WebSocket üzerinden gerçek zamanlı yüzde, hız (MB/s), ETA gösterimi.
- [x] İlerleme çubuğu (brass accent renk).
- [x] Durum etiketi (indiriliyor, işleniyor, tamamlandı, hata).

### P3-T9: Torrent Tab — Tam İmplementasyon
- [x] aria2c uyarı bannerı (yoksa sarı/kırmızı banner).
- [x] Magnet URI / Torrent URL / Dosya Yolu girişi.
- [x] Browse `.torrent` butonu (Tauri `dialog.open`).
- [x] Mode selector: Full / Sequential / Stream — CustomTkinter ile birebir.
- [x] Output dizin seçici (Tauri `dialog.open`).
- [x] Download Torrent / Cancel Download / Open in Player butonları.
- [x] 8 sütunlu indirme tablosu (Name, Mode, Status, Progress, Downloaded, Remaining, Speed, ETA).
- [x] İlerleme çubuğu ve metrikleri.
- [x] Backend: `POST /api/v1/downloads/torrent/start`, `POST /api/v1/downloads/torrent/cancel`.

### P3-T10: Batch İndirme — Tam İmplementasyon
- [x] Çok satırlı URL textbox.
- [x] Toplu indirme butonu — tüm URL'leri sıraya alır.
- [x] İlerleme: her URL için ayrı durum satırı.

### P3-T11: ErrorPanel Entegrasyonu
- [x] Download tab'ın altına ErrorPanel bileşeni yerleştir.
- [x] İndirme hatalarında otomatik göster.

**P3 Doğrulama Kapısı:**
- [x] Platform seçici çalışıyor, profil seçince format/kalite otomatik değişiyor.
- [x] Playlist fetch edildiğinde PlaylistSortDialog açılıyor.
- [x] Torrent indirme aria2c ile gerçek backend üzerinden çalışıyor.
- [x] İlerleme çubuğu WebSocket'ten gerçek veri alıyor.

---

## PHASE 4 — STUDIO WORKSPACE TAM EŞLEŞMESİ

> Bu phase'in her subtask'ı için **ilgili CustomTkinter Python dosyasını baştan sona oku**. Ezberden YAZMA.

### P4-T1: Studio Launcher Grid (Opsiyonel Geliştirme)
Mevcut tab navigasyonu zaten var. Ek olarak:
- [x] Studio ilk açıldığında 5 kartlık ızgara görünsün (CustomTkinter'daki gibi).
- [x] Kart tıklanınca ilgili tab'a geçiş.
- [x] Geri butonu: `‹ Back to Launcher`.

### P4-T2: ConverterTab.vue — Tam Yeniden Yazım
Kaynak: `ravn_app/ui/tabs/converter_tab.py` — SATIR SATIR OKU.
- [x] Input File: DND zone + Browse butonu (Tauri `dialog.open`).
- [x] Video Codec Dropdown: `h264`, `hevc (H.265)`, `vp9`, `av1`, `copy`.
- [x] Audio Codec Dropdown: `aac`, `mp3`, `opus`, `flac`, `copy`.
- [x] Quality Dropdown: `Kayıpsız (Lossless)`, `Çok Yüksek (CRF 18)`, `Yüksek (CRF 21)`, `Orta (CRF 23)`, `Düşük (CRF 28)`, `Çok Düşük (CRF 32)`.
- [x] Speed Preset: `ultrafast`, `superfast`, `veryfast`, `faster`, `fast`, `medium`, `slow`, `slower`, `veryslow`.
- [x] Hardware Acceleration: `Yok (Software)`, `NVENC (NVIDIA)`, `Quick Sync (Intel QSV)`, `AMF (AMD)`.
- [x] Audio Bitrate: `320k`, `256k`, `192k`, `128k`, `96k`.
- [x] Output File: path girişi + Browse butonu.
- [x] Convert / Stop / Clear butonları.
- [x] Progress bar + Status label.
- [x] Scrollable log textbox.
- [x] ErrorPanel entegrasyonu.
- [x] Backend API: `POST /api/v1/convert/start` — endpoint yoksa BACKEND'E EKLE.
- [x] **Mock path (`C:/Downloads/sample_video.mkv`) SİL.** Gerçek dosya seçici kullan.

### P4-T3: SubtitleTab.vue — Tam Yeniden Yazım
Kaynak: `ravn_app/ui/tabs/subtitle_tab.py` — OKU.
- [x] **Sol Panel (Altyazı İndirme)**:
  - Video URL girişi.
  - Dil checkboxları: Turkish (tr), English (en), German (de), French (fr), Spanish (es).
  - Auto-generated subtitles checkbox.
  - Output klasör seçici (Tauri `dialog.open`).
  - Download Subtitles butonu.
- [x] **Sağ Panel (Altyazı İşleme)**:
  - Video dosya seçici (DND + Browse).
  - Subtitle dosya seçici (DND + Browse).
  - Format dönüştürücü: Output format dropdown (SRT, VTT, ASS, SSA) + Convert Format butonu.
  - Zamanlama ayarlayıcı: Shift slider (-10.0s → +10.0s) + sayısal giriş + Adjust Timing butonu.
  - Soft Subtitle (mux) butonu + Hard Subtitle (burn-in) butonu.
- [x] Çalıştırma logu textbox.
- [x] ErrorPanel.
- [x] Backend: `POST /api/v1/subtitle/download`, `POST /api/v1/subtitle/process`.
- [x] **`alert()` ÇAĞRISINI SİL.**

### P4-T4: FiltersTab.vue — Tam Yeniden Yazım
Kaynak: `ravn_app/ui/tabs/filters_tab.py` — OKU.
- [x] Input dosya seçici (DND + Browse).
- [x] Output dosya seçici (Browse).
- [x] **Sayısal Ayar Kontrolleri** (slider + sayı girişi):
  - Brightness: `-1.0` → `1.0` (mevcut).
  - Contrast: `0.0` → `3.0` (mevcut, üst sınır düzelt).
  - Saturation: `0.0` → `3.0` (mevcut).
  - Blur: `0.0` → `10.0` (EKLE).
  - Sharpen: `0.0` → `5.0` (EKLE).
  - Rotate: `0`, `90`, `180`, `270` (EKLE).
- [x] **Efekt Checkboxları** (EKLE):
  - Flip Horizontal, Flip Vertical, Grayscale, Sepia, Invert Colors, Deinterlace.
- [x] Denoise Dropdown: Off, Light, Moderate, Strong, Ultra (EKLE).
- [x] LUT dosya seçici (EKLE).
- [x] Canlı filtre özeti etiketi (EKLE).
- [x] Apply Filters / Cancel butonları (EKLE).
- [x] Progress bar + Status label (EKLE).
- [x] ErrorPanel (EKLE).
- [x] Backend: `POST /api/v1/filters/apply`.
- [x] **Bass/Treble/Gain slider'larını KALDIR** — bunlar CustomTkinter'da yok, Mixer'a ait değil burada.

### P4-T5: MixerTab.vue — Tam Yeniden Yazım
Kaynak: `ravn_app/ui/tabs/mixer_tab.py` — OKU.
- [x] **Mode Segmented Button**: `Audio` / `Video`.
- [x] **Operation Dropdown** (mode'a göre değişir):
  - Audio: `concat`, `mix`, `crossfade`, `normalize`, `trim`, `fade`.
  - Video: `concat`, `overlay`, `pip`, `side-by-side`, `watermark`, `transition`, `replace-audio`.
- [x] **Çoklu Dosya Girdi Listesi**: textbox + Add Inputs butonu + Clear Inputs butonu + dosya sayısı rozeti.
- [x] **Output seçici** (Browse).
- [x] **Global Ayarlar**: Audio Bitrate (128k/192k/256k/320k), Sample Rate (44100/48000), Normalize Audio checkbox, Re-encode Video checkbox.
- [x] **Dinamik Parametre Paneli** (seçilen işleme göre değişir):
  - Crossfade duration girişi.
  - Trim start + duration girişleri.
  - Fade-in + fade-out girişleri.
  - Position dropdown (Top Left/Top Right/Bottom Left/Bottom Right/Center).
  - Scale girişi.
  - Opacity girişi.
  - Orientation dropdown (Horizontal/Vertical).
  - Transition duration girişi.
- [x] Run Operation / Cancel butonları.
- [x] Progress bar + Status label.
- [x] ErrorPanel.
- [x] Backend: `POST /api/v1/mixer/run`.
- [x] **Mevcut 2 text input + `alert()` yapısını TAMİNEN SİL.**

### P4-T6: UtilitiesTab.vue — Tam Yeniden Yazım
Kaynak: `ravn_app/ui/tabs/utilities_tab.py` — OKU.
- [x] Input dosya seçici + Output dosya seçici.
- [x] **4 Katlanır Panel** (`<details>`/`<summary>` veya custom accordion):
  1. **Quick Helpers** (6 buton): Remux, Extract Audio (MP3 192k), Mute, Trim (30s), Preview Clip (10s), Thumbnail (JPG 640px).
  2. **Audio Utilities** (6 buton): Volume (+3dB), Fade in/out, Convert bitrate (192k 44.1kHz), Stereo/Mono (2-ch), Silence detection (-50dB), Loudness normalization (EBU R128).
  3. **Video Utilities** (8 buton): Scale (1280x720), Crop (90%), Pad, Rotate (90°), Change FPS (30fps), Color adjust, Blur/Sharpen, Deinterlace.
  4. **Smart Helpers** (3 buton): Black frame detection, Scene preview (10 scenes), Scene thumbnails (640px).
- [x] Her buton tıklandığında ilgili backend API çağrısı yapar.
- [x] Process butonu animasyonlu loading durumu.
- [x] Backend: `POST /api/v1/utilities/run` — operation parametresi ile.
- [x] **Mevcut 3 kartlık basit yapıyı TAMİNEN SİL.**

**P4 Doğrulama Kapısı:**
- [x] Converter'da gerçek dosya seçilebiliyor (mock path yok).
- [x] Subtitle'da hem indirme hem işleme paneli çalışıyor.
- [x] Filters'da 6 efekt checkbox'u ve denoise dropdown'u var.
- [x] Mixer'da Audio/Video mod değiştirilebiliyor, 13 işlem seçilebiliyor.
- [x] Utilities'de 4 katlanır panel, toplam 23 işlem butonu var.
- [x] HİÇBİR bileşende `alert()` çağrısı YOK.

---

## PHASE 5 — LIBRARY WORKSPACE TAM EŞLEŞMESİ

> Kaynak: `ravn_app/ui/tabs/library_tab.py`, `history_tab.py` — İKİSİNİ DE OKU.

### P5-T1: Library/History Tab Yapısı
Mevcut `Library.vue`'yu ikiye böl:
- [ ] `LibraryTab.vue` — Medya kütüphanesi (import, arama, koleksiyonlar).
- [ ] `HistoryTab.vue` — İndirme geçmişi (filtreleme, temizleme, istatistikler).
- [ ] Library workspace'de tab navigasyonu: `Media Library` | `History`.

### P5-T2: Media Library Tab — Tam İmplementasyon
- [ ] **İçe Aktarma Bölümü**: File Path (Browse), Title girişi, Tags girişi (virgülle ayrılmış), Add to Library butonu.
- [ ] **Arama & Filtre Bölümü**: Search query, Search tags, Format combobox (All/mp4/mp3/mkv/webm/wav/flac/aac/mov), Search + Reset butonları.
- [ ] **Dışa Aktarma**: Export JSON + Export CSV butonları.
- [ ] **Sonuç Listesi**: Her satırda → kapak görseli, Başlık, Format rozeti, Süre, Dosya Boyutu, Çözünürlük/Sample Rate, Tags, Dosya Yolu, Open File + Open Folder + Add to Collection butonları.
- [ ] **Sidebar Panelleri**:
  - Stats Card: Toplam öğe, Toplam boyut (MB/GB), Koleksiyon sayısı, Yinelenen grup sayısı.
  - Collections Card: Collection Name girişi + Create butonu, Target collection dropdown, Koleksiyon listesi.
  - Recent Searches Card: Önceki aramaların tıklanabilir listesi.
- [ ] Backend: `GET/POST /api/v1/library/`, `GET /api/v1/library/stats`, `POST /api/v1/library/export`.

### P5-T3: History Tab — Tam İmplementasyon
- [ ] Header: Başlık, Statistics butonu (popup dialog), Clear History butonu (onay dialog'u ile).
- [ ] Arama & Filtre: Search girişi (canlı), Format combobox (All/MP4/MP3/MKV/AVI), Status combobox (All/completed/failed/cancelled).
- [ ] Kaydırılabilir geçmiş listesi: Başlık, Format, Kalite, Boyut, Tarih, Status rozeti (completed=yeşil, failed=kırmızı, cancelled=amber), Open File butonu.
- [ ] Backend: `GET /api/v1/history/downloads`, `DELETE /api/v1/history/clear`, `GET /api/v1/history/stats`.

**P5 Doğrulama Kapısı:**
- [ ] Library'de dosya import edilebiliyor.
- [ ] Tags ile arama çalışıyor.
- [ ] Export JSON butonu dosya indiriyor.
- [ ] History'de status filtresi çalışıyor.

---

## PHASE 6 — SETTINGS TAM EŞLEŞMESİ

> Kaynak: `ravn_app/ui/tabs/settings_tab.py` — TAMAMINI OKU (uzun dosya).

### P6-T1: Araç Sağlık Bölümü — Dinamik
- [ ] `GET /api/v1/health` çağrısı ile gerçek sürüm, yol, durum bilgisi al.
- [ ] Her araç için ayrı kart: ffmpeg, ffprobe, yt-dlp, aria2c.
- [ ] Kart içeriği: Sürüm numarası, Yol, Etkilenen özellikler listesi.
- [ ] Refresh butonu.
- [ ] Install Missing Tools butonu (platform-aware komut gösterimi).
- [ ] Statik "Available"/"Optional" rozetlerini SİL.

### P6-T2: Genel Ayarlar
- [ ] Tema Seçici: `Nordic Dark` / `Nordic Light` dropdown → `data-theme` değiştirir.
- [ ] Dil Seçici: `Türkçe` / `English` dropdown.
- [ ] Checkboxlar: Notifications Enabled, Auto Check for Updates, Crash Reporting.
- [ ] Güncelleme Kontrol Butonu + Status label (GitHub Releases `waldseelen/ravn` kontrol).
- [ ] Kapatma Davranışı: `Close to System Tray` / `Close Application Fully` dropdown.

### P6-T3: İndirme Ayarları
- [ ] Download Directory (mevcut) + Browse butonu (Tauri `dialog.open`).
- [ ] Default Format: MP4 / MP3 / MKV dropdown.
- [ ] Default Quality: Best / 1080p / 720p / 480p dropdown.
- [ ] Concurrent Downloads: Slider (1–5).
- [ ] History Limit: Sayı girişi.

### P6-T4: Altyazı Ayarları
- [ ] Auto Subtitles checkbox.
- [ ] Preferred Subtitle Language dropdown (tr/en/de/fr/es).
- [ ] Subtitle Fallback Language dropdown.
- [ ] Include Auto-generated checkbox.
- [ ] Auto Embed Subtitles checkbox.

### P6-T5: Metadata & Sıralama Ayarları
- [ ] Embed Metadata checkbox (mevcut).
- [ ] Auto Sort Downloads checkbox.
- [ ] Download Naming Preset: Standard / Clean / Playlist dropdown.
- [ ] Filename Template girişi (düzenlenebilir).

### P6-T6: Post-Process Ayarları
- [ ] Extract Audio checkbox.
- [ ] Audio Format dropdown.
- [ ] Audio Bitrate dropdown.
- [ ] Convert Video checkbox.
- [ ] Convert Format dropdown.
- [ ] Embed Subtitles checkbox.

### P6-T7: Güvenilirlik Ayarları
- [ ] Enable Download Archive checkbox.
- [ ] Detect Duplicates checkbox.
- [ ] Continue Partial Downloads checkbox.
- [ ] Format Fallback checkbox.
- [ ] Download Rate Limit girişi (KB/s).

### P6-T8: Gelişmiş İndirme Ayarları (Katlanır Panel)
- [ ] Cookies Mode: None / Browser / File dropdown.
- [ ] Cookies Browser: chrome / firefox / edge / safari / brave / chromium / opera dropdown.
- [ ] Browser Profile girişi.
- [ ] Cookies File girişi + Browse butonu.
- [ ] Concurrent Fragments girişi.
- [ ] Fragment Retries girişi.
- [ ] Socket Timeout girişi (saniye).

### P6-T9: Torrent & Dönüştürme Ayarları
- [ ] aria2c Path girişi.
- [ ] Seed Time girişi (dakika).
- [ ] Max Connections girişi.
- [ ] FFmpeg Path girişi.
- [ ] Auto Cleanup checkbox.

### P6-T10: Ayar Eylemleri
- [ ] Save Settings butonu (mevcut).
- [ ] Reset Settings butonu (varsayılana döndür).
- [ ] Export Settings (JSON) butonu.
- [ ] Import Settings (JSON) butonu (Tauri `dialog.open`).

**P6 Doğrulama Kapısı:**
- [ ] Araç kartlarında gerçek sürüm numarası görünüyor.
- [ ] Tema değişince tüm sayfa anında renk değiştiriyor.
- [ ] Export Settings butonu JSON dosyası indiriyor.
- [ ] Tüm ayarlar `PATCH /api/v1/settings/` ile kaydediliyor.

---

## PHASE 7 — KUYRUK PANELİ TAM EŞLEŞMESİ

> Kaynak: `ravn_app/ui/queue_panel.py`, `ravn_app/ui/tabs/queue_tab.py`

### P7-T1: QueueItemWidget Yeniden Yapımı
- [ ] Sol kenarda renkli durum çizgisi (running=brass, completed=green, failed=red, queued=gray).
- [ ] Durum ikonu animasyonları:
  - Running: dönen spinner `⟳`.
  - Failed: titreşen hata ikonu `✕`.
  - Success: beliren onay işareti `✓`.
- [ ] Task adı + durum metni (yüzde, hız, süre veya hata mesajı).
- [ ] Progress bar (running görevler için).
- [ ] Aksiyon butonu: Cancel (running için), Open Folder (completed için).

### P7-T2: Kuyruk Yönetimi
- [ ] Pause Queue / Resume Queue butonları (mevcut — korunu).
- [ ] Clear Completed butonu.
- [ ] Boş durum widget'ı (kuyruk boşken illüstrasyon).
- [ ] Header stats: `Active: N • Queued: N • Completed: N`.

**P7 Doğrulama Kapısı:**
- [ ] Aktif indirme sırasında spinner dönüyor.
- [ ] Tamamlanan görevde Open Folder tıklanıyor.
- [ ] Clear Completed tüm bitmiş görevleri temizliyor.

---

## PHASE 8 — BACKEND API GENİŞLETMESİ

> Frontend'in ihtiyaç duyduğu ama mevcut olmayan API endpoint'leri.

### P8-T1: Converter API
- [ ] `POST /api/v1/convert/start` — FFmpeg dönüştürme başlat.
- [ ] `POST /api/v1/convert/cancel` — İptal.
- [ ] WebSocket event: `convert.progress`, `convert.complete`, `convert.error`.

### P8-T2: Subtitle API
- [ ] `POST /api/v1/subtitle/download` — yt-dlp ile altyazı indir.
- [ ] `POST /api/v1/subtitle/process` — Format dönüştür, zamanlama ayarla, embed et.

### P8-T3: Filters API
- [ ] `POST /api/v1/filters/apply` — FFmpeg filtreleri uygula.

### P8-T4: Mixer API
- [ ] `POST /api/v1/mixer/run` — Ses/video karıştırma işlemi başlat.

### P8-T5: Utilities API
- [ ] `POST /api/v1/utilities/run` — 23 utility işleminden herhangi birini çalıştır.

### P8-T6: Library API
- [ ] `GET /api/v1/library/` — Kütüphane listesi.
- [ ] `POST /api/v1/library/` — Kütüphaneye ekleme.
- [ ] `GET /api/v1/library/stats` — İstatistikler.
- [ ] `POST /api/v1/library/export` — JSON/CSV dışa aktarma.
- [ ] `POST /api/v1/library/collections/` — Koleksiyon CRUD.

### P8-T7: History API Genişletme
- [ ] `DELETE /api/v1/history/clear` — Geçmişi temizle.
- [ ] `GET /api/v1/history/stats` — Detaylı istatistikler.

### P8-T8: Torrent API
- [ ] `POST /api/v1/downloads/torrent/start` — Torrent başlat.
- [ ] `POST /api/v1/downloads/torrent/cancel` — İptal.
- [ ] WebSocket event: `torrent.progress`, `torrent.complete`.

### P8-T9: Health API Genişletme
- [ ] `GET /api/v1/health` zaten var — `version`, `path`, `affected_features` alanlarını ekle.

**P8 Doğrulama Kapısı:**
- [ ] Her endpoint `pytest` ile test edilmiş.
- [ ] WebSocket event'leri frontend'de doğru handle ediliyor.
- [ ] `GET /api/v1/health` gerçek araç bilgisi dönüyor.

---

## PHASE SIRASI VE BAĞIMLILIKLAR

```
P0 (Temizlik) ← İLK YAPILACAK, her şeyin temeli
  ↓
P8 (Backend API) ← Frontend'in bağlanacağı endpoint'ler
  ↓
P1 (App Shell) ← Navigasyon altyapısı
  ↓
P2 (Home) ← İstatistik kartları API'ye bağımlı
  ↓
P3 (Download) ← En kritik kullanıcı akışı
  ↓
P4 (Studio) ← 5 alt sekme, en hacimli phase
  ↓
P5 (Library) ← Library API'ye bağımlı
  ↓
P6 (Settings) ← Tüm ayar kontrolleri
  ↓
P7 (Queue) ← Son cilalama
```

> **Not:** P8 (Backend) ile P0 (Temizlik) paralel çalışılabilir.
> P3 ve P4 en uzun sürecek phase'lerdir — acele etme, kaliteli yap.

---

## NİHAİ DOĞRULAMA KONTROL LİSTESİ

Tüm phase'ler bittiğinde şu kontrolleri yap:

- [ ] `grep -r "alert(" frontend/src/components/` → **0 sonuç**.
- [ ] `grep -r "setTimeout" frontend/src/components/` → **0 sonuç** (mock amaçlı).
- [ ] `grep -r "bg-slate\|bg-purple\|bg-rose\|bg-cyan\|bg-teal\|bg-indigo\|bg-amber" frontend/src/components/` → **0 sonuç**.
- [ ] `grep -r "Coming soon\|TODO\|FIXME\|placeholder" frontend/src/components/` → **0 sonuç** (kullanıcıya görünen).
- [ ] Her Vue bileşeni en az bir backend API çağrısı yapıyor.
- [ ] Tema toggle çalışıyor: Dark ↔ Light.
- [ ] `Ctrl+K` komut paleti açılıyor.
- [ ] `npm run dev` ile uygulama hatasız başlıyor.
- [ ] `pytest -q` → tüm testler geçiyor.













