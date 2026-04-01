# WMS Feature Adoption Checker

A Playwright-based scraper that checks WMS frontend configuration settings across warehouses and markets, outputting a colour-coded Excel report.

---

## What it does

1. Logs into Shopee WMS via Google SSO (first run only — session is saved)
2. Iterates over every configured warehouse per market
3. Switches warehouse context via the UI dropdown
4. Reads the Yes/No value for each configured feature signal
5. Saves results to `wms_adoption_results.xlsx`

---

## Quickstart

### 1. Install dependencies

```bash
pip3 install playwright openpyxl
playwright install chromium
```

### 2. Configure targets

Edit the `CONFIG` section at the top of `wms_adoption_checker.py`:

```python
FEATURES = [
    {
        "feature": "MTO Picking Task Generation",
        "signal": "Split MTO into multiple picking tasks",   # exact label on the page
        "url": "/v2/rulecenter/pickingrule/mtoPickingRule",
    },
    # Add more features here
]

MARKETS = {
    "PH": ["PHA", "PHB", "PHD", ...],
    # "MY": ["MYA", ...],
}
```

### 3. Run

```bash
python3 wms_adoption_checker.py
```

**First run:** a browser window opens → log in via Google SSO → press Enter in the terminal. The session is saved to `wms_session.json` for all future runs.

**Subsequent runs:** no login needed, session is reused automatically.

---

## Output

| File | Description |
|------|-------------|
| `wms_adoption_results.xlsx` | Per-warehouse results with green/red formatting |
| `wms_session.json` | Saved browser session (gitignored, do not share) |

### Excel sheets

- **WMS Adoption** — one row per warehouse × feature, colour-coded Yes/No
- **Summary by Feature** — adoption count and % per feature

---

## Safety

The script is **read-only by design**:

- All `PUT`, `DELETE`, `PATCH` requests to `wms.ssc.shopee.ph` are aborted at the network level
- `POST` requests to paths containing write verbs (`create`, `update`, `delete`, `save`, etc.) are aborted
- Only `set_user_setting` POST is allowed — this is the warehouse context switch, not a config change

---

## Extending

### Add a new feature

```python
FEATURES = [
    ...,
    {
        "feature": "My New Feature",
        "signal": "Exact label text shown before Yes/No on the page",
        "url": "/v2/rulecenter/someOtherPage",
    },
]
```

### Add a new market

```python
MARKETS = {
    "PH": [...],
    "MY": ["MYA", "MYB", "MYC"],   # add warehouse codes here
}
```

The script will automatically iterate all markets × warehouses × features.

---

## Roadmap

- [ ] Admin-level configuration pages (non-warehouse scope)
- [ ] Multi-market support (MY, SG, TH, ...)
- [ ] Scheduled runs + Slack/email diff alerts
- [ ] Delta report (highlight changes vs previous run)

---

## Requirements

- Python 3.9+
- `playwright` — browser automation
- `openpyxl` — Excel output
- Access to `wms.ssc.shopee.ph` (internal network / VPN)
