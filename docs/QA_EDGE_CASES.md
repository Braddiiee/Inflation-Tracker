# Edge Cases Catalog

## Input validation

| ID | Case | Expected | Test |
|----|------|----------|------|
| E-01 | Empty item/store/category name | ValidationError | `test_validation` |
| E-02 | Price = 0 or negative | Rejected | `test_database`, `test_uat_05` |
| E-03 | Future date | Rejected | `test_database` |
| E-04 | Invalid unit (e.g. "lb") | Rejected | `test_validation` |
| E-05 | Notes > 500 chars | Rejected | `test_validation` |
| E-06 | Non-numeric price | Rejected | `test_validation` |
| E-07 | Unicode names (Café, accents) | Stored and searchable | `test_edge_cases` |

## Data & analytics

| ID | Case | Expected | Test |
|----|------|----------|------|
| E-10 | Empty database | KPIs show "—"; charts show empty state | `test_edge_cases` |
| E-11 | Single observation | No % increase/decrease extremes | `test_edge_cases` |
| E-12 | One calendar month only | No MoM inflation row | `test_edge_cases` |
| E-13 | % change when old price = 0 | Returns None | `test_edge_cases` |
| E-14 | Tiny quantity (0.001 g) | Unit price computed correctly | `test_edge_cases` |
| E-15 | Shrinkflation (500→280, qty 1→0.5) | Unit price +12% not shelf −44% | `test_uat_07` |
| E-16 | Filter range with no rows | Empty charts, warning in UI | Manual |

## Records & pagination

| ID | Case | Expected | Test |
|----|------|----------|------|
| E-20 | Page number > total pages | Clamps to last page | `test_edge_cases` |
| E-23 | page_size=1 (valid option) | Returns single row per page | `test_record_service` |
| E-21 | Search with no hits | Empty table | `test_edge_cases` |
| E-22 | Product exists under different category | ValidationError on import/save | `test_entry_service` |

## Import / export / backup

| ID | Case | Expected | Test |
|----|------|----------|------|
| E-30 | CSV missing required columns | Error list; 0 imports | `test_edge_cases` |
| E-31 | Empty CSV (headers only) | Error message | `test_edge_cases` |
| E-32 | Backup when DB missing | DatabaseError | `test_edge_cases` |
| E-33 | PDF with empty DB | Valid PDF, no crash | `test_edge_cases` |
| E-34 | Restore without safety copy flag | Still works in tests | `test_export_backup_import` |

## Concurrency / environment

| ID | Case | Expected | Notes |
|----|------|----------|-------|
| E-40 | Restore while app running | Engine reset; refresh data | Call **Refresh data** on Dashboard |
| E-41 | Very large CSV import (1000+ rows) | Performance acceptable | Manual / load test |
| E-42 | Missing `data/` folder | Created on init | `init_db()` |

## Streamlit UI (manual)

| ID | Case | Expected |
|----|------|----------|
| E-50 | Double-click Save rapidly | No duplicate rows or clear error |
| E-51 | Browser back button | App recovers |
| E-52 | Sidebar filter: start > end | Error message, no crash |
