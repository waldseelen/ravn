"""
RAVN Entegrasyon Test Scripti
Tüm modüllerin doğru çalıştığını test eder
"""

import sys
import os

# Proje kök dizinini Python path'ine ekle
sys.path.insert(0, os.path.dirname(__file__))

def test_imports():
    """Tüm import'ları test et"""
    print("=" * 60)
    print("RAVN Entegrasyon Testi")
    print("=" * 60)
    print()

    tests = [
        ("Core - Database", "from ravn_app.core.database import DatabaseManager, ConfigManager"),
        ("Core - Subtitle", "from ravn_app.core.subtitle_manager import SubtitleDownloader, SubtitleConverter"),
        ("Core - Converter", "from ravn_app.core.converter import VideoConverter, BatchConverter"),
        ("UI - Main Window", "from ravn_app.ui.main_window import YouTubeDownloaderApp"),
        ("UI - Subtitle Tab", "from ravn_app.ui.subtitle_tab import SubtitleTab"),
        ("UI - History Tab", "from ravn_app.ui.history_settings_tab import HistoryTab, SettingsTab"),
        ("UI - Advanced", "from ravn_app.ui.advanced_features import SearchFilter, ThemeManager"),
    ]

    passed = 0
    failed = 0

    for test_name, import_stmt in tests:
        try:
            exec(import_stmt)
            print(f"✓ {test_name:30} OK")
            passed += 1
        except Exception as e:
            print(f"✗ {test_name:30} FAILED: {str(e)}")
            failed += 1

    print()
    print("-" * 60)
    print(f"Sonuçlar: {passed} başarılı, {failed} başarısız")
    print("-" * 60)

    return failed == 0


def test_database_creation():
    """Veritabanı oluşturma testi"""
    print("\n📊 Veritabanı Testi...")

    try:
        from ravn_app.core.database import DatabaseManager, DownloadRecord

        # Test veritabanı oluştur
        db = DatabaseManager("test_ravn.db")

        # Test kaydı ekle
        record = DownloadRecord(
            url="https://test.com",
            title="Test Video",
            format="MP4",
            quality="1080p",
            file_path="/test/path.mp4",
            file_size=1024000
        )

        record_id = db.add_download(record)
        print(f"  ✓ Kayıt eklendi (ID: {record_id})")

        # Kaydı geri al
        downloads = db.get_downloads(limit=1)
        assert len(downloads) > 0, "Kayıt bulunamadı"
        print(f"  ✓ Kayıt okundu: {downloads[0].title}")

        # Temizlik
        db.close()
        os.remove("test_ravn.db")
        print("  ✓ Veritabanı testi başarılı")

        return True
    except Exception as e:
        print(f"  ✗ Veritabanı testi başarısız: {e}")
        return False


def test_config():
    """Konfigürasyon testi"""
    print("\n⚙️  Konfigürasyon Testi...")

    try:
        from ravn_app.core.database import ConfigManager

        # Test config oluştur
        config = ConfigManager("test_config.json")

        # Değer ayarla
        config.set('test_key', 'test_value')
        print("  ✓ Ayar kaydedildi")

        # Değer oku
        value = config.get('test_key')
        assert value == 'test_value', "Değer eşleşmiyor"
        print(f"  ✓ Ayar okundu: {value}")

        # Temizlik
        os.remove("test_config.json")
        print("  ✓ Konfigürasyon testi başarılı")

        return True
    except Exception as e:
        print(f"  ✗ Konfigürasyon testi başarısız: {e}")
        return False


def test_subtitle_classes():
    """Altyazı sınıflarını test et"""
    print("\n📝 Altyazı Sınıfları Testi...")

    try:
        from ravn_app.core.subtitle_manager import (
            SubtitleDownloader,
            SubtitleConverter,
            SubtitleEditor,
            SubtitleEmbedder,
            SubtitleFormat
        )

        # Sınıfları oluştur
        downloader = SubtitleDownloader()
        converter = SubtitleConverter()
        editor = SubtitleEditor()
        embedder = SubtitleEmbedder()

        print("  ✓ SubtitleDownloader oluşturuldu")
        print("  ✓ SubtitleConverter oluşturuldu")
        print("  ✓ SubtitleEditor oluşturuldu")
        print("  ✓ SubtitleEmbedder oluşturuldu")

        # Format enum kontrolü
        assert SubtitleFormat.SRT.value == "srt"
        assert SubtitleFormat.VTT.value == "vtt"
        print("  ✓ SubtitleFormat enum doğru")

        print("  ✓ Altyazı sınıfları testi başarılı")
        return True
    except Exception as e:
        print(f"  ✗ Altyazı sınıfları testi başarısız: {e}")
        return False


def main():
    """Ana test fonksiyonu"""
    try:
        results = []

        # Import testleri
        results.append(("Import", test_imports()))

        # Veritabanı testi
        results.append(("Database", test_database_creation()))

        # Konfigürasyon testi
        results.append(("Config", test_config()))

        # Altyazı sınıfları testi
        results.append(("Subtitle Classes", test_subtitle_classes()))

        # Özet
        print("\n" + "=" * 60)
        print("TEST ÖZETİ")
        print("=" * 60)

        all_passed = True
        for name, passed in results:
            status = "✓ BAŞARILI" if passed else "✗ BAŞARISIZ"
            print(f"{name:20} {status}")
            if not passed:
                all_passed = False

        print("=" * 60)

        if all_passed:
            print("\n🎉 TÜM TESTLER BAŞARILI!")
            print("\nRavn uygulaması çalışmaya hazır.")
            print("Başlatmak için: python ravn.py")
            return 0
        else:
            print("\n⚠️  BAZI TESTLER BAŞARISIZ")
            print("\nLütfen hataları kontrol edin.")
            return 1

    except KeyboardInterrupt:
        print("\n\nTest iptal edildi.")
        return 1
    except Exception as e:
        print(f"\n✗ Beklenmeyen hata: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
