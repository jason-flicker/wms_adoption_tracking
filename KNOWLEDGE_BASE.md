# WMS Feature Adoption Checker — Knowledge Base

A developer reading this file should have everything needed to write a new checker without consulting any other document.

---

## Overview

The adoption checker scans WMS and admin portal pages to determine whether each warehouse has adopted a given feature, based on predefined signal criteria. It operates in **read-only mode at all times** — it must never click toggles, submit forms, or modify any configuration.

---

## Architecture

```
adoption_tracker/
├── runner.py          # Engine — never edit
├── features.py        # Feature + market config — edited by PM/BPM team
├── checkers/          # One .py file per feature (auto-discovered)
│   ├── dynamic_wave_rule.py
│   ├── picking_while_sorting.py
│   ├── mto_exclusion.py
│   ├── dynamic_replenishment.py
│   └── ...
└── output/
    └── wms_adoption_results.xlsx
```

**Runner responsibilities:**
- Auto-discovers all `*.py` files in `checkers/` (skips `_*.py`)
- Validates that each checker exposes the required interface
- Manages all navigation and warehouse switching for `wms_frontend` checkers
- Handles login detection and session pre-flight checks
- Writes results to Excel

**To add a feature:** drop a new file in `checkers/`, add an entry to `FEATURES` in `features.py`. The runner picks it up automatically.

**To add a market:** add it to `MARKETS` in `features.py` (leave the warehouse list empty for auto-discovery), then add the market code to each relevant feature's `"markets"` list.

---

## Checker Interface Contract

Every checker file **must** expose these four attributes:

| Attribute | Type | Description |
|---|---|---|
| `FEATURE_NAME` | `str` | Must exactly match the key in `features.py` `FEATURES` list |
| `CHECK_TYPE` | `str` | `"wms_frontend"` or `"admin_portal"` |
| `SIGNAL` | `str` | Human-readable description of what is being measured |
| `check` | `async def` | The check function (see signature below) |

### `check` function signature

```python
async def check(page, warehouse: str, market: str, params: dict) -> tuple[str, bool | None]:
    ...
```

**Returns:** `(signal_value: str, adopted: bool | None)`
- `True` → adopted
- `False` → not adopted
- `None` → error (signal_value should describe what went wrong)

**Important:** For `wms_frontend` checkers, the runner has **already navigated to the correct URL and switched to the correct warehouse** before calling `check()`. The checker should call `page.wait_for_load_state("networkidle")` at the start, then read the page state.

### Minimal checker template

```python
FEATURE_NAME = "My Feature Name"
CHECK_TYPE   = "wms_frontend"
SIGNAL       = "Human-readable description of signal"

async def check(page, warehouse: str, market: str, params: dict) -> tuple:
    try:
        await page.wait_for_load_state("networkidle", timeout=15000)
        # ... read the page ...
        return "signal_value_string", True  # or False or None
    except Exception as e:
        return f"error: {e}", None
```

---

## Configuration (`features.py`)

### `MARKETS` dict

```python
MARKETS = {
    "PH": ["PHB", "PHIXP"],   # hardcoded
    "SG": [],                  # empty = auto-discovered from WMS dropdown
}
```

Auto-discovery reads warehouse codes from the `li.ssc-option` elements in the WMS sidebar warehouse selector dropdown.

### `FEATURES` list

Each entry:

```python
{
    "feature": "Feature Name",          # must match FEATURE_NAME in checker
    "markets": ["PH", "SG"],            # market codes to check
    "params": {                         # passed directly to checker.check()
        "url_path": "/some/path",       # required for wms_frontend
        # ... any other checker-specific params ...
    },
}
```

`params` keys are not interpreted by the runner — they are passed as-is to the checker. Each checker documents the params it expects.

### WMS URL mapping

The runner constructs the full URL as `WMS_BASE_URLS[market] + params["url_path"]`.

| Market | Base URL |
|---|---|
| ID | `https://wms.ssc.shopee.co.id/v2` |
| MY | `https://wms.ssc.shopee.com.my/v2` |
| TH | `https://wms.ssc.shopee.co.th/v2` |
| PH | `https://wms.ssc.shopee.ph/v2` |
| SG | `https://wms.ssc.shopee.sg/v2` |
| VN | `https://wms.ssc.shopee.vn/v2` |
| TW | `https://wms.ssc.shopee.tw/v2` |
| BR | `https://wms.ssc.shopee.com.br/v2` |

---

## Check Types

### Type 1 — `admin_portal`

- URL pattern: `https://ops.ssc.*`
- Each page shows settings for **all warehouses at once** — no per-warehouse navigation needed
- Adoption logic (evaluate in order):
  1. If the **region** is configured correctly → all warehouses in that region are adopted
  2. Else if an **individual warehouse** is configured correctly → that warehouse is adopted
  3. Otherwise → not adopted

### Type 2 — `wms_frontend`

- URL pattern: `https://wms.ssc.*`
- The runner visits each market's WMS portal and checks each warehouse individually
- The runner owns navigation and warehouse switching; the checker just reads the page

---

## WMS Login Handling Rules

WMS uses per-market sessions. Logging into one market does **not** grant access to another. Each domain maintains its own independent session cookie.

### Rule 1 — Pre-run session check (mandatory)
Before any scan begins, the runner navigates to each required market's WMS base URL and verifies the session is active. This applies to **every** market in any checker's `markets` list.

### Rule 2 — Detect login by UI element, not URL
Do **not** rely on the page URL to determine if login is complete. The post-OAuth redirect can land on a WMS URL while the app has not rendered. Instead, poll for `.ssc-select` (the WMS warehouse dropdown) — it only appears once the user is authenticated and the application shell has loaded.

```python
# Login is complete when:
document.querySelector('.ssc-select, [class*="ssc-select"]') !== null
# OR
document.querySelector('.ant-layout-sider') !== null
```

### Rule 3 — Never block on `input()` for login
The runner polls for `.ssc-select` and auto-continues when it appears. No terminal keypress required.

### Rule 4 — Mid-run session expiry
If `page.goto()` redirects to a login page during a scan, apply the same `.ssc-select` polling before retrying navigation.

### Rule 5 — Admin portal session is separate
`ops.ssc.shopeemobile.com` has its own independent session. If any checker has `CHECK_TYPE = "admin_portal"`, the pre-run check must also verify admin portal access. Login detection for the admin portal uses **URL inspection** (wait for URL to leave the login domain) — the admin portal does not use `.ssc-select`.

---

## SSC Component DOM Patterns

Discovered via live DevTools inspection. Apply to all checkers targeting WMS pages.

### 8.1 Dropdown Options — `ssc-select`

- Options render as **`.ssc-option`** elements (NOT `.ssc-table-header-column-container`)
- Options are **dynamically created** when the dropdown opens — they do not exist in the DOM before clicking
- After clicking an `ssc-select`, wait ~600ms then query `.ssc-option`

```js
// Pattern: click filter label's grandparent container's ssc-select, then find option
const label = Array.from(document.querySelectorAll('.ssc-form-item-label'))
    .find(el => /Label Text/i.test(el.innerText.trim()));
const container = label.parentElement?.parentElement;
const sel = container.querySelector('[class*="ssc-select"]');
sel.click();
// wait 600ms
const opts = Array.from(document.querySelectorAll('.ssc-option'));
const target = opts.find(el => el.innerText.trim() === 'Exact Option Text');
target.click();
```

- Active/highlighted option: `ssc-option ssc-option-highlighted`
- Selected option: `ssc-option ssc-option-selected`
- Do **not** use `window.__pickBefore` snapshot approach — unnecessary for `.ssc-option`

### 8.2 Table Rows and Status Toggles — `ssc-react` table

- Table cells use class **`ssc-react-rc-table-cell`** (NOT `ant-table-cell` or `td`)
- **Row 1 is always a hidden placeholder** with `height:0` — skip it when counting data rows
- Real data rows have a numeric priority value in `td` index 1

Status toggle classes:
```
Active  : <span class="ssc-react-switch-wrapper ssc-react-switch-wrapper-checked"><input value="1">
Inactive: <span class="ssc-react-switch-wrapper"><input value="0">
```

```js
// Detect any active row
document.querySelector('.ssc-react-switch-wrapper-checked')

// Count data rows (skip placeholder)
const dataRows = rows.filter(r => {
    const cells = r.querySelectorAll('td');
    return cells.length > 1 && /^\d+$/.test((cells[1]?.innerText || '').trim());
});
```

Adopted if `activeCount >= 1`.

### 8.3 Date Range Picker — `ssc-date-picker-range`

- Two plain `<input>` elements inside `.ssc-date-picker-range`
- Scoped by `data-for` attribute, e.g. `data-for="create_time_gt+create_time_lt"`
- Input format: `YYYY/MM/DD HH:mm:ss`

```python
# Playwright pattern — triple_click() does NOT exist on Locator; use click(click_count=3)
date_container = '[data-for="create_time_gt+create_time_lt"]'
start_input = page.locator(f'{date_container} input').first
end_input   = page.locator(f'{date_container} input').last

await start_input.click(click_count=3)
await start_input.type(start_str)
await page.keyboard.press('Tab')       # move to end date input

await end_input.click(click_count=3)
await end_input.type(end_str)
await page.keyboard.press('Escape')    # close calendar popup if opened
```

### 8.4 Vue Toggle Switches — `ssc-switch` (allocate rule pages)

Some WMS pages use the **Vue** `ssc-switch` component instead of the React `ssc-react-switch-wrapper`.

```
Active  : class="ssc-switch rule-switch"                     (no inactive class)
Inactive: class="ssc-switch rule-switch ssc-switch-inactive"
```

- `aria-checked` is `null` — **do not rely on it**
- Scope using `.allocate-exclusion-rule-table-container` rather than walking up from headings
- Section heading class: `.mt-sub-rule-title` (leaf DIV); its grandparent holds the switches

```js
// Pattern (mto_exclusion.py)
const container = document.querySelector('.allocate-exclusion-rule-table-container');
const all    = container.querySelectorAll('.ssc-switch.rule-switch');
const active = Array.from(all).filter(el => !el.classList.contains('ssc-switch-inactive'));
// Adopted if active.length >= 1
```

### Toggle Pattern Summary

| Class / Selector | Component type | Example page |
|---|---|---|
| `.ssc-react-switch-wrapper-checked` | React table toggle | Dynamic Wave Rule |
| `.ssc-switch.rule-switch` without `.ssc-switch-inactive` | Vue allocate rule toggle | MTO Allocate Rule |
| `.ssc-option` (dynamic, post-click) | Filter dropdown option | Picking Method filter |

---

## Error Handling Rules

| Situation | Signal value | `adopted` |
|---|---|---|
| Page requires login / session expired | Stop and surface to user | — |
| Signal element not found | `element_not_found` | `None` |
| Page fails to load | `page_load_failed` | `None` |
| Signal value ambiguous | `unexpected_value: <raw>` | `None` |

- Set `adopted = None` for all error conditions (maps to "Error" in output)
- Continue to the next warehouse/feature after logging — do not stop the entire scan

---

## Output Format

Results are written to `adoption_tracker/output/wms_adoption_results.xlsx` with two sheets:

**Detail sheet** — one row per warehouse per feature:

| Column | Description |
|---|---|
| Market | Market code (e.g. `PH`) |
| Warehouse | Warehouse ID |
| Feature | Feature name |
| Signal | What was checked |
| Signal Value | Actual value observed |
| Adopted | `Yes` / `No` / `Error` |
| Checked At | UTC timestamp `YYYY-MM-DDTHH:MM:SSZ` |

**Summary sheet** — one row per (feature, market) pair with totals and adoption %.

---

## Safety Guard

The runner blocks all network mutations on WMS and admin portal hosts via a Playwright route interceptor:

- Blocked: `PUT`, `DELETE`, `PATCH` to guarded hosts
- Blocked: `POST` to paths containing write-like verbs (`create`, `update`, `delete`, `remove`, `save`, `submit`, `edit`, `modify`, `add_`, `batch_update`, `upload`)
- Allowed: `POST` to `set_user_setting` (warehouse-switch API)

Hard rules for checkers:
- Never edit any input field or submit any form
- Never confirm any dialog or prompt
- If unsure whether an action modifies data, stop and report
- Permitted actions: navigate to URLs, scroll, read visible page content
