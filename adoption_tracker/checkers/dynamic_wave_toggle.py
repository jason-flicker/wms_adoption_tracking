"""
Checker: Dynamic Wave Toggle
Admin portal check — ALL three keys must equal 1:
  wave_dynamic_wave_task_enable = 1
  wave_algorithm_switch = 1
  pre_allocate_zone_inventory = 1

Results cached per (market, url). Adopted only if all three pass (AND logic).
"""
import re

FEATURE_NAME = "Dynamic Wave Toggle"
CHECK_TYPE   = "admin_portal"
SIGNAL       = "wave_dynamic_wave_task_enable=1 AND wave_algorithm_switch=1 AND pre_allocate_zone_inventory=1"

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

        text    = _cache[cache_key]
        adopted = _is_adopted(text, market, warehouse, target)
        label   = f"{key}={target}" if adopted else f"{key}!={target}"
        results.append((label, adopted))

    all_pass = all(r[1] for r in results)
    summary  = " & ".join(r[0] for r in results)
    return summary, all_pass


def _is_adopted(text: str, market: str, warehouse: str, target: str) -> bool:
    for line in text.splitlines():
        if re.search(rf"\b{re.escape(market)}\b", line, re.IGNORECASE):
            if re.search(rf"\b{re.escape(target)}\b", line):
                return True
    for line in text.splitlines():
        if re.search(rf"\b{re.escape(warehouse)}\b", line, re.IGNORECASE):
            if re.search(rf"\b{re.escape(target)}\b", line):
                return True
    return False
