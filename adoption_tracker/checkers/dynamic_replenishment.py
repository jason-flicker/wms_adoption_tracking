"""
Checker: Dynamic Replenishment
Adopted if there are orders from "Replenishment Demand Pool" with Create Time
within the last N days.

NOTE: Applying the "Source from" dropdown filter requires knowing the exact
      filter UI structure for this page. Current implementation scans visible
      page text for the filter_value keyword and recent dates.
      Update once the page UI is confirmed (see TODO below).
"""
import datetime
import re

FEATURE_NAME = "Dynamic Replenishment"
CHECK_TYPE   = "wms_frontend"
SIGNAL       = "Orders from Replenishment Demand Pool in last 7 days"


async def check(page, warehouse: str, market: str, params: dict) -> tuple:
    filter_value = params.get("filter_value", "Replenishment Demand Pool")
    days         = params.get("days", 7)
    try:
        await page.wait_for_load_state("networkidle", timeout=15000)

        # TODO: click the "Source from" filter dropdown, select filter_value,
        # then read the resulting table rows with their Create Time dates.
        # For now, check if the keyword appears anywhere on the page.
        text = await page.evaluate("document.body.innerText")

        if filter_value.lower() not in text.lower():
            return "replenishment_pool_not_found", None

        # Look for date strings in YYYY-MM-DD or DD/MM/YYYY format within the last N days
        cutoff = datetime.date.today() - datetime.timedelta(days=days)
        date_patterns = [
            r"(\d{4}-\d{2}-\d{2})",   # YYYY-MM-DD
            r"(\d{2}/\d{2}/\d{4})",   # DD/MM/YYYY
        ]
        found_recent = False
        for pat in date_patterns:
            for m in re.finditer(pat, text):
                ds = m.group(1)
                try:
                    if "-" in ds:
                        d = datetime.date.fromisoformat(ds)
                    else:
                        parts = ds.split("/")
                        d = datetime.date(int(parts[2]), int(parts[1]), int(parts[0]))
                    if d >= cutoff:
                        found_recent = True
                        break
                except ValueError:
                    continue
            if found_recent:
                break

        if found_recent:
            return f"recent_order_found_in_{days}d", True
        return "filter_check_not_implemented", None

    except Exception as e:
        return f"error: {e}", None
