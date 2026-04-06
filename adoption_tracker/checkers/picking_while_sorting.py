"""
Checker: Picking While Sorting
Path : /rulecenter/skillManagementRule/operatorSkill/salesOutbound/picking

Adopted if the number of users with Picking Method = "Sorting While Picking"
is >= min_count (default 5).

Page flow
---------
1. Find the "Picking Method" filter label, click its adjacent Ant Design
   dropdown to open it.
2. Click the "Sorting While Picking" option.
3. Click the red "Search" button.
4. Read the "Total: X" counter at the bottom-left of the result table.
5. Adopted = (X >= min_count).
"""

import re

FEATURE_NAME = "Picking While Sorting"
CHECK_TYPE   = "wms_frontend"
SIGNAL       = ">=5 users with Picking Method = Sorting While Picking"


async def check(page, warehouse: str, market: str, params: dict) -> tuple:
    min_count = int(params.get("min_count", 5))

    try:
        await page.wait_for_load_state("networkidle", timeout=15000)

        # ── Step 1: open the Picking Method dropdown ──────────────────────
        # Label and dropdown may be siblings in a grid layout (not nested),
        # so walking up the DOM won't find the select from inside the label.
        # Instead: find the .ant-select-selector whose bounding box sits on
        # the same horizontal row and immediately to the right of the label.
        clicked = await page.evaluate("""() => {
            // Find the visible label — allow child elements (tooltip icons etc.)
            const label = Array.from(document.querySelectorAll('*')).find(el =>
                el.offsetParent !== null &&
                /^Picking Met/i.test((el.innerText || '').trim()) &&
                el.getBoundingClientRect().width < 300
            );
            if (!label) return {ok: false, msg: 'Picking Method label not found'};

            const lRect = label.getBoundingClientRect();

            // Among all visible .ant-select-selector elements, pick the one
            // that is on the same row (vertically overlapping) and closest to
            // the right edge of the label.
            const selectors = Array.from(
                document.querySelectorAll('.ant-select-selector')
            );
            let best = null, bestDist = Infinity;
            for (const sel of selectors) {
                const r = sel.getBoundingClientRect();
                const sameRow = r.top <= lRect.bottom + 8 && r.bottom >= lRect.top - 8;
                const toRight = r.left >= lRect.right - 4;
                if (!sameRow || !toRight) continue;
                const dist = r.left - lRect.right;
                if (dist < bestDist) { bestDist = dist; best = sel; }
            }
            if (!best) return {ok: false, msg: 'no ant-select-selector found on same row to the right'};
            best.click();
            return {ok: true, dist: bestDist};
        }""")

        if not clicked.get("ok"):
            return f"filter_open_failed: {clicked.get('msg')}", None

        await page.wait_for_timeout(500)

        # ── Step 2: select "Sorting While Picking" ────────────────────────
        selected = await page.evaluate("""() => {
            const opts = Array.from(document.querySelectorAll(
                '.ant-select-item-option-content'
            ));
            const target = opts.find(el =>
                (el.innerText || '').trim() === 'Sorting While Picking'
            );
            if (!target) {
                return {
                    ok: false,
                    available: opts.map(e => e.innerText.trim())
                };
            }
            target.click();
            return {ok: true};
        }""")

        if not selected.get("ok"):
            return (
                f"option_not_found (available: {selected.get('available')})",
                None,
            )

        await page.wait_for_timeout(300)

        # ── Step 3: click Search ──────────────────────────────────────────
        clicked_search = await page.evaluate("""() => {
            const btn = Array.from(document.querySelectorAll('button')).find(
                b => (b.innerText || '').trim() === 'Search'
            );
            if (!btn) return false;
            btn.click();
            return true;
        }""")

        if not clicked_search:
            return "search_button_not_found", None

        await page.wait_for_load_state("networkidle", timeout=20000)
        await page.wait_for_timeout(1000)

        # ── Step 4: read Total: X from the table footer ───────────────────
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
