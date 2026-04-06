"""
Checker: MTO Exclusion of Non-Sellable Stock
Path  : /rulecenter/allocaterule/mtAllocateRule

DOM notes:
  - Page has 3 sections: MT Allocate Rule, Allocate Rule, Allocate Exclusion Rule
  - Exclusion rules live inside: DIV.allocate-exclusion-rule-table-container
  - Toggles inside that container use class: ssc-switch rule-switch
    Active  : "ssc-switch rule-switch"              (no extra class)
    Inactive: "ssc-switch rule-switch ssc-switch-inactive"
  - Do NOT use .ant-switch-checked — this page uses Vue ssc-switch, not Ant Design

  Signal: at least 1 rule in .allocate-exclusion-rule-table-container is active
          (i.e. has .rule-switch but NOT .ssc-switch-inactive)
"""

FEATURE_NAME = "MTO Exclusion of Non-Sellable Stock"
CHECK_TYPE   = "wms_frontend"
SIGNAL       = "At least 1 Allocate Exclusion Rule toggled on"


async def check(page, warehouse: str, market: str, params: dict) -> tuple:
    try:
        await page.wait_for_load_state("networkidle", timeout=15000)

        result = await page.evaluate("""() => {
            const container = document.querySelector(
                '.allocate-exclusion-rule-table-container'
            );
            if (!container) return {found: false};

            const all     = container.querySelectorAll('.ssc-switch.rule-switch');
            const active  = Array.from(all).filter(
                el => !el.classList.contains('ssc-switch-inactive')
            );
            return {found: true, total: all.length, active: active.length};
        }""")

        if not result.get("found"):
            return "exclusion_container_not_found", None

        total  = result["total"]
        active = result["active"]

        if total == 0:
            return "no_exclusion_rules_present", None
        if active > 0:
            return f"{active}_of_{total}_exclusion_rules_on", True
        return f"0_of_{total}_exclusion_rules_on", False

    except Exception as e:
        return f"error: {e}", None
