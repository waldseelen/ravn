"""
Otomatik Güncelleme Sistemi
GitHub Release'lerinden yeni sürümleri kontrol et ve indir
"""

import logging
import subprocess
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, Optional

import requests

logger = logging.getLogger(__name__)


class UpdateStatus(Enum):
    """Güncelleme durumu"""
    CHECKING = "checking"
    UP_TO_DATE = "up_to_date"
    UPDATE_AVAILABLE = "update_available"
    DOWNLOADING = "downloading"
    INSTALLING = "installing"
    SUCCESS = "success"
    ERROR = "error"


@dataclass
class ReleaseInfo:
    """GitHub sürümü bilgileri"""
    version: str
    tag: str
    name: str
    body: str
    published_at: str
    download_url: str
    file_name: str
    file_size: int


class UpdateManager:
    """Otomatik güncelleme yöneticisi"""

    def __init__(
        self,
        current_version: str,
        github_owner: str = "ravn-project",
        github_repo: str = "ravn",
        update_dir: Optional[str] = None,
        check_interval_hours: int = 24
    ):
        """
        Başlatma

        Args:
            current_version: Geçerli sürüm (örn: "1.0.0")
            github_owner: GitHub proje sahibi
            github_repo: GitHub depo adı
            update_dir: Güncelleme indirme dizini
            check_interval_hours: Kontrol aralığı (saat)
        """
        self.current_version = current_version
        self.github_owner = github_owner
        self.github_repo = github_repo
        self.update_dir = Path(update_dir) if update_dir else Path.home() / ".ravn" / "updates"
        self.check_interval = timedelta(hours=check_interval_hours)

        # Callbacks
        self.on_status_change: Optional[Callable[[UpdateStatus], None]] = None
        self.on_progress: Optional[Callable[[int], None]] = None

        # State
        self._status = UpdateStatus.CHECKING
        self._last_check: Optional[datetime] = None
        self._latest_release: Optional[ReleaseInfo] = None

        self.update_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"UpdateManager başlatıldı: v{current_version}")

    @property
    def status(self) -> UpdateStatus:
        """Şu anki durum"""
        return self._status

    @status.setter
    def status(self, value: UpdateStatus):
        """Durumu değiştir ve callback çağır"""
        if value != self._status:
            self._status = value
            logger.info(f"Durum değişti: {value.value}")
            if self.on_status_change:
                self.on_status_change(value)

    def get_latest_release(self) -> Optional[ReleaseInfo]:
        """
        GitHub'dan en son sürümü al

        Returns:
            ReleaseInfo veya None (başarısız ise)
        """
        try:
            self.status = UpdateStatus.CHECKING

            url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/releases/latest"

            response = requests.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()

            # Asset'i bul
            asset = None
            for a in data.get('assets', []):
                if a['name'].endswith('.exe') or a['name'].endswith('.tar.gz') or a['name'].endswith('.zip'):
                    asset = a
                    break

            if not asset:
                logger.warning("İndirilebilir asset bulunamadı")
                return None

            release = ReleaseInfo(
                version=data['tag_name'].lstrip('v'),
                tag=data['tag_name'],
                name=data['name'],
                body=data['body'],
                published_at=data['published_at'],
                download_url=asset['browser_download_url'],
                file_name=asset['name'],
                file_size=asset['size']
            )

            self._latest_release = release
            self._last_check = datetime.now()

            logger.info(f"En son sürüm: v{release.version}")
            return release

        except requests.exceptions.RequestException as e:
            logger.error(f"GitHub API hatası: {e}")
            self.status = UpdateStatus.ERROR
            return None
        except (KeyError, ValueError) as e:
            logger.error(f"Sürüm parse hatası: {e}")
            return None

    def check_for_updates(self) -> bool:
        """
        Güncelleme kontrol et

        Returns:
            True (güncelleme var), False (güncel)
        """
        # Son kontrol çok yakınsa atla
        if self._last_check and datetime.now() - self._last_check < self.check_interval:
            logger.info("Son kontrol henüz yeterince uzun olmadı")
            return False

        release = self.get_latest_release()

        if not release:
            self.status = UpdateStatus.ERROR
            return False

        if self._is_newer_version(release.version):
            self.status = UpdateStatus.UPDATE_AVAILABLE
            return True
        else:
            self.status = UpdateStatus.UP_TO_DATE
            return False

    def _is_newer_version(self, new_version: str) -> bool:
        """Yeni sürüm daha mı yeni?"""
        try:
            current_parts = [int(x) for x in self.current_version.split('.')]
            new_parts = [int(x) for x in new_version.split('.')]

            # Aynı uzunluğa getir
            max_len = max(len(current_parts), len(new_parts))
            current_parts += [0] * (max_len - len(current_parts))
            new_parts += [0] * (max_len - len(new_parts))

            return new_parts > current_parts

        except ValueError:
            logger.error(f"Sürüm karşılaştırması başarısız: {self.current_version} vs {new_version}")
            return False

    def download_update(self) -> Optional[Path]:
        """
        Güncellemeyi indir

        Returns:
            İndirilen dosyanın yolu
        """
        if not self._latest_release:
            logger.error("Sürüm bilgisi yok")
            return None

        try:
            self.status = UpdateStatus.DOWNLOADING

            download_path = self.update_dir / self._latest_release.file_name

            logger.info(f"İndiriliyor: {self._latest_release.download_url}")

            response = requests.get(
                self._latest_release.download_url,
                stream=True,
                timeout=300
            )
            response.raise_for_status()

            # Progress tracking
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            with open(download_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        if total_size > 0 and self.on_progress:
                            progress = int((downloaded / total_size) * 100)
                            self.on_progress(progress)

            logger.info(f"İndirme tamamlandı: {download_path}")
            return download_path

        except Exception as e:
            logger.error(f"İndirme hatası: {e}")
            self.status = UpdateStatus.ERROR
            return None

    def install_update(self, downloaded_file: Path) -> bool:
        """
        Güncellemeyi yükle

        Args:
            downloaded_file: İndirilen dosyanın yolu

        Returns:
            True (başarı), False (başarısız)
        """
        try:
            self.status = UpdateStatus.INSTALLING

            if not downloaded_file.exists():
                logger.error(f"Dosya bulunamadı: {downloaded_file}")
                self.status = UpdateStatus.ERROR
                return False

            # Windows executable
            if downloaded_file.suffix == '.exe':
                logger.info(f"Installer çalıştırılıyor: {downloaded_file}")

                # Installer'ı başlat (yeni process'te)
                subprocess.Popen(
                    [str(downloaded_file)],
                    cwd=self.update_dir
                )

                self.status = UpdateStatus.SUCCESS
                return True

            # Diğer formatlar (zip, tar.gz)
            elif downloaded_file.suffix in ['.zip', '.gz']:
                logger.info(f"Arşiv çıkartılıyor: {downloaded_file}")

                extract_dir = self.update_dir / "extracted"

                if downloaded_file.suffix == '.zip':
                    import zipfile
                    with zipfile.ZipFile(downloaded_file) as zf:
                        zf.extractall(extract_dir)
                else:
                    import tarfile
                    with tarfile.open(downloaded_file) as tf:
                        tf.extractall(extract_dir)

                self.status = UpdateStatus.SUCCESS
                logger.info(f"Güncelleme hazır: {extract_dir}")
                return True

            else:
                logger.error(f"Desteklenmeyen format: {downloaded_file.suffix}")
                self.status = UpdateStatus.ERROR
                return False

        except Exception as e:
            logger.error(f"Yükleme hatası: {e}")
            self.status = UpdateStatus.ERROR
            return False

    def check_and_update_async(self, callback: Optional[Callable[[bool], None]] = None):
        """
        Asenkron güncelleme kontrol ve yükle

        Args:
            callback: Tamamlandığında çağrılacak fonksiyon (başarı bool)
        """
        def _worker():
            try:
                if self.check_for_updates():
                    downloaded = self.download_update()
                    if downloaded:
                        success = self.install_update(downloaded)
                    else:
                        success = False
                else:
                    success = True  # Güncel demek başarı

                if callback:
                    callback(success)

            except Exception as e:
                logger.error(f"Async güncelleme hatası: {e}")
                if callback:
                    callback(False)

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()

    def get_release_notes(self) -> Optional[str]:
        """En son sürüm notlarını al"""
        if self._latest_release:
            return self._latest_release.body
        return None

    def cleanup_old_updates(self, keep_last: int = 2):
        """Eski güncelleme dosyalarını sil"""
        try:
            files = sorted(
                list(self.update_dir.glob("*.exe")) +
                list(self.update_dir.glob("*.zip")) +
                list(self.update_dir.glob("*.tar.gz")),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )

            for f in files[keep_last:]:
                f.unlink()
                logger.info(f"Eski güncelleme silindi: {f}")

        except Exception as e:
            logger.error(f"Cleanup hatası: {e}")


class UpdateNotification:
    """Güncelleme bildirimi UI"""

    def __init__(self, update_manager: UpdateManager):
        self.manager = update_manager
        self.notification_callback: Optional[Callable[[Dict], None]] = None

    def show_notification(self, release: ReleaseInfo):
        """Güncelleme bildirimi göster"""
        notification = {
            'title': f'RAVN Güncellemesi Mevcut: v{release.version}',
            'message': f'Yeni sürüm v{release.version} indirilebilir\n\n{release.body[:200]}...',
            'version': release.version,
            'release_notes': release.body,
            'can_update': True
        }

        if self.notification_callback:
            self.notification_callback(notification)
