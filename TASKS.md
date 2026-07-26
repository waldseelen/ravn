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














