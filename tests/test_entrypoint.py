import builtins
import sys
import types

import ravn


def _patch_startup_steps(monkeypatch):
    monkeypatch.setattr(ravn, "setup_logging", lambda: None)
    monkeypatch.setattr(ravn, "ensure_directories_exist", lambda: None)
    monkeypatch.setattr(ravn, "migrate_all_legacy_files", lambda: None)


def test_main_handles_keyboard_interrupt_during_import(monkeypatch):
    _patch_startup_steps(monkeypatch)

    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "ravn_app.ui.main_window":
            raise KeyboardInterrupt()
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    ravn.main()


def test_main_calls_quit_handler_on_keyboard_interrupt(monkeypatch):
    _patch_startup_steps(monkeypatch)
    state = {"quit_called": False}

    class FakeApp:
        def mainloop(self):
            raise KeyboardInterrupt()

        def _quit_app(self):
            state["quit_called"] = True

    fake_module = types.ModuleType("ravn_app.ui.main_window")
    fake_module.YouTubeDownloaderApp = FakeApp
    monkeypatch.setitem(sys.modules, "ravn_app.ui.main_window", fake_module)

    ravn.main()

    assert state["quit_called"] is True


def test_main_falls_back_to_destroy_when_quit_handler_missing(monkeypatch):
    _patch_startup_steps(monkeypatch)
    state = {"destroy_called": False}

    class FakeApp:
        def mainloop(self):
            raise KeyboardInterrupt()

        def destroy(self):
            state["destroy_called"] = True

    fake_module = types.ModuleType("ravn_app.ui.main_window")
    fake_module.YouTubeDownloaderApp = FakeApp
    monkeypatch.setitem(sys.modules, "ravn_app.ui.main_window", fake_module)

    ravn.main()

    assert state["destroy_called"] is True
