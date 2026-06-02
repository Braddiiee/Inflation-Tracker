# QA Test Plan — Grocery Inflation Tracker

## Scope

| Layer | Location | Automated |
|-------|----------|-----------|
| Validation | `src/validation.py` | `tests/test_validation.py` |
| Database / DAL | `src/database.py`, `src/repositories.py` | `tests/test_database.py`, `tests/test_repositories.py` |
| Entry | `src/entry_service.py` | `tests/test_entry_service.py` |
| Records | `src/record_service.py` | `tests/test_record_service.py` |
| Analytics | `src/data_processor.py` | `tests/test_analytics.py`, `tests/test_dashboard_metrics.py` |
| Charts | `src/charts.py` | `tests/test_charts.py` |
| Export / import / backup | `src/export/`, `src/import_data/`, `src/backup/` | `tests/test_export_backup_import.py` |
| Integration flows | Cross-module | `tests/test_integration.py` |
| UAT journeys | Business scenarios | `tests/test_uat.py` + `docs/QA_UAT.md` |
| Edge cases | Boundaries / failures | `tests/test_edge_cases.py` + `docs/QA_EDGE_CASES.md` |
| UI (Streamlit) | `*_view.py`, `pages/` | Manual (`docs/QA_BUG_CHECKLIST.md`) |

## Run commands

```powershell
cd "c:\Users\HpVpro\Desktop\Inflation Tracker"
pip install -r requirements.txt -r requirements-dev.txt

# Full suite
python -m pytest

# By category
python -m pytest -m unit
python -m pytest -m integration
python -m pytest -m uat
python -m pytest -m edge

# With coverage (optional)
python -m pytest --cov=src --cov-report=term-missing
```

## Pass criteria (MVP)

- All automated tests pass.
- UAT scenarios UAT-01 through UAT-07 pass (`pytest -m uat`).
- Manual checklist completed with no **P0/P1** open defects.
- Goal metrics: zero critical input errors; basket chart with 4+ weeks of demo data; dashboard KPIs load without error.

## Related documents

- [QA_UAT.md](QA_UAT.md) — acceptance scenarios
- [QA_EDGE_CASES.md](QA_EDGE_CASES.md) — edge-case catalog
- [QA_BUG_CHECKLIST.md](QA_BUG_CHECKLIST.md) — manual regression checklist
