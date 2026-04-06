"""
Checker: Dynamic Wave Rule Setting
Path  : /rulecenter/waverule/dynamicWaveRule

DOM notes:
  - Table uses ssc-react-rc-table-cell (NOT ant-table-cell)
  - Status column (td index 4) holds a toggle switch
  - Active   : <span class="ssc-react-switch-wrapper ssc-react-switch-wrapper-checked">
                 <input value="1">
  - Inactive : <span class="ssc-react-switch-wrapper">   (no -checked suffix)
                 <input value="0">
  - No data  : table has only 1 row (header placeholder row)
  Signal: at least 1 rule row whose toggle has class ssc-react-switch-wrapper-checked
"""

FEATURE_NAME = "Dynamic Wave Rule Setting"
CHECK_TYPE   = "wms_frontend"
SIGNAL       = "At least 1 active (toggled-on) rule in Dynamic Wave Rule table"


async def check(page, warehouse: str, market: str, params: dict) -> tuple:
    try:
        await page.wait_for_load_state("networkidle", timeout=15000)

        result = await page.evaluate("""() => {
            // Count data rows (skip row1 which is a hidden placeholder row)
            const rows = Array.from(document.querySelectorAll('tr'));
            const dataRows = rows.filter(r => {
                const cells = r.querySelectorAll('td');
                // A real data row has td1 with a numeric priority value
                return cells.length > 1 && /^\d+$/.test((cells[1]?.innerText || '').trim());
            });

            // Check for at least one active toggle
            const activeToggles = document.querySelectorAll(
                '.ssc-react-switch-wrapper-checked'
            );

            return {
                dataRowCount: dataRows.length,
                activeCount: activeToggles.length,
            };
        }""")

        data_rows   = result["dataRowCount"]
        active_count = result["activeCount"]

        if data_rows == 0:
            return "no_rules_configured", False
        if active_count > 0:
            return f"{active_count}_active_rules_of_{data_rows}", True
        return f"0_active_rules_of_{data_rows}", False

    except Exception as e:
        return f"error: {e}", None
