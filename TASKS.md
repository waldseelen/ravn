# RAVN — Project Task Board

All development tasks organized by priority and status.

---

## Status Legend

- `[ ]` — Not started
- `[~]` — In progress
- `[x]` — Done
- `[!]` — Blocked

---

## Phase 4C — UI Polish & Micro-interactions (Nordic Brand Theme)

Smooth transitions, micro-interactions, real-time feedback, and RAVN brand-consistent visual polish. Minimal animations that enhance usability without being distracting. Theme: Nordic kahverengi/beige minimalism with accent highlights.

**Implementation Order:** 1 → 3 → 4 → 2 → 5 → 6 → 7 (dependencies-first approach)

### 4C.1 — Brand Color Palette Update [x]

**Priority:** FOUNDATION — Required before all other sections.

Align design system with RAVN brand (Nordic kahverengi + minimal beige).

- [x] **[BRD-01]** Update `design_tokens.py` — Add brand-primary kahverengi (#3D3230 or similar) as accent
- [x] **[BRD-02]** Define secondary accent — light beige (#D4C5B9 or warm gray)
- [x] **[BRD-03]** Replace blue accent (#3b82f6) → kahverengi for consistency
- [x] **[BRD-04]** Dark mode backgrounds — Keep #141414 but adjust surface colors for kahverengi harmony
- [x] **[BRD-05]** Success/error/warning — Maintain semantic colors but test contrast with new palette
- [x] **[BRD-06]** Hover state color — Use kahverengi-derived lighter shade for hover (not blue)

**Output:** Updated `design_tokens.py` with Nordic theme fully integrated.

**Dependencies:** None. Start immediately.

---

### 4C.2 — Icon System & Placement [x]

**Priority:** MEDIUM — Visual consistency (depends on color palette being set).

Strategically place vector icons (not emojis) for clarity and brand consistency.

**Navigation & Tabs:**

- [x] **[ICN-01]** Download tab — ⬇ → minimize icon or custom raven icon (top-left tab)
- [x] **[ICN-02]** Converter tab — ⇄ → gear/convert icon (second tab)
- [x] **[ICN-03]** Subtitle tab — ≡ → subtitle/speech icon (third tab)
- [x] **[ICN-04]** History tab — ◷ → history/clock icon (fourth tab)
- [x] **[ICN-05]** Settings tab — ⚙ → settings/cog icon (fifth tab)
- [x] **[ICN-06]** Queue panel — ☰ → queue/list icon (header or left sidebar)

**Action Buttons:**

- [x] **[ICN-07]** Download button — Large + kahverengi icon indicator
- [x] **[ICN-08]** Convert button — Process/arrow icon
- [x] **[ICN-09]** Browse/Select button — Folder icon
- [x] **[ICN-10]** Cancel/Stop button — X or stop icon in red/error color
- [x] **[ICN-11]** Retry button — Clockwise arrow/refresh icon

**Status Indicators:**

- [x] **[ICN-12]** Queued status — Purple hourglass or circle outline
- [x] **[ICN-13]** Running status — Animated spinner (2-3 rot/sec)
- [x] **[ICN-14]** Success status — Green checkmark (static, 150ms slide-in)
- [x] **[ICN-15]** Error status — Red X or exclamation (pulsing red)
- [x] **[ICN-16]** Paused status — Pause symbol (gray)

**Form & Input:**

- [x] **[ICN-17]** URL input prefix icon — Link/chain icon (left of input)
- [x] **[ICN-18]** Quality selector prefix — Video/quality icon
- [x] **[ICN-19]** Format selector prefix — File type icon
- [x] **[ICN-20]** Error indicator — Exclamation triangle (red, right of field)
- [x] **[ICN-21]** Success indicator — Green checkmark (right of field, animated)
- [x] **[ICN-22]** Clear/Reset button — Trash or X icon (muted gray)

**Implementation:** Use Lucide icon library (SVG) or custom Raven vector assets.

**Dependencies:** 4C.1 (colors). Can start once BRD-01 to BRD-06 complete.

---

### 4C.3 — Smooth State Transitions [x]

**Priority:** HIGH — Core animations foundation (POL-01, POL-02 already implemented via AnimationManager).

Smooth visual feedback for all interactive elements (150-250ms easing). Uses centralized AnimationManager with cubic easing curves.

- [x] **[POL-01]** Button press states — scale (0.95–1.0) + kahverengi glow on click
- [x] **[POL-02]** Input field focus ring — animated kahverengi border (gray → brand kahverengi, 150ms)
- [x] **[POL-03]** Hover states — subtle beige background shift + opacity (100ms ease-out)
- [x] **[POL-04]** Tab switching — crossfade between tab content (150ms, no flicker)
- [x] **[POL-05]** Modal open/close — scale + fade animation (150-200ms, centered)
- [x] **[POL-06]** Dropdown expand/collapse — smooth height transition + kahverengi accent line
- [x] **[POL-07]** Progress bar fill — smooth linear fill (no jumps) + color pulse on 100%
- [x] **[POL-08]** Disabled state clarity — reduced opacity (0.5) + desaturated kahverengi

**Implementation:** CustomTkinter animation loop using `after()` and easing functions. All transitions use kahverengi accent color.

**Dependencies:** 4C.1 (colors must be defined). POL-01 and POL-02 partially done via AnimationManager.

---

### 4C.4 — Loading & Operational Feedback [x]

**Priority:** HIGH — User-facing feedback during async operations.

Real-time visual feedback during async operations with brand consistency. Spinner animation already available via AnimationManager.

- [x] **[POL-09]** Animated spinner — kahverengi rotating icon (2-3 rotations/sec) during download/convert
- [x] **[POL-10]** Progress bar — kahverengi fill color + beige background (smooth 60fps updates)
- [x] **[POL-11]** Queue item entrance — slide-in from top + kahverengi accent bar (150ms)
- [x] **[POL-12]** Job status badges — color-coded icons (purple queued, orange running, green done)
- [x] **[POL-13]** "Processing..." — animated kahverengi icon + "Downloading..." text with ellipsis
- [x] **[POL-14]** Success feedback — brief green flash + checkmark animation (300ms total)
- [x] **[POL-15]** Completion sound/visual — Subtle kahverengi pulse + success checkmark

**Implementation:** Use `AnimationManager.start_spinner_loop()` and `ctk.CTkProgressBar` with kahverengi color.

**Dependencies:** 4C.1 (colors), 4C.3 (animations). POL-09 spinner already works via AnimationManager.

---

### 4C.5 — Error & Form Feedback [x]

**Priority:** MEDIUM — User feedback on actions.

Inline, contextual feedback without disruption. Brand-consistent error messaging.

- [x] **[POL-16]** Inline error messages — red icon + text below input (color fade-in, 150ms)
- [x] **[POL-17]** Input validation feedback — real-time (on blur, not keystroke)
- [x] **[POL-18]** Error recovery affordance — "Retry" or "Edit" hint with icon near error
- [x] **[POL-19]** Form field error state — red left border indicator + icon (no full red)
- [x] **[POL-20]** Success toast — slide-in from top-right, green checkmark + "Success" text (3s auto-dismiss)
- [x] **[POL-21]** Warning toast — amber/orange warning icon + clear message (4s auto-dismiss)

**Implementation:** Inline `ctk.CTkLabel` with icon + color animation; custom toast widget.

**Dependencies:** 4C.3 (animations), 4C.1 (colors).

---

### 4C.6 — Visual Polish & Consistency [x]

**Priority:** LOW-MEDIUM — Refinement and details.

Refinements that improve perceived quality and brand alignment.

- [x] **[POL-22]** Consistent corner radius — 8px for cards, 6px for buttons/inputs (soft Nordic feel)
- [x] **[POL-23]** Focus ring visibility — 2px kahverengi ring on all interactive elements
- [x] **[POL-24]** Smooth color transitions — all state changes use easing (not instant)
- [x] **[POL-25]** Empty state messaging — clear text + action icon (e.g., folder icon for "No files")
- [x] **[POL-26]** Loading skeleton — beige placeholder cards with subtle shimmer
- [x] **[POL-27]** Cursor feedback — pointer cursor on buttons + icons, text cursor on inputs
- [x] **[POL-28]** Drag & drop refinement — animated kahverengi dashed border on target zone
- [x] **[POL-29]** Scroll smoothness — smooth scrolling, no jank in queue/history
- [x] **[POL-30]** Brand consistency check — all UI elements use kahverengi/beige (not blue)

**Implementation:** `ctk.CTkCanvas` for custom effects; frame-based animation loop.

**Dependencies:** 4C.1 (colors), 4C.3 (animations).

---

### 4C.7 — Accessibility & Motor Control [x]

**Priority:** CRITICAL (Final Pass) — Ensure micro-interactions don't harm accessibility.

Ensure micro-interactions don't harm accessibility.

- [x] **[POL-31]** Respect reduced-motion — disable animations if system preference detected
- [x] **[POL-32]** Keyboard navigation — all animations preserve tab order + focus visibility
- [x] **[POL-33]** Animation cancellation — allow user to interrupt long operations (click to stop)
- [x] **[POL-34]** Tooltip on hover — explain button actions with icons (300ms delay)
- [x] **[POL-35]** Screen reader support — icon labels + descriptive aria-labels

**Implementation:** Platform detection for reduced-motion; focus management during transitions.

**Dependencies:** All other 4C sections (final accessibility pass after implementation).

---

## Phase 6 — Torrent/Magnet Entegrasyonu

- [x] 6A: Aria2Runner
- [x] 6B: TorrentDownloader
- [x] 6C: Hata Yönetimi (parse_aria2c_error)
- [x] 6D: URL Router + Drag-Drop
- [x] 6E: Ayarlar
- [x] 6F: CLI (ravn torrent)
- [x] 6G: Stream UI
- [x] 6H: Dokümantasyon

---

## Phase 5 — Build, Package & Distribution

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

## Quick Reference: What's Next?

**Phase 4 (Next Priority) — GUI Polish & Full Controllability:**

1. Audit all core features — every function has UI control
2. Real-time FFmpeg progress bar parsing
3. Download queue panel with job management
4. Batch operations (download/convert)
5. Settings panel for advanced options
6. UI/UX enhancements (icons, themes, accessibility)

---

## Phase 7 — UI Tutarlılık & Kullanılabilirlik İyileştirmeleri

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

**Phase 5 (After GUI is Done) — Build & Distribution:**

1. PyInstaller spec updates with FFmpeg bundling
2. Windows/Linux/macOS build pipelines
3. GitHub Actions CI/CD setup
4. Installer testing and code signing
