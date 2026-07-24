# Contributing to RAVN

Thank you for your interest in contributing to RAVN! RAVN is a Windows-first desktop media utility built with Python and CustomTkinter.

---

## Code of Conduct

This project adheres to the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

---

## Getting Started

### Prerequisites

- **OS**: Windows 10 / 11 (64-bit)
- **Python**: 3.11, 3.12, or 3.13 (Python 3.12 recommended)
- **External Tools**: `ffmpeg` and `aria2c` in your system PATH (or downloadable via the app's tool installer).

### Local Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/waldseelen/ravn.git
   cd ravn
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. **Install locked dependencies**:
   ```bash
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Run the desktop app**:
   ```bash
   python ravn.py
   ```

5. **Run the CLI**:
   ```bash
   python -m ravn_app.cli --help
   ```

---

## Engineering Guidelines & Verification

Before submitting a Pull Request, verify your changes pass all code quality gates:

### 1. Test Suite
```bash
pytest -q
```
Ensure all tests pass and coverage does not drop below the required baseline (`--cov-fail-under=49`).

### 2. Linting & Formatting
```bash
ruff check ravn_app tests
```

### 3. Type Checking
```bash
mypy ravn_app/core ravn_app/utils
```

### 4. Code & Architecture Rules
- Keep UI composition modular: thin shell (`ravn_app/ui/main_window.py`) + focused tabs (`ravn_app/ui/tabs/`).
- Use shared runners (`ravn_app/core/runners/`) for external process calls (`ffmpeg`, `yt-dlp`, `aria2`).
- All user-facing UI text **must** be key-based using `i18n` (supported in `tr.json` and `en.json`).
- Always update documentation when repository behavior changes (`README.md`, `ARCHITECTURE.md`, `PROGRESS.md`, `TASKS.md`).

---

## Submitting Pull Requests

1. Create a feature branch off `main`: `git checkout -b feat/my-awesome-feature`.
2. Commit with descriptive messages.
3. Push to your fork and submit a PR against `main`.
4. Fill out the [Pull Request Template](.github/PULL_REQUEST_TEMPLATE.md).
