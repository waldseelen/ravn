# RAVN — Project Task Board

All development tasks organized by priority and status.

---

## Status Legend

- `[ ]` — Not started
- `[~]` — In progress
- `[x]` — Done
- `[!]` — Blocked

---

## Summary

**Completed:** Phase 1 (Stabilization & Core Rewrite), Phase 2 (High Priority Features), Phase 3 (Medium Priority Features), Phase 4A (Core GUI Completeness), and Phase 4B (UI/UX Pro Max Enhancements) — 367 tests passing, 1 skipped.

**Active Backlog:** Phase 5 (Build, Package & Distribution) remains open.

-PHASE 1-2-3 COMPLETED- find next [] tasks
















## Phase 4 — GUI Polish & Full Controllability

Every function accessible and controllable via GUI. Better frontend, full control, no CLI-only features, visual enhancements.

### 4A — Core GUI Completeness [x]

Full UI coverage and queue management.

- [x] **[GUI-01]** Audit all core features — ensure every function has UI control
- [x] **[GUI-02]** Real-time FFmpeg progress bar (parse `-progress pipe:1`)
- [x] **[GUI-03]** Download queue panel — show queued, active, completed jobs
- [x] **[GUI-04]** Per-job cancel button in queue panel
- [x] **[GUI-05]** Batch download — accept multiple URLs
- [x] **[GUI-06]** Batch convert — select multiple files with one profile
- [x] **[GUI-07]** Settings panel for advanced FFmpeg options (CRF, preset, bitrate)
- [x] **[GUI-08]** Output directory selector with "remember last used"
- [x] **[GUI-09]** Keyboard shortcuts (Ctrl+D, Ctrl+O, Ctrl+Q, etc.)
- [x] **[GUI-10]** "Open output folder" button after successful operation

### 4B — UI/UX Pro Max Enhancements [x]

Design system, accessibility, and visual polish. (Design tokens and colors defined; micro-interactions implemented via AnimationManager.)

- [x] **[UX-01]** Visual Design & Theme — consistent corner radius, dark mode colors, semantic palette
- [x] **[UX-02]** Icons — replace emojis with vector icons (Lucide or similar)
- [x] **[UX-03]** Interaction & Feedback — disabled buttons during operations, spinner animations
- [x] **[UX-04]** Drag & Drop Visualization — dashed borders, color changes on hover
- [x] **[UX-05]** Layout & Spacing — standardize padding/margin to 4px or 8px rhythm
- [x] **[UX-06]** Forms & Accessibility — persistent labels (not placeholders), proper labeling
- [x] **[UX-07]** Error Placement — show errors near problematic inputs (not pop-ups)
- [x] **[UX-08]** Typography Hierarchy — consistent sizing and color contrast (≥4.5:1)
- [x] **[UX-09]** Navigation — tab icons + text, clear active state

**Dependencies:** Core GUI completeness (4A).

---

























## Phase 4C — UI Polish & Micro-interactions (Nordic Brand Theme)

Smooth transitions, micro-interactions, real-time feedback, and RAVN brand-consistent visual polish. Minimal animations that enhance usability without being distracting. Theme: Nordic kahverengi/beige minimalism with accent highlights.

### 4C.1 — Brand Color Palette Update [  ]

Align design system with RAVN brand (Nordic kahverengi + minimal beige).

- [ ] **[BRD-01]** Update `design_tokens.py` — Add brand-primary kahverengi (#3D3230 or similar) as accent
- [ ] **[BRD-02]** Define secondary accent — light beige (#D4C5B9 or warm gray)
- [ ] **[BRD-03]** Replace blue accent (#3b82f6) → kahverengi for consistency
- [ ] **[BRD-04]** Dark mode backgrounds — Keep #141414 but adjust surface colors for kahverengi harmony
- [ ] **[BRD-05]** Success/error/warning — Maintain semantic colors but test contrast with new palette
- [ ] **[BRD-06]** Hover state color — Use kahverengi-derived lighter shade for hover (not blue)

**Output:** Updated `design_tokens.py` with Nordic theme fully integrated.

### 4C.2 — Icon System & Placement [  ]

Strategically place vector icons (not emojis) for clarity and brand consistency.

**Navigation & Tabs:**
- [ ] **[ICN-01]** Download tab — ⬇ → minimize icon or custom raven icon (top-left tab)
- [ ] **[ICN-02]** Converter tab — ⇄ → gear/convert icon (second tab)
- [ ] **[ICN-03]** Subtitle tab — ≡ → subtitle/speech icon (third tab)
- [ ] **[ICN-04]** History tab — ◷ → history/clock icon (fourth tab)
- [ ] **[ICN-05]** Settings tab — ⚙ → settings/cog icon (fifth tab)
- [ ] **[ICN-06]** Queue panel — ☰ → queue/list icon (header or left sidebar)

**Action Buttons:**
- [ ] **[ICN-07]** Download button — Large + kahverengi icon indicator
- [ ] **[ICN-08]** Convert button — Process/arrow icon
- [ ] **[ICN-09]** Browse/Select button — Folder icon
- [ ] **[ICN-10]** Cancel/Stop button — X or stop icon in red/error color
- [ ] **[ICN-11]** Retry button — Clockwise arrow/refresh icon

**Status Indicators:**
- [ ] **[ICN-12]** Queued status — Purple hourglass or circle outline
- [ ] **[ICN-13]** Running status — Animated spinner (2-3 rot/sec)
- [ ] **[ICN-14]** Success status — Green checkmark (static, 150ms slide-in)
- [ ] **[ICN-15]** Error status — Red X or exclamation (pulsing red)
- [ ] **[ICN-16]** Paused status — Pause symbol (gray)

**Form & Input:**
- [ ] **[ICN-17]** URL input prefix icon — Link/chain icon (left of input)
- [ ] **[ICN-18]** Quality selector prefix — Video/quality icon
- [ ] **[ICN-19]** Format selector prefix — File type icon
- [ ] **[ICN-20]** Error indicator — Exclamation triangle (red, right of field)
- [ ] **[ICN-21]** Success indicator — Green checkmark (right of field, animated)
- [ ] **[ICN-22]** Clear/Reset button — Trash or X icon (muted gray)

**Implementation:** Use Lucide icon library (SVG) or custom Raven vector assets.

### 4C.3 — Smooth State Transitions [  ]

Smooth visual feedback for all interactive elements (150-250ms easing).

- [ ] **[POL-01]** Button press states — scale (0.95–1.0) + kahverengi glow on click
- [ ] **[POL-02]** Input field focus ring — animated kahverengi border (gray → brand kahverengi, 150ms)
- [ ] **[POL-03]** Hover states — subtle beige background shift + opacity (100ms ease-out)
- [ ] **[POL-04]** Tab switching — crossfade between tab content (150ms, no flicker)
- [ ] **[POL-05]** Modal open/close — scale + fade animation (150-200ms, centered)
- [ ] **[POL-06]** Dropdown expand/collapse — smooth height transition + kahverengi accent line
- [ ] **[POL-07]** Progress bar fill — smooth linear fill (no jumps) + color pulse on 100%
- [ ] **[POL-08]** Disabled state clarity — reduced opacity (0.5) + desaturated kahverengi

**Implementation:** CustomTkinter animation loop using `after()` and easing functions. All transitions use kahverengi accent color.

### 4C.4 — Loading & Operational Feedback [  ]

Real-time visual feedback during async operations with brand consistency.

- [ ] **[POL-09]** Animated spinner — kahverengi rotating icon (2-3 rotations/sec) during download/convert
- [ ] **[POL-10]** Progress bar — kahverengi fill color + beige background (smooth 60fps updates)
- [ ] **[POL-11]** Queue item entrance — slide-in from top + kahverengi accent bar (150ms)
- [ ] **[POL-12]** Job status badges — color-coded icons (purple queued, orange running, green done)
- [ ] **[POL-13]** "Processing..." — animated kahverengi icon + "Downloading..." text with ellipsis
- [ ] **[POL-14]** Success feedback — brief green flash + checkmark animation (300ms total)
- [ ] **[POL-15]** Completion sound/visual — Subtle kahverengi pulse + success checkmark

**Implementation:** Use `ctk.CTkProgressBar` with kahverengi color; custom spinner widget.

### 4C.5 — Error & Form Feedback [  ]

Inline, contextual feedback without disruption. Brand-consistent error messaging.

- [ ] **[POL-16]** Inline error messages — red icon + text below input (color fade-in, 150ms)
- [ ] **[POL-17]** Input validation feedback — real-time (on blur, not keystroke)
- [ ] **[POL-18]** Error recovery affordance — "Retry" or "Edit" hint with icon near error
- [ ] **[POL-19]** Form field error state — red left border indicator + icon (no full red)
- [ ] **[POL-20]** Success toast — slide-in from top-right, green checkmark + "Success" text (3s auto-dismiss)
- [ ] **[POL-21]** Warning toast — amber/orange warning icon + clear message (4s auto-dismiss)

**Implementation:** Inline `ctk.CTkLabel` with icon + color animation; custom toast widget.

### 4C.6 — Visual Polish & Consistency [  ]

Refinements that improve perceived quality and brand alignment.

- [ ] **[POL-22]** Consistent corner radius — 8px for cards, 6px for buttons/inputs (soft Nordic feel)
- [ ] **[POL-23]** Focus ring visibility — 2px kahverengi ring on all interactive elements
- [ ] **[POL-24]** Smooth color transitions — all state changes use easing (not instant)
- [ ] **[POL-25]** Empty state messaging — clear text + action icon (e.g., folder icon for "No files")
- [ ] **[POL-26]** Loading skeleton — beige placeholder cards with subtle shimmer
- [ ] **[POL-27]** Cursor feedback — pointer cursor on buttons + icons, text cursor on inputs
- [ ] **[POL-28]** Drag & drop refinement — animated kahverengi dashed border on target zone
- [ ] **[POL-29]** Scroll smoothness — smooth scrolling, no jank in queue/history
- [ ] **[POL-30]** Brand consistency check — all UI elements use kahverengi/beige (not blue)

**Implementation:** `ctk.CTkCanvas` for custom effects; frame-based animation loop.

### 4C.7 — Accessibility & Motor Control [  ]

Ensure micro-interactions don't harm accessibility.

- [ ] **[POL-31]** Respect reduced-motion — disable animations if system preference detected
- [ ] **[POL-32]** Keyboard navigation — all animations preserve tab order + focus visibility
- [ ] **[POL-33]** Animation cancellation — allow user to interrupt long operations (click to stop)
- [ ] **[POL-34]** Tooltip on hover — explain button actions with icons (300ms delay)
- [ ] **[POL-35]** Screen reader support — icon labels + descriptive aria-labels

**Implementation:** Platform detection for reduced-motion; focus management during transitions.

**Dependencies:** Phase 4B (design tokens, colors, icons). Requires BRD-01 to BRD-06 complete before POL-* items.

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

**Phase 5 (After GUI is Done) — Build & Distribution:**
1. PyInstaller spec updates with FFmpeg bundling
2. Windows/Linux/macOS build pipelines
3. GitHub Actions CI/CD setup
4. Installer testing and code signing
