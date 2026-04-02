"""
Checker: Dynamic Wave Rule Setting
Adopted if at least 1 rule row has status = Active in the Dynamic Wave Rule table.
"""

FEATURE_NAME = "Dynamic Wave Rule Setting"
CHECK_TYPE   = "wms_frontend"
SIGNAL       = "At least 1 active rule in Dynamic Wave Rule table"


async def check(page, warehouse: str, market: str, params: dict) -> tuple:
    try:
        await page.wait_for_load_state("networkidle", timeout=15000)
        result = await page.evaluate("""() => {
            const cells = Array.from(document.querySelectorAll(
                'td, .ant-table-cell, [class*="table-cell"]'
            ));
            const active = cells.find(el => /^active$/i.test((el.innerText||'').trim()));
            return {found: !!active, total_cells: cells.length};
        }""")
        if result["total_cells"] == 0:
            return "page_no_table", None
        if result["found"]:
            return "active_rule_found", True
        return "no_active_rule", False
    except Exception as e:
        return f"error: {e}", None
