"""Experimental plugin/extension scaffold.

This module is intentionally not wired into the active desktop or CLI runtime.
It remains as a future-facing extension boundary only; no stable plugin API is
currently promised for packaged or day-to-day RAVN usage.
"""

import importlib
import logging
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

PLUGIN_SYSTEM_STATUS = "experimental"
PLUGIN_RUNTIME_INTEGRATED = False


class PluginHook(Enum):
    """Kullanılabilir plugin hook'ları"""
    # Download hooks
    BEFORE_DOWNLOAD = "before_download"
    AFTER_DOWNLOAD = "after_download"
    DOWNLOAD_ERROR = "download_error"

    # Conversion hooks
    BEFORE_CONVERSION = "before_conversion"
    AFTER_CONVERSION = "after_conversion"
    CONVERSION_ERROR = "conversion_error"

    # Subtitle hooks
    BEFORE_SUBTITLE_DOWNLOAD = "before_subtitle_download"
    AFTER_SUBTITLE_DOWNLOAD = "after_subtitle_download"

    # UI hooks
    ON_APP_STARTUP = "on_app_startup"
    ON_APP_SHUTDOWN = "on_app_shutdown"
    ON_TAB_CREATED = "on_tab_created"

    # Merge/normalize hooks
    BEFORE_MERGE = "before_merge"
    AFTER_MERGE = "after_merge"
    BEFORE_NORMALIZE = "before_normalize"
    AFTER_NORMALIZE = "after_normalize"


@dataclass
class PluginInfo:
    """Plugin meta bilgileri"""
    name: str
    version: str
    author: str
    description: str
    enabled: bool = True
    min_ravn_version: str = "1.0.0"


class PluginInterface:
    """Tüm pluginler bu arayüzü implement etmeli"""

    def get_info(self) -> PluginInfo:
        """Plugin bilgisini döndür"""
        raise NotImplementedError

    def on_load(self):
        """Plugin yüklendiğinde çalış"""
        pass

    def on_unload(self):
        """Plugin kaldırıldığında çalış"""
        pass

    def get_hooks(self) -> Dict[PluginHook, Callable]:
        """Bu plugin tarafından sağlanan hook'ları döndür"""
        return {}


class PluginManager:
    """Plugin yönetim sistemi"""

    def __init__(self, plugins_dir: str = "plugins"):
        """
        PluginManager'ı başlat

        Args:
            plugins_dir: Plugin dosyalarının dizini
        """
        self.plugins_dir = Path(plugins_dir)
        self.plugins: Dict[str, PluginInterface] = {}
        self.hooks: Dict[PluginHook, List[Callable]] = {hook: [] for hook in PluginHook}
        logger.info(f"PluginManager başlatıldı: {self.plugins_dir}")

    def discover_plugins(self) -> List[str]:
        """Plugin dizininde pluginleri keşfet"""
        if not self.plugins_dir.exists():
            logger.warning(f"Plugin dizini bulunamadı: {self.plugins_dir}")
            return []

        plugin_names = []

        # Tüm Python dosyalarını bul
        for py_file in self.plugins_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
            plugin_names.append(py_file.stem)

        # Tüm paket (klasör) ları bul
        for package_dir in self.plugins_dir.iterdir():
            if package_dir.is_dir() and not package_dir.name.startswith("_"):
                if (package_dir / "__init__.py").exists():
                    plugin_names.append(package_dir.name)

        logger.info(f"Bulunan pluginler: {plugin_names}")
        return plugin_names

    def load_plugin(self, plugin_name: str) -> bool:
        """Plugin'i yükle"""
        try:
            if plugin_name in self.plugins:
                logger.warning(f"Plugin zaten yüklü: {plugin_name}")
                return False

            # Plugin modülünü import et
            sys.path.insert(0, str(self.plugins_dir))
            module = importlib.import_module(plugin_name)
            sys.path.pop(0)

            # PluginInterface'i implement eden sınıfı bul
            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and
                    issubclass(attr, PluginInterface) and
                    attr is not PluginInterface):
                    plugin_class = attr
                    break

            if not plugin_class:
                logger.error(f"Plugin sınıfı bulunamadı: {plugin_name}")
                return False

            # Plugin örneğini oluştur
            plugin = plugin_class()
            info = plugin.get_info()

            if not info.enabled:
                logger.info(f"Plugin devre dışı bırakıldı: {plugin_name}")
                return False

            # Hook'ları kaydet
            hooks = plugin.get_hooks()
            for hook_name, hook_func in hooks.items():
                if isinstance(hook_name, PluginHook):
                    self.hooks[hook_name].append(hook_func)

            # Plugin'i depoya ekle
            self.plugins[plugin_name] = plugin

            # Plugin'in on_load metodunu çağır
            plugin.on_load()

            logger.info(f"Plugin yüklendi: {plugin_name} v{info.version}")
            return True

        except Exception as e:
            logger.error(f"Plugin yükleme hatası ({plugin_name}): {str(e)}")
            return False

    def unload_plugin(self, plugin_name: str) -> bool:
        """Plugin'i kaldır"""
        try:
            if plugin_name not in self.plugins:
                logger.warning(f"Plugin bulunamadı: {plugin_name}")
                return False

            plugin = self.plugins[plugin_name]

            # Hook'ları kaldır
            hooks = plugin.get_hooks()
            for hook_name, hook_func in hooks.items():
                if isinstance(hook_name, PluginHook):
                    if hook_func in self.hooks[hook_name]:
                        self.hooks[hook_name].remove(hook_func)

            # on_unload metodunu çağır
            plugin.on_unload()

            # Plugin'i deposundan kaldır
            del self.plugins[plugin_name]

            logger.info(f"Plugin kaldırıldı: {plugin_name}")
            return True

        except Exception as e:
            logger.error(f"Plugin kaldırma hatası ({plugin_name}): {str(e)}")
            return False

    def load_all_plugins(self) -> Dict[str, bool]:
        """Tüm pluginleri yükle"""
        plugin_names = self.discover_plugins()
        results = {}

        for plugin_name in plugin_names:
            results[plugin_name] = self.load_plugin(plugin_name)

        logger.info(f"Plugin yükleme özeti: {sum(results.values())}/{len(results)}")
        return results

    def trigger_hook(self, hook: PluginHook, *args, **kwargs) -> List[Any]:
        """Hook'u tetikle ve tüm plugin çıktılarını topla"""
        results: List[Any] = []

        if hook not in self.hooks:
            logger.warning(f"Bilinmeyen hook: {hook}")
            return results

        for hook_func in self.hooks[hook]:
            try:
                result = hook_func(*args, **kwargs)
                results.append(result)
            except Exception as e:
                logger.error(f"Hook yürütme hatası ({hook.value}): {str(e)}")

        return results

    def get_plugin_info(self, plugin_name: str) -> Optional[PluginInfo]:
        """Plugin bilgisini al"""
        if plugin_name not in self.plugins:
            return None

        return self.plugins[plugin_name].get_info()

    def list_plugins(self) -> Dict[str, PluginInfo]:
        """Yüklü tüm pluginleri listele"""
        return {
            name: plugin.get_info()
            for name, plugin in self.plugins.items()
        }


# ===== Örnek Plugin Uygulaması =====

class ExamplePlugin(PluginInterface):
    """Örnek plugin (şablon olarak kullanılabilir)"""

    def get_info(self) -> PluginInfo:
        return PluginInfo(
            name="Example Plugin",
            version="1.0.0",
            author="RAVN Team",
            description="Örnek plugin şablonu",
            enabled=True,
            min_ravn_version="1.0.0"
        )

    def on_load(self):
        """Plugin yüklendiğinde"""
        logger.info("Example Plugin yüklendi")

    def on_unload(self):
        """Plugin kaldırıldığında"""
        logger.info("Example Plugin kaldırıldı")

    def get_hooks(self) -> Dict[PluginHook, Callable]:
        """Plugin hook'ları"""
        return {
            PluginHook.AFTER_CONVERSION: self.on_conversion_complete,
            PluginHook.ON_APP_STARTUP: self.on_startup,
        }

    def on_conversion_complete(self, output_file: str, **kwargs):
        """Dönüştürme tamamlandığında"""
        logger.info(f"[ExamplePlugin] Dönüştürme tamamlandı: {output_file}")

    def on_startup(self, **kwargs):
        """Uygulama başlatıldığında"""
        logger.info("[ExamplePlugin] Uygulama başlatıldı")
