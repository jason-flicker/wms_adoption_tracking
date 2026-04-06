"""
Checker: Picking While Sorting
Path : /rulecenter/skillManagementRule/operatorSkill/salesOutbound/picking

Adopted if the number of users with Picking Method = "Sorting While Picking"
is >= min_count (default 5).

DOM structure (confirmed via DevTools inspection):
  - Filter label : SPAN.ssc-form-item-label  (text "Picking Meth...")
                    └─ parent: SPAN.tooltip
                        └─ parent: container that holds .ssc-select
  - Dropdown trigger : [class*="ssc-select"]  (2 levels up from label)
  - Dropdown options : DIV.ssc-table-header-column-container
  - Search button    : <button> with innerText "Search"
  - Total counter    : leaf element whose text matches /^Total: [\d,]+/
"""

import re

FEATURE_NAME = "Picking While Sorting"
CHECK_TYPE   = "wms_frontend"
SIGNAL       = ">=5 users with Picking Method = Sorting While Picking"


async def check(page, warehouse: str, market: str, params: dict) -> tuple:
    min_count = int(params.get("min_count", 5))

    try:
        await page.wait_for_load_state("networkidle", timeout=15000)

        # ── Step 1: open the Picking Method ssc-select dropdown ───────────
        # label.parentElement = SPAN.tooltip
        # label.parentElement.parentElement = container with .ssc-select (i=1)
        clicked = await page.evaluate("""() => {
            const label = Array.from(
                document.querySelectorAll('.ssc-form-item-label')
            ).find(el => /Picking Met/i.test((el.innerText || '').trim()));

            if (!label) return {ok: false, msg: 'ssc-form-item-label not found'};

            // Walk up 2 levels (label → tooltip → container)
            const container = label.parentElement?.parentElement;
            if (!container) return {ok: false, msg: 'container not found'};

            const sel = container.querySelector('[class*="ssc-select"]');
            if (!sel) return {ok: false, msg: 'ssc-select not found in container'};

            sel.click();
            return {ok: true};
        }""")

        if not clicked.get("ok"):
            return f"filter_open_failed: {clicked.get('msg')}", None

        await page.wait_for_timeout(400)

        # ── Step 2: click "Sorting While Picking" option ──────────────────
        # Options render as DIV.ssc-table-header-column-container
        selected = await page.evaluate("""() => {
            const opts = Array.from(document.querySelectorAll(
                '.ssc-table-header-column-container'
            ));
            const target = opts.find(
                el => (el.innerText || '').trim() === 'Sorting While Picking'
            );
            if (!target) {
                return {
                    ok: false,
                    available: opts.map(e => e.innerText.trim()).slice(0, 8)
                };
            }
            target.click();
            return {ok: true};
        }""")

        if not selected.get("ok"):
            return f"option_not_found: {selected.get('available')}", None

        await page.wait_for_timeout(300)

        # ── Step 3: click the Search button ──────────────────────────────
        clicked_search = await page.evaluate("""() => {
            const btn = Array.from(
                document.querySelectorAll('button, [class*="ssc-btn"]')
            ).find(b => (b.innerText || '').trim() === 'Search');
            if (!btn) return false;
            btn.click();
            return true;
        }""")

        if not clicked_search:
            return "search_button_not_found", None

        await page.wait_for_load_state("networkidle", timeout=20000)
        await page.wait_for_timeout(1000)

        # ── Step 4: read Total: X from table footer ───────────────────────
        total_text = await page.evaluate("""() => {
            const el = Array.from(document.querySelectorAll('*')).find(e =>
                e.offsetParent !== null &&
                e.children.length === 0 &&
                /^Total:\s*[\d,]+/.test((e.innerText || '').trim())
            );
            return el ? el.innerText.trim() : null;
        }""")

        if not total_text:
            return "total_counter_not_found", None

        match = re.search(r'Total:\s*([\d,]+)', total_text)
        if not match:
            return f"total_parse_error: {total_text!r}", None

        count   = int(match.group(1).replace(',', ''))
        adopted = count >= min_count
        return f"{count}_users_sorting_while_picking", adopted

    except Exception as e:
        return f"error: {e}", None
