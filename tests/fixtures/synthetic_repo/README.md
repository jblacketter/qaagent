Synthetic repository used for Sprint 1 collector tests.

Usage:
```bash
python tests/fixtures/synthetic_repo/setup_git_history.py
```
This will initialize a git repository with a 120-day-old initial commit and 14 churn commits touching `src/auth/session.py` within the last 90 days.
