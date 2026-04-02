"""
Checker: Picking While Sorting
Adopted if >= min_count users have Picking Method = "Sorting While Picking".

NOTE: Filter interaction is page-specific and TBD.
      Current implementation counts rows containing the filter_value text
      without applying the dropdown filter — may over-count if the page
      shows all methods by default. Update once page UI is confirmed.
"""

FEATURE_NAME = "Picking While Sorting"
CHECK_TYPE   = "wms_frontend"
SIGNAL       = ">=5 users with Picking Method = Sorting While Picking"


async def check(page, warehouse: str, market: str, params: dict) -> tuple:
    filter_value = params.get("filter_value", "Sorting While Picking")
    min_count    = params.get("min_count", 5)
    try:
        await page.wait_for_load_state("networkidle", timeout=15000)
        result = await page.evaluate("""(target) => {
            const cells = Array.from(document.querySelectorAll(
                'td, .ant-table-cell, [class*="table-cell"]'
            ));
            const matches = cells.filter(el =>
                (el.innerText||'').trim().toLowerCase() === target.toLowerCase()
            );
            return {count: matches.length};
        }""", filter_value)
        count = result["count"]
        if count == 0:
            # Table may not have loaded or filter not applied yet
            return "filter_check_not_implemented", None
        adopted = count >= min_count
        return f"{count}_users_found", adopted
    except Exception as e:
        return f"error: {e}", None
