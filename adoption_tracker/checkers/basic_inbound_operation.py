"""
Checker: Basic Inbound Operation
Path : /inbound/order

Adopted if the inbound ASN table has at least 1 row after filtering
Actual Arrive time to the last N days (default 7).

Steps:
  1. Set Actual Arrive time range to [today-N, today]
     (filter is visible by default — no "More" button needed)
  2. Click Search
  3. Check Total > 0

DOM notes:
  - "More" button must be clicked first to expand the filter grid.
  - Date picker: no data-for attribute — scoped via .ssc-form-item-label
    matching "Actual Arriv" → xpath ../.. → two <input> elements.
  - Use click(click_count=3) + type() to set dates (triggers Vue reactivity).
    Do NOT use native HTMLInputElement setter — it does not commit to the
    Vue date picker component.
  - Total counter: "X Order(s) Selected" text OR leaf /^Total:\s*[\d,]+/
"""

import re
import datetime

FEATURE_NAME = "Basic Inbound Operation"
CHECK_TYPE   = "wms_frontend"
SIGNAL       = "At least 1 ASN with Actual Arrive time in the last 7 days"


async def check(page, warehouse: str, market: str, params: dict) -> tuple:
    days = int(params.get("days", 7))

    try:
        await page.wait_for_load_state("networkidle", timeout=15000)

        # ── Step 0: close dropdowns, remove toasts ────────────────────────
        for _ in range(3):
            await page.keyboard.press('Escape')
            await page.wait_for_timeout(150)
        await page.evaluate("""() => {
            document.querySelectorAll(
                '[class*="ssc-notification"], [class*="notification-notice"],' +
                '[class*="ssc-message"], [class*="ssc-toast"]'
            ).forEach(el => el.remove());
        }""")
        await page.wait_for_timeout(300)

        # ── Step 1: click "More" to expand filter grid ───────────────────
        clicked_more = await page.evaluate("""() => {
            const btn = Array.from(document.querySelectorAll('button')).find(
                b => /^More$/i.test((b.innerText || '').trim())
            );
            if (!btn) return {ok: false, msg: 'More button not found'};
            btn.click();
            return {ok: true};
        }""")
        if not clicked_more.get("ok"):
            return f"more_button_not_found: {clicked_more.get('msg')}", None
        await page.wait_for_timeout(500)

        # ── Step 2: set Actual Arrive time date range ─────────────────────
        today      = datetime.date.today()
        start_date = today - datetime.timedelta(days=days)
        start_str  = start_date.strftime("%Y/%m/%d 00:00:00")
        end_str    = today.strftime("%Y/%m/%d 23:59:59")

        # Verify the label and its inputs are present
        picker_info = await page.evaluate("""() => {
            const label = Array.from(document.querySelectorAll('.ssc-form-item-label'))
                .find(el => /actual arriv/i.test((el.innerText || '').trim()));
            if (!label) return {ok: false, msg: 'Actual Arrive label not found'};
            const container = label.parentElement?.parentElement;
            if (!container) return {ok: false, msg: 'container missing'};
            const inputs = container.querySelectorAll('input');
            if (inputs.length < 2) return {ok: false, msg: `only ${inputs.length} inputs`};
            return {ok: true};
        }""")
        if not picker_info.get("ok"):
            return f"arrive_time_picker_not_found: {picker_info.get('msg')}", None

        # Open calendar by clicking the outer start date input
        container_loc = page.locator('.ssc-form-item-label').filter(
            has_text=re.compile(r'Actual Arriv', re.IGNORECASE)
        ).locator('xpath=../..')
        await container_loc.locator('input').first.click()
        await page.wait_for_timeout(600)

        # Find cell indices, then use Playwright locator.click() which dispatches
        # all necessary events (pointerdown, mousedown, mouseup, click) correctly.
        indices = await page.evaluate(f"""() => {{
            const panel = document.querySelector('.ssc-picker-panel.ssc-date-range-panel');
            if (!panel) return {{ok: false, msg: 'panel not found'}};
            const cells = Array.from(panel.querySelectorAll('.ssc-date-table-date-cell'));
            const todayCell = cells.find(c =>
                c.parentElement.classList.contains('ssc-picker-table-today')
            );
            if (!todayCell) return {{ok: false, msg: 'today cell not found'}};
            const todayIdx = cells.indexOf(todayCell);
            const startIdx = todayIdx - {days};
            if (startIdx < 0) return {{ok: false, msg: `need_nav:${{startIdx}}`}};
            return {{ok: true, startIdx, todayIdx,
                     sd: cells[startIdx].innerText.trim(),
                     ed: todayCell.innerText.trim()}};
        }}""")
        if not indices.get("ok"):
            return f"date_cell_not_found: {indices.get('msg')}", None

        cell_loc = page.locator('.ssc-picker-panel.ssc-date-range-panel .ssc-date-table-date-cell')
        await cell_loc.nth(indices["startIdx"]).click()
        await page.wait_for_timeout(500)
        await cell_loc.nth(indices["todayIdx"]).click()
        await page.wait_for_timeout(500)

        # Click the footer Confirm button (ssc-picker-panel-footer-action-button)
        confirm_btn = page.locator('button.ssc-picker-panel-footer-action-button')
        if await confirm_btn.count() == 0:
            return "calendar_confirm_not_found", None
        await confirm_btn.click()
        await page.wait_for_timeout(500)

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

        # ── Step 4: read Total: X — poll until stable (table may still render) ──
        def _read_total_js():
            return """() => {
                const el = Array.from(document.querySelectorAll('*')).find(e =>
                    e.offsetParent !== null &&
                    e.children.length === 0 &&
                    /^Total:\\s*[\\d,]+/.test((e.innerText || '').trim())
                );
                return el ? el.innerText.trim() : null;
            }"""

        total_text = None
        for _ in range(6):          # up to ~6s of polling
            t1 = await page.evaluate(_read_total_js())
            await page.wait_for_timeout(1000)
            t2 = await page.evaluate(_read_total_js())
            if t1 and t1 == t2:     # stable — table finished loading
                total_text = t1
                break
        if not total_text:
            return "total_counter_not_found", None

        match = re.search(r'Total:\s*([\d,]+)', total_text)
        if not match:
            return f"total_parse_error: {total_text!r}", None

        count   = int(match.group(1).replace(',', ''))
        adopted = count > 0
        return f"{count}_inbound_orders_in_{days}d", adopted

    except Exception as e:
        return f"error: {e}", None
