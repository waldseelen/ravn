# RAVN — Project Task Board

All development tasks organized by priority and status.

﻿Read AGENT.md, CLAUDE.md , ARCHITECTURE.md, README.md  and PROGRESS.md first. Treat them as one
unified instruction set and follow all rules, constraints, and context strictly.

Then execute TASKS.md as the single source of truth. Only complete tasks marked [ ]. Never touch
or redo tasks marked [x].

Do not deviate from scope, structure, or intent. If any conflict occurs, follow the most recent
and most specific instruction.

After completing all eligible tasks, update AGENT.md, CLAUDE.md, and PROGRESS.md briefly and
accurately based on this session.



---

## Status Legend

- `[ ]` — Not started
- `[~]` — In progress
- `[x]` — Done
- `[!]` — Blocked

---

---


## Phase 1 — UI Tutarlılık & Kullanılabilirlik İyileştirmeleri

Tüm sekmeler arasında görsel dil, spacing, etkileşim ve hata yönetimi tutarlılığı.
Kolay maddeler tamamlandı (bkz. plan `agile-percolating-spark.md`). Kalanlar:

- [ ] **[UI-01]** `_style_combo` / `_style_entry` tekrarını gider — 3 dosyadaki statik metotları `ui_components.py`'a taşı, sekmeler import etsin (`converter_tab.py`, `subtitle_tab.py`, `history_settings_tab.py`)
- [ ] **[UI-03]** Hardcoded tooltip metinleri i18n'e taşı — `converter_tab.py` satır 159, 175, 191, 253'teki 4 Türkçe string'i `t()` çağrısıyla değiştir, i18n dosyalarına anahtar ekle
- [ ] **[UI-05]** Focus ring animasyonu eksik giriş alanlarına ekle — `converter_tab.py` ve `subtitle_tab.py`'deki `CTkEntry`/`CTkComboBox` widget'larına `FocusIn`/`FocusOut` → `animate_focus_ring()` bağlaması
- [ ] **[UI-06]** Hardcoded padding değerlerini `Spacing.*` token'larıyla değiştir — `converter_tab.py`, `error_panel.py`, `playlist_item.py`, `advanced_features.py` içindeki `padx=5`, `pady=4`, `padx=20` vb.
- [ ] **[UI-08]** Subtitle ve History sekmelerine `Tooltip` ekle — dil seçimi, format filtresi, durum filtresi, zamanlama kontrolü gibi anlamlı tüm kontroller
- [ ] **[UI-11]** Loading state görselini tüm sekmelerde standartlaştır — `_set_button_loading_state()` yardımcısını merkezi bir yere taşı; `subtitle_tab.py` ve `converter_tab.py`'deki eksik loading göstergelerini düzelt
- [ ] **[UI-12]** Hata gösterimini standartlaştır — `converter_tab.py` ve `subtitle_tab.py`'ye `ErrorPanel` entegrasyonu ekle, log text widget'a düşen hataları kullanıcı dostu panele taşı
- [ ] **[UI-09]** Klavye kısayolları ekle — tüm sekmelerde `Ctrl+Enter` (indir/dönüştür), `Escape` (iptal), `Ctrl+L` (URL/yol temizle) bağlamaları

---

**Phase 1 (After GUI is Done) — Build & Distribution:**

1. PyInstaller spec updates with FFmpeg bundling
2. Windows/Linux/macOS build pipelines
3. GitHub Actions CI/CD setup
4. Installer testing and code signing






## Phase X — Build, Package & Distribution

Cross-platform binary builds and installers. (After GUI is polished)

- [ ] **[BLD-01]** Update `ravn.spec` (PyInstaller) — include FFmpeg binaries for Windows
- [ ] **[BLD-02]** Bundle FFmpeg Windows binaries in `assets/ffmpeg/win64/`
- [ ] **[BLD-03]** Auto-detect bundled FFmpeg in `ffmpeg_checker.py`
- [ ] **[BLD-04]** Update `build.ps1` — full Windows build pipeline
- [ ] **[BLD-05]** Create `build.sh` — Linux build pipeline (PyInstaller → AppImage or .deb)
- [ ] **[BLD-06]** macOS build pipeline — PyInstaller → `.app` bundle → `.dmg`
- [ ] **[BLD-07]** GitHub Actions `tests.yml` — Windows/Linux/macOS artifact builds on tag
- [ ] **[BLD-08]** GitHub Actions `release.yml` — auto-publish on `v*` tag
- [ ] **[BLD-09]** Test installer on clean VM — verify FFmpeg found, app launches, config dir created
- [ ] **[BLD-10]** Code-sign Windows executable (minimum: self-signed cert)

**Dependencies:** GUI polish complete (Phase 4).

---

## General Notes

- All file paths use `pathlib.Path` — no hardcoded separators
- All user-facing strings support TR/EN toggle (i18n-ready structure)
- Minimum Python version: 3.9
- FFmpeg minimum version: 5.0
- yt-dlp must always be latest release (no version pin)


---
