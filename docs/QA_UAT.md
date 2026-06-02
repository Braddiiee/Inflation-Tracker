# User Acceptance Tests (UAT)

Personas: **Budgeter**, **Analyst**, **STEAM judge**.

| ID | Scenario | Steps | Expected | Auto test |
|----|----------|-------|----------|-----------|
| UAT-01 | Log weekly shop | Add 2+ items via entry form | Records saved; success message with ID | `test_uat_01_*` |
| UAT-02 | Time to insight | Open Dashboard after save | Basket cost & weekly change visible without extra clicks | `test_uat_02_*` |
| UAT-03 | Export for analysis | Settings → Download CSV | File opens; all columns present | `test_uat_03_*` |
| UAT-04 | Find an item | Manage Records → search "milk" | Only matching rows | `test_uat_04_*` |
| UAT-05 | Data integrity | Enter negative price | Blocked with clear error | `test_uat_05_*` |
| UAT-06 | Demo charts | Dashboard with sample data | 4 chart types render | `test_uat_06_*` |
| UAT-07 | Shrinkflation | Log 1kg then 0.5kg rice | Unit-price trend shows +12%, not −44% shelf | `test_uat_07_*` |

## Manual UAT (UI)

### UAT-M01 — Add Price Entry form

1. Open **Add Price Entry**.
2. Fill item, store, category, price, date, notes; submit.
3. **Pass:** Green success banner; fields retain or clear per design.

### UAT-M02 — Manage Records edit/delete

1. Open **Manage Records**; click **Edit** on a row; change price; **Save**.
2. Click **Delete**; confirm in dialog.
3. **Pass:** Table updates; deleted row gone.

### UAT-M03 — Dashboard filters

1. Open **Dashboard**; narrow date range in sidebar.
2. **Pass:** KPI cards and charts update; empty state if no data.

### UAT-M04 — Settings backup/restore

1. **Settings** → create backup → import CSV row → restore backup.
2. **Pass:** Import undone after restore; app still loads.

### UAT-M05 — Dark mode

1. **Settings** → Appearance → Dark.
2. Navigate all pages.
3. **Pass:** Readable contrast; no white flashes on charts.

## Sign-off

| Role | Name | Date | Pass/Fail |
|------|------|------|-----------|
| Product owner | | | |
| QA | | | |
| STEAM lead | | | |
