# Security Policy

## Supported Versions

RAVN actively maintains security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0.0 | :x:                |

## Reporting a Vulnerability

The RAVN team takes security vulnerabilities seriously. If you discover a security flaw or vulnerability in RAVN, please **do not** open a public issue.

Instead, please report vulnerabilities via one of the following methods:

- **GitHub Security Advisory** (preferred): Use the "Report a vulnerability" button under the
  **Security** tab of the [GitHub repository](https://github.com/waldseelen/ravn/security/advisories/new).
- **Private Disclosure**: Contact the maintainer directly via the email on the
  [GitHub profile](https://github.com/waldseelen).

### What to Include in Your Report

To help us triage and respond quickly, please include:
- A detailed description of the issue.
- Steps to reproduce or a Proof of Concept (PoC).
- Impact assessment (e.g., local execution risk, log sensitive data exposure, etc.).
- Proposed fix or mitigation (if available).

### Response Expectations

- **Initial Response**: Within 48 hours.
- **Status Update**: Within 7 business days.
- **Public Disclosure**: Coordinated after a patch is released to all supported channels.

## Scope

In scope:

- The RAVN desktop application and CLI (`ravn_app/`)
- The packaged Windows build and its release pipeline (`ravn.spec`, `build.ps1`,
  `.github/workflows/windows-release.yml`)

Out of scope:

- Vulnerabilities in third-party dependencies (`yt-dlp`, `ffmpeg`, `aria2c`, etc.) — please report
  those upstream. If a dependency vulnerability specifically affects how RAVN uses it (e.g. an
  unsafe invocation pattern), that is in scope here.
- `ravn_app/core/plugin_system.py` — experimental and not part of the active packaged runtime (see
  [ARCHITECTURE.md](ARCHITECTURE.md)).
