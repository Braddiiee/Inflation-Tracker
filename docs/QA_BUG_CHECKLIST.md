# Bug Checklist — Manual Regression

Use before STEAM demo, release, or major merge. Mark **P0** (blocker), **P1** (major), **P2** (minor), **P3** (cosmetic).

## Environment

- [ ] Python 3.10+ / 3.11 / 3.12 verified
- [ ] `pip install -r requirements.txt` succeeds
- [ ] `python -m pytest` — all tests pass
- [ ] `streamlit run app.py` starts without traceback

---

## P0 — Blockers (must be zero)

| # | Area | Check | OK | Bug ID |
|---|------|-------|----|--------|
| 1 | Startup | App loads home page | ☐ | |
| 2 | Database | `data/tracker.db` created on first use | ☐ | |
| 3 | Entry | Valid save persists after page refresh | ☐ | |
| 4 | Entry | Negative price blocked | ☐ | |
| 5 | Entry | Future date blocked | ☐ | |
| 6 | Dashboard | KPI cards show values with data | ☐ | |
| 7 | Records | Delete confirmation works | ☐ | |
| 8 | Restore | Backup restore does not corrupt app | ☐ | |

---

## P1 — Major features

### Add Price Entry

| # | Check | OK | Notes |
|---|-------|----|-------|
| 10 | All required fields validated | ☐ | |
| 11 | New category path works | ☐ | |
| 12 | Package size (qty + unit) saves correctly | ☐ | |
| 13 | Success message shows record ID | ☐ | |
| 14 | Error messages appear on invalid submit | ☐ | |

### Manage Records

| # | Check | OK | Notes |
|---|-------|----|-------|
| 20 | Search filters table | ☐ | |
| 21 | Sort columns change order | ☐ | |
| 22 | Pagination prev/next | ☐ | |
| 23 | Edit saves changes | ☐ | |
| 24 | Delete requires confirmation | ☐ | |

### Dashboard

| # | Check | OK | Notes |
|---|-------|----|-------|
| 30 | Current basket cost card | ☐ | |
| 31 | Weekly change card (%) | ☐ | |
| 32 | Monthly change card (%) | ☐ | |
| 33 | Highest / lowest inflation items | ☐ | |
| 34 | Price trend chart interactive (zoom/hover) | ☐ | |
| 35 | Basket cost chart | ☐ | |
| 36 | Store comparison chart | ☐ | |
| 37 | Inflation trend chart (2+ months data) | ☐ | |
| 38 | Recent entries table | ☐ | |
| 39 | Sidebar filters update charts | ☐ | |
| 40 | Refresh data clears cache | ☐ | |

### Settings

| # | Check | OK | Notes |
|---|-------|----|-------|
| 50 | CSV download opens in Excel/Sheets | ☐ | |
| 51 | PDF download opens in reader | ☐ | |
| 52 | CSV import template downloads | ☐ | |
| 53 | CSV import adds rows | ☐ | |
| 54 | Create backup file in `data/backups/` | ☐ | |
| 55 | Restore from backup list | ☐ | |
| 56 | Dark mode toggles on all pages | ☐ | |

---

## P2 — Minor / polish

| # | Check | OK |
|---|-------|----|
| 60 | Empty state when no data (friendly message) | ☐ |
| 61 | Long item names do not break layout | ☐ |
| 62 | Chart legends readable in dark mode | ☐ |
| 63 | Import shows row-level errors in expander | ☐ |
| 64 | Home page link to Dashboard works | ☐ |

---

## P3 — Cosmetic

| # | Check | OK |
|---|-------|----|
| 70 | Page titles and captions consistent | ☐ |
| 71 | No debug print / stack traces in UI | ☐ |
| 72 | Sidebar page order logical (0 Dashboard first) | ☐ |

---

## Security & data (MVP)

| # | Check | OK |
|---|-------|----|
| 80 | No secrets in repo (.env gitignored) | ☐ |
| 81 | SQL uses parameterized queries only | ☐ (code review) |
| 82 | Restore warns before overwrite | ☐ |

---

## Test execution log

| Date | Tester | Build/commit | Automated (`pytest`) | Manual complete | Open P0/P1 |
|------|--------|--------------|----------------------|-----------------|------------|
| | | | ☐ Pass ☐ Fail | ☐ | |

---

## Defect template

```
ID: BUG-___
Priority: P0 / P1 / P2 / P3
Area: Entry / Records / Dashboard / Settings / DB
Steps to reproduce:
1.
2.
Expected:
Actual:
Screenshot/log:
```
