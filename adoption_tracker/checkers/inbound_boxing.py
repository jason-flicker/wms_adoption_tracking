"""
Checker: Inbound Boxing
Admin portal check — Non_QC_Item_Putaway_Directly = 1.

Adoption logic (per KB):
  1. If the market region appears configured with target_value → all warehouses adopted.
  2. Else check each warehouse individually.

Results are cached per (market, url) to avoid re-fetching the page for every warehouse.
"""
import re

FEATURE_NAME = "Inbound Boxing"
CHECK_TYPE   = "admin_portal"
SIGNAL       = "Non_QC_Item_Putaway_Directly = 1"

# Cache: (market, url) -> page_text
# Populated on first call per market; read-only for subsequent calls.
_cache: dict = {}


async def check(page, warehouse: str, market: str, params: dict) -> tuple:
    results = []
    for sub in params.get("checks", []):
        url    = sub["url"]
        key    = sub["key"]
        target = sub["target_value"]

        cache_key = (market, url)
        if cache_key not in _cache:
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(1000)
                if "login" in page.url.lower() or "sso" in page.url.lower():
                    print(f"\n⚠️  Admin portal login required. Log in, then press Enter.")
                    input()
                    await page.goto(url, wait_until="networkidle", timeout=30000)
                _cache[cache_key] = await page.evaluate("document.body.innerText")
            except Exception as e:
                return f"page_load_failed: {e}", None

        text = _cache[cache_key]
        adopted = _is_adopted(text, market, warehouse, target)
        label   = f"{key}={target}" if adopted else f"{key}!={target}"
        results.append((label, adopted))

    all_pass = all(r[1] for r in results)
    summary  = " & ".join(r[0] for r in results)
    return summary, all_pass


def _is_adopted(text: str, market: str, warehouse: str, target: str) -> bool:
    """
    Check region-level first, then warehouse-level.
    Looks for the market/warehouse code appearing near the target value on the same line.
    """
    # Region-level: any line containing the market code and target value
    for line in text.splitlines():
        if re.search(rf"\b{re.escape(market)}\b", line, re.IGNORECASE):
            if re.search(rf"\b{re.escape(target)}\b", line):
                return True
    # Warehouse-level
    for line in text.splitlines():
        if re.search(rf"\b{re.escape(warehouse)}\b", line, re.IGNORECASE):
            if re.search(rf"\b{re.escape(target)}\b", line):
                return True
    return False
