## Summary of Changes

Briefly describe what this PR does and why it is needed.

## Type of Change

- [ ] Bug fix (non-breaking change fixing an issue)
- [ ] New feature (non-breaking change adding functionality)
- [ ] Breaking change (fix or feature causing existing functionality to change)
- [ ] Code refactoring / performance improvement
- [ ] Documentation update

## Verification Checklist

Please verify the following before requesting a review:

- [ ] `pytest -q` passes cleanly with no regressions
- [ ] Coverage threshold is maintained (`--cov-fail-under=49`)
- [ ] `ruff check ravn_app tests` reports no errors
- [ ] `mypy ravn_app/core ravn_app/utils` passes
- [ ] New UI strings are key-based and added to both `tr.json` and `en.json`
- [ ] Relevant documentation updated (`README.md`, `ARCHITECTURE.md`, `PROGRESS.md`, `TASKS.md`)
