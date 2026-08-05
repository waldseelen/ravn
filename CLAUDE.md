# CLAUDE.md

Use this as the compact session guide. For the full workflow rules, read [AGENTS.md](AGENTS.md).

## Read Order

1. `TASKS.md`
2. `PROGRESS.md`
3. `ARCHITECTURE.md`
4. `README.md`
5. `AGENTS.md`

## Current Scope

RAVN is a cross-platform desktop + CLI media pipeline with:

- desktop workspaces for `Home`, `Download`, `Studio`, and `Library`
- shared runner-based execution for FFmpeg, yt-dlp, and aria2 flows
- queue/history/media-library coverage across desktop and CLI
- Windows, Linux, and macOS support verified by a CI test matrix (`tests.yml`)
- external tools (ffmpeg/ffprobe, yt-dlp, aria2c) **bundled into packaged builds** under
  `assets/<tool>/<platform>/` and resolved by `ravn_app/utils/bundled_tools.py`; the Settings
  "install missing tools" action is the fallback, not the primary path
- packaging: Windows is the signed release; Linux is `workflow_dispatch`-only
  (`linux-package.yml`) until verified on a real runner; macOS is tracked in `TASKS.md`
- an experimental `plugin_system.py` that is **not** part of the active packaged runtime

## Key Entry Points

- `ravn.py` (desktop GUI), `ravn_cli_entry.py` (packaged CLI entry point)
- `ravn_app/ui/main_window.py`
- `ravn_app/core/downloader.py`
- `ravn_app/core/task_manager.py`
- `ravn_app/core/database.py`
- `ravn_app/cli.py`
- `ravn_app/utils/bundled_tools.py` (external tool resolution)

## Guardrails

- Verify code before making status claims.
- Prefer shared runners for new external tool execution paths.
- Keep UI strings translation-key based.
- Update `README.md`, `ARCHITECTURE.md`, `PROGRESS.md`, and `TASKS.md` together when repo reality changes.
- Keep settings compact, themes limited to `dark` / `light`, and torrent mode semantics stable.

## Tauri Frontend Migration — Critical Guardrails

> These rules exist because previous agents repeatedly violated them. **Non-negotiable.**

### ⛔ RENK PALETİ — TEK KAYNAK: `style.css` CSS DEĞİŞKENLERİ
- **YASAK:** Tailwind renk sınıfları (`bg-slate-*`, `text-purple-*`, `bg-rose-*`, `bg-cyan-*`, `bg-teal-*`, `bg-indigo-*`, `bg-amber-*`) Vue bileşenlerinde kullanmak.
- **DOĞRU:** `var(--bg-primary)`, `var(--accent-brass)`, `var(--bg-card)` vb. CSS custom properties kullanmak.
- **DOĞRULAMA:** `grep -r "bg-slate\|bg-purple\|bg-rose\|bg-cyan\|bg-teal\|bg-indigo\|bg-amber" frontend/src/components/` → 0 sonuç.
- **NEDEN:** 6 bileşen (ConverterTab, SubtitleTab, FiltersTab, MixerTab, UtilitiesTab, QueuePanel) Tailwind renkleriyle yazıldı ve tema tutarsızlığı yarattı.

### ⛔ STUB / PLACEHOLDER / ALERT YASAĞI
- **YASAK:** `alert()`, `console.log("TODO")`, `setTimeout` mock, "Coming soon" placeholder.
- **DOĞRU:** Her buton ya gerçek API çağrısı yapar, ya da `disabled` + tooltip gösterir.
- **DOĞRULAMA:** `grep -r "alert(" frontend/src/components/` → 0 sonuç.
- **NEDEN:** 5 Studio bileşeni tamamen `alert()` stub'larıyla teslim edildi, kullanıcıya fonksiyonel gösterildi.

### ⛔ MOCK DATA YASAĞI
- **YASAK:** Statik dosya yolları (`C:/Downloads/sample_video.mkv`), sahte istatistikler, hardcoded durum rozetleri.
- **DOĞRU:** Backend API'den gerçek veri çek. API yoksa önce endpoint yaz.
- **NEDEN:** ConverterTab mock path kullanıyordu, Settings araç durumları hardcoded idi.

### ⛔ GIT İŞLEM YASAĞI
- **YASAK:** `git commit`, `git push`, `git tag` — kullanıcı açıkça istemeden YAPMA.
- **NEDEN:** Daha önce test edilmeden commit atıldı.

### ⛔ CUSTOMTKINTER REFERANS ZORUNLULUĞU
- Bir Vue bileşeni yazarken veya düzenlerken, orijinal CustomTkinter Python dosyasını **MUTLAKA** oku.
- Ezberden veya varsayımla yazma. Orijinal dosya yolları `TASKS.md` → KURAL-8'de listelenmiştir.
- **NEDEN:** Önceki portta features atlandı çünkü orijinal kod okunmadan yazıldı.

### Referans Dosya Yolları (Tauri Frontend)
- Frontend bileşenleri: `frontend/src/components/*.vue`
- Stil tanımları: `frontend/src/style.css`
- API istemcisi: `frontend/src/services/apiClient.ts`
- Pinia store: `frontend/src/stores/downloadStore.ts`
- Backend API routers: `ravn_app/api/routers/`
- Orijinal CustomTkinter UI: `ravn_app/ui/tabs/`, `ravn_app/ui/components/`
- Design tokens: `ravn_app/ui/design_tokens.py`

### Görev Takibi
Tauri Frontend Migration görev listesi `TASKS.md` → "TAURI FRONTEND MİGRASYON" bölümündedir.
9 Phase (P0–P8), ~100+ subtask. Phase sırası ve bağımlılıklar orada belgelidir.

## Verification

Primary checks:

- `pytest -q`
- `pytest -q tests/test_ui_logic.py`
- `pytest -q tests/test_ui_components.py tests/test_app_builder.py`
- `pytest -q tests/test_config_paths.py tests/test_database_manager.py`

Latest full-suite verification: `854 passed, 1 skipped` on 2026-07-26.

Quality gates (both blocking in CI): `ruff check ravn_app tests` (clean) and
`mypy ravn_app/core ravn_app/utils` (0 errors). UI-layer mypy is still being tightened — see `ROADMAP.md`.
