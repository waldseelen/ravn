# RAVN — Project Task Board

All development tasks organized by priority and status.

﻿Read AGENT.md, CLAUDE.md , ARCHITECTURE.md, README.md and PROGRESS.md first. Treat them as one
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

## Phase 1.0 — UI Tutarlılık & Kullanılabilirlik İyileştirmeleri

Tüm sekmeler arasında görsel dil, spacing, etkileşim ve hata yönetimi tutarlılığı.
Kolay maddeler tamamlandı (bkz. plan `agile-percolating-spark.md`). Kalanlar:

- [x] **[UI-01]** `_style_combo` / `_style_entry` tekrarını gider — 3 dosyadaki statik metotları `ui_components.py`'a taşı, sekmeler import etsin (`converter_tab.py`, `subtitle_tab.py`, `history_settings_tab.py`)
- [x] **[UI-03]** Hardcoded tooltip metinleri i18n'e taşı — `converter_tab.py` satır 159, 175, 191, 253'teki 4 Türkçe string'i `t()` çağrısıyla değiştir, i18n dosyalarına anahtar ekle
- [x] **[UI-05]** Focus ring animasyonu eksik giriş alanlarına ekle — `converter_tab.py` ve `subtitle_tab.py`'deki `CTkEntry`/`CTkComboBox` widget'larına `FocusIn`/`FocusOut` → `animate_focus_ring()` bağlaması
- [x] **[UI-06]** Hardcoded padding değerlerini `Spacing.*` token'larıyla değiştir — `converter_tab.py`, `error_panel.py`, `playlist_item.py`, `advanced_features.py` içindeki `padx=5`, `pady=4`, `padx=20` vb.
- [x] **[UI-08]** Subtitle ve History sekmelerine `Tooltip` ekle — dil seçimi, format filtresi, durum filtresi, zamanlama kontrolü gibi anlamlı tüm kontroller
- [x] **[UI-11]** Loading state görselini tüm sekmelerde standartlaştır — `_set_button_loading_state()` yardımcısını merkezi bir yere taşı; `subtitle_tab.py` ve `converter_tab.py`'deki eksik loading göstergelerini düzelt
- [x] **[UI-12]** Hata gösterimini standartlaştır — `converter_tab.py` ve `subtitle_tab.py`'ye `ErrorPanel` entegrasyonu ekle, log text widget'a düşen hataları kullanıcı dostu panele taşı
- [x] **[UI-09]** Klavye kısayolları ekle — tüm sekmelerde `Ctrl+Enter` (indir/dönüştür), `Escape` (iptal), `Ctrl+L` (URL/yol temizle) bağlamaları

---

## Phase 1.1 — Micro-interaction & Polish

UI/UX Pro Max analizi (Flat Design + Micro-interactions profili) çıktısına göre görsel kalite iyileştirmeleri.

- [x] **[MIC-01]** Tüm `CTkButton` widget'larına hover rengi ekle — `hover_color=Colors.ACCENT_HOVER` token kullanılsın, manuel hex yasak
- [x] **[MIC-02]** Treeview (Queue, History) satırlarına hover highlight ekle — `tag_configure("hover", background=BG_HOVER)` + `<Motion>` bağlaması
- [x] **[MIC-03]** Progress bar rengini `ACCENT` token'ına çek — varsayılan mavi yerine `Colors.ACCENT` kullanılsın; tüm sekmelerde tutarlı olsun
- [ ] **[MIC-04]** Active tab göstergesini belirginleştir — aktif sekme etiketini `font=Fonts.H2` (bold) yap veya accent renkli alt çizgi ekle (`main_window.py`)
- [ ] **[MIC-05]** Queue ve History sekmeleri için boş durum (empty state) ekle — içerik yokken ikon + açıklayıcı metin + aksiyon butonu göster
- [ ] **[MIC-06]** Başarı bildirimi (toast) otomatik kapanmasını standartlaştır — `3000 ms` after() ile dismiss; mevcut toast'ların hepsinin bu kurala uyduğunu doğrula
- [ ] **[MIC-07]** Disabled widget opaklığını standartlaştır — devre dışı kontroller `text_color=Colors.TEXT_MUTED`, `state="disabled"` kombinasyonu; tüm sekmelerde aynı görünüm

---

## Phase 1.2 — Accessibility & Keyboard Navigation

WCAG AA uyumluluğu ve klavye erişilebilirliği.

- [ ] **[ACC-01]** Focus ring animasyonu — `converter_tab.py` ve `subtitle_tab.py`'deki tüm `CTkEntry`/`CTkComboBox` widget'larına `FocusIn` → border `ACCENT`, `FocusOut` → border `BG_INPUT` geçişi ekle _(mevcut UI-05 ile çakışmaz, onu tamamlar)_
- [ ] **[ACC-02]** Global klavye kısayolları — `main_window.py`'de `Ctrl+Enter` (aktif sekmenin birincil eylemi), `Escape` (devam eden işlemi iptal et), `Ctrl+L` (URL/yol alanını odakla ve temizle) bağlamaları _(UI-09)_
- [ ] **[ACC-03]** Renk + ikon birlikteliği — hata/uyarı/başarı durumlarında renk tek başına bilgi taşımasın; `ErrorPanel` ve toast'larda mutlaka ikon prefix (`⚠`, `✓`, `ℹ`) kullanılsın
- [ ] **[ACC-04]** Tab sırası doğrulaması — her sekmedeki widget'ların Tab geçiş sırası görsel soldan-sağa, yukarıdan-aşağıya düzeniyle örtüşsün; bozuk sıralar `tkinter.Widget.lift()` ile düzeltilsin
- [ ] **[ACC-05]** Minimum tıklama alanı — tüm ikon butonları (kare olanlar dahil) en az `32×32 px` görünür boyuta sahip olsun; `BTN_HEIGHT_SM=32` token'ı baz alınsın

---

**(After GUI is Done) — Build & Distribution:**

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
