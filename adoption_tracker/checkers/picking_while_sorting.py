"""
Checker: Picking While Sorting
Path : /rulecenter/skillManagementRule/operatorSkill/salesOutbound/picking

Adopted if the number of users with Picking Method = "Sorting While Picking"
is >= min_count (default 5).

DOM structure (confirmed via DevTools on wms.ssc.shopee.sg):
  - Filter label : SPAN.ssc-form-item-label  "Picking Meth..."
                     parent: SPAN.tooltip
                       parent: container with [class*="ssc-select"]  (i=1)
  - Dropdown options : DIV.ssc-table-header-column-container
  - Search button    : <button> innerText "Search"
  - Total counter    : leaf text matching /^Total: [\d,]+/

Known pitfall: after previous warehouse check a toast/notification ssc-select
may be open (shows "Success/Download/Failed"). We dismiss all overlays first
and verify the correct options appear before proceeding.
"""

import re

FEATURE_NAME = "Picking While Sorting"
CHECK_TYPE   = "wms_frontend"
SIGNAL       = ">=5 users with Picking Method = Sorting While Picking"


async def check(page, warehouse: str, market: str, params: dict) -> tuple:
    min_count = int(params.get("min_count", 5))

    try:
        await page.wait_for_load_state("networkidle", timeout=15000)

        # ── Step 0: dismiss any open overlays / toast notifications ───────
        # After a previous warehouse check a toast dropdown may still be open.
        await page.evaluate("""() => {
            // Click body to close any open dropdowns
            document.body.click();
            // Remove toast / notification elements
            document.querySelectorAll(
                '[class*="ssc-notification"], [class*="notification-notice"], ' +
                '[class*="ssc-message"], [class*="ssc-toast"]'
            ).forEach(el => el.remove());
        }""")
        await page.wait_for_timeout(400)

        # ── Step 1: open the Picking Method ssc-select ────────────────────
        # Walk up 2 levels from label to its form-item container, then click
        # the ssc-select inside that container (not a global querySelector).
        clicked = await page.evaluate("""() => {
            const label = Array.from(
                document.querySelectorAll('.ssc-form-item-label')
            ).find(el => /Picking Met/i.test((el.innerText || '').trim()));

            if (!label) return {ok: false, msg: 'ssc-form-item-label not found'};

            // label → SPAN.tooltip → form-item container (i=1 from inspection)
            const container = label.parentElement?.parentElement;
            if (!container) return {ok: false, msg: 'container not found'};

            const sel = container.querySelector('[class*="ssc-select"]');
            if (!sel) return {ok: false, msg: 'ssc-select not in container'};

            sel.click();
            return {ok: true};
        }""")

        if not clicked.get("ok"):
            return f"filter_open_failed: {clicked.get('msg')}", None

        await page.wait_for_timeout(400)

        # ── Step 1b: verify correct options appeared ───────────────────────
        # If a notification dropdown opened instead, options will be
        # "Success/Download/Failed". Check for expected picking options.
        opts_check = await page.evaluate("""() => {
            const opts = Array.from(document.querySelectorAll(
                '.ssc-table-header-column-container'
            )).map(el => (el.innerText || '').trim());
            return opts;
        }""")

        if 'Sorting While Picking' not in opts_check and 'Batch Picking' not in opts_check:
            # Wrong dropdown opened — close it and report
            await page.keyboard.press('Escape')
            return f"wrong_dropdown_options: {opts_check[:6]}", None

        # ── Step 2: click "Sorting While Picking" option ──────────────────
        selected = await page.evaluate("""() => {
            const opts = Array.from(document.querySelectorAll(
                '.ssc-table-header-column-container'
            ));
            const target = opts.find(
                el => (el.innerText || '').trim() === 'Sorting While Picking'
            );
            if (!target) {
                return {ok: false,
                        available: opts.map(e => e.innerText.trim()).slice(0, 6)};
            }
            target.click();
            return {ok: true};
        }""")

        if not selected.get("ok"):
            return f"option_not_found: {selected.get('available')}", None

        await page.wait_for_timeout(300)

        # ── Step 3: click Search ──────────────────────────────────────────
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

        # ── Step 4: read Total: X ─────────────────────────────────────────
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
