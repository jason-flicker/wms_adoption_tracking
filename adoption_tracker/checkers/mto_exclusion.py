"""
Checker: MTO Exclusion of Non-Sellable Stock
Adopted if at least 1 rule under Allocate Exclusion Rule is toggled ON.
Uses Ant Design's .ant-switch-checked class for ON state detection.
"""

FEATURE_NAME = "MTO Exclusion of Non-Sellable Stock"
CHECK_TYPE   = "wms_frontend"
SIGNAL       = "At least 1 Allocate Exclusion Rule toggled on"


async def check(page, warehouse: str, market: str, params: dict) -> tuple:
    try:
        await page.wait_for_load_state("networkidle", timeout=15000)
        result = await page.evaluate("""() => {
            const on = document.querySelectorAll(
                '.ant-switch-checked, input[type="checkbox"]:checked'
            );
            const total = document.querySelectorAll(
                '.ant-switch, input[type="checkbox"]'
            );
            return {on_count: on.length, total_count: total.length};
        }""")
        on_count    = result["on_count"]
        total_count = result["total_count"]
        if total_count == 0:
            return "page_no_toggles", None
        if on_count > 0:
            return f"{on_count}_rules_toggled_on", True
        return "no_rules_toggled_on", False
    except Exception as e:
        return f"error: {e}", None
