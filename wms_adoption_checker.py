#!/usr/bin/env python3
"""
WMS Feature Adoption Checker
Scalable: configure FEATURES and MARKETS below, run once.

First run:  opens a real Chrome window (dedicated profile), log in via
            Google SSO, then press Enter — profile is saved to wms_profile/.
Later runs: session is reused automatically (no login needed).

Usage:
    python3 wms_adoption_checker.py

Output:
    wms_adoption_results.xlsx
"""

import re
import asyncio
import datetime
from pathlib import Path
from playwright.async_api import async_playwright
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

# ─── CONFIG ──────────────────────────────────────────────────────────────────

BASE_URL = "https://wms.ssc.shopee.ph"

FEATURES = [
    {
        "feature": "MTO Picking Task Generation",
        "signal": "Split MTO into multiple picking tasks",
        "url": "/v2/rulecenter/pickingrule/mtoPickingRule",
    },
    # Add more features here:
    # {
    #     "feature": "My Other Feature",
    #     "signal": "Exact label text on page before Yes/No",
    #     "url": "/v2/rulecenter/someOtherPage",
    # },
]

MARKETS = {
    "PH": [
        "PHA", "PHB", "PHD", "PHE", "PHG", "PHIXC", "PHIXP",
        "PHJ", "PHK", "PHL", "PHM", "PHN", "PHO", "PHP",
        "PHR", "PHS", "PHT", "PHTSDS", "PHU", "PHV", "PHX", "PHY",
    ],
    # "MY": ["MYA", "MYB", ...],
    # "SG": ["SGA", ...],
}

PROFILE_DIR = str(Path(__file__).parent / "wms_profile")  # dedicated Chrome profile
OUTPUT_FILE = str(Path(__file__).parent / "wms_adoption_results.xlsx")

# ─── SCRAPER ─────────────────────────────────────────────────────────────────

async def get_config_value(page, signal_label: str) -> str:
    """Extract Yes/No value for a given signal label from the current page."""
    try:
        text = await page.evaluate("document.body.innerText")
        match = re.search(
            re.escape(signal_label) + r"[\s\n]+(Yes|No|YES|NO|Enabled|Disabled|On|Off)",
            text, re.IGNORECASE
        )
        return match.group(1).capitalize() if match else "unknown"
    except Exception as e:
        return f"error: {e}"


async def switch_warehouse(page, warehouse_code: str):
    """Click the warehouse dropdown and select the given warehouse."""
    # Click dropdown
    await page.locator("text=" + warehouse_code).first.click()
    await page.wait_for_load_state("networkidle", timeout=15000)


async def select_warehouse_from_dropdown(page, warehouse_code: str):
    """Open the warehouse selector and pick a warehouse by code using JS clicks."""

    # Step 1: Find and click the visible trigger (the "PH - XXX" display element).
    # The .ssc-options list is hidden; the trigger lives elsewhere in the DOM.
    click_result = await page.evaluate("""() => {
        // Walk every element; find the first visible one whose trimmed text
        // looks like a warehouse label ("PH - XXX") and has no deep children.
        const all = Array.from(document.querySelectorAll('*'));
        const candidates = all.filter(el => {
            if (!el.offsetParent) return false;
            const text = (el.innerText || '').trim();
            return /^[A-Z]{2} - [A-Z0-9]+$/.test(text);
        });
        if (candidates.length === 0) return {ok: false, msg: 'no visible trigger found'};
        const el = candidates[0];
        el.click();
        return {ok: true, clicked: el.tagName + '.' + el.className, text: el.innerText.trim()};
    }""")
    print(f"\n    [debug] trigger click: {click_result}")

    if not click_result.get("ok"):
        raise Exception(f"Could not find warehouse trigger: {click_result.get('msg')}")

    await page.wait_for_timeout(600)

    # Step 2: Click the target warehouse option via JS (options may still be hidden to Playwright).
    target_text = f"PH - {warehouse_code}"
    option_result = await page.evaluate("""(target) => {
        // Only target LI.ssc-option items — never the trigger span itself
        const options = Array.from(document.querySelectorAll('li.ssc-option, li[class*="ssc-option"]'));
        const el = options.find(e => (e.innerText || '').trim() === target);
        if (!el) {
            const texts = options.map(e => e.innerText.trim()).slice(0, 10);
            return {ok: false, msg: 'option not found', available: texts};
        }
        el.click();
        return {ok: true, clicked: el.tagName + '.' + el.className};
    }""", target_text)
    print(f"    [debug] option click: {option_result}")

    if not option_result.get("ok"):
        raise Exception(f"Could not find option '{target_text}': {option_result.get('msg')} | available: {option_result.get('available')}")

    await page.wait_for_load_state("networkidle", timeout=20000)
    await page.wait_for_timeout(1000)


async def run():
    checked_at = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    results = []

    async with async_playwright() as p:
        is_first_run = not Path(PROFILE_DIR).exists()
        # Use real Chrome with a dedicated profile dir so Google OAuth works.
        # The profile is created on first run and reused on subsequent runs.
        context = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            channel="chrome",
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )

        if is_first_run:
            print("First run — browser opened. Please log in via Google SSO.")
            print("Press Enter here once you are fully logged into WMS.")
            page = await context.new_page()
            await page.goto(BASE_URL, wait_until="networkidle", timeout=30000)
            input()
            print("Session saved to profile. Subsequent runs won't need login.")
            await page.close()
        else:
            print(f"Reusing saved profile from {PROFILE_DIR}")

        page = await context.new_page()

        # ── SAFETY GUARD: block write operations at network level ─────────
        # WMS uses POST for many read operations (get_conf_list, etc.) so we
        # can't block all POSTs. Instead, block by URL keyword: any endpoint
        # whose path contains a write-like verb is aborted.
        WRITE_VERBS = {
            "create", "update", "delete", "remove", "save", "submit",
            "edit", "modify", "add_", "batch_update", "upload",
        }
        # set_user_setting is how the UI switches warehouse context — allow it.
        ALLOWED_PATHS = {"set_user_setting"}
        BLOCKED_METHODS = {"PUT", "DELETE", "PATCH"}
        GUARD_HOST = "wms.ssc.shopee.ph"

        async def block_mutations(route, request):
            host = request.url.split("/")[2] if "//" in request.url else ""
            if host != GUARD_HOST:
                await route.continue_()
                return
            method = request.method.upper()
            path = request.url.lower()
            is_allowed = any(a in path for a in ALLOWED_PATHS)
            is_write_post = method == "POST" and any(v in path for v in WRITE_VERBS)
            if not is_allowed and (method in BLOCKED_METHODS or is_write_post):
                print(f"\n  🛡️  BLOCKED {method} → {request.url[:80]}")
                await route.abort()
            else:
                await route.continue_()

        await page.route("**/*", block_mutations)
        # ───────────────────────────────────────────────────────────────────

        for feature in FEATURES:
            feature_name = feature["feature"]
            signal = feature["signal"]
            url = BASE_URL + feature["url"]

            for market, warehouses in MARKETS.items():
                print(f"\n{'─'*50}")
                print(f"Feature: {feature_name} | Market: {market}")
                print(f"{'─'*50}")

                for i, whs in enumerate(warehouses):
                    try:
                        print(f"  [{i+1}/{len(warehouses)}] {whs}...", end=" ", flush=True)

                        # Navigate to feature page (always navigate to ensure correct page)
                        await page.goto(url, wait_until="networkidle", timeout=30000)
                        await page.wait_for_timeout(1000)

                        # Check for login redirect
                        if "login" in page.url.lower() or "sso" in page.url.lower():
                            print("\n⚠️  Login required! Please log in manually, then press Enter.")
                            input()
                            await page.goto(url, wait_until="networkidle", timeout=30000)

                        # Always switch warehouse explicitly (session is server-side/cookie-based)
                        await select_warehouse_from_dropdown(page, whs)

                        # Re-navigate after switch: set_user_setting may reload the page
                        # and navigate away from the feature URL.
                        await page.goto(url, wait_until="networkidle", timeout=30000)

                        # Wait for the signal label to appear before reading
                        try:
                            await page.wait_for_function(
                                f"document.body.innerText.includes({repr(signal)})",
                                timeout=15000,
                            )
                        except Exception:
                            body_preview = (await page.evaluate("document.body.innerText"))[:300]
                            print(f"\n    [debug] signal not found. page preview: {body_preview!r}")

                        # Extract value
                        value = await get_config_value(page, signal)
                        adopted = value.lower() in ("yes", "enabled", "on")
                        print(f"→ {value} ({'✅' if adopted else '❌'})")

                        results.append({
                            "market": market,
                            "warehouse": whs,
                            "feature": feature_name,
                            "signal": signal,
                            "signal_value": value,
                            "adopted": adopted,
                            "checked_at": checked_at,
                        })

                    except Exception as e:
                        print(f"→ ERROR: {e}")
                        results.append({
                            "market": market,
                            "warehouse": whs,
                            "feature": feature_name,
                            "signal": signal,
                            "signal_value": f"error: {e}",
                            "adopted": None,
                            "checked_at": checked_at,
                        })

        await context.close()
        await browser.close()

    save_excel(results, checked_at)
    print(f"\n✅ Done! Results saved to: {OUTPUT_FILE}")
    print(f"   Total checked: {len(results)}")
    adopted_count = sum(1 for r in results if r["adopted"] is True)
    print(f"   Adopted: {adopted_count} / {len(results)}")


# ─── EXCEL OUTPUT ─────────────────────────────────────────────────────────────

def save_excel(results: list, checked_at: str):
    wb = Workbook()
    ws = wb.active
    ws.title = "WMS Adoption"

    headers = ["Market", "Warehouse", "Feature", "Signal", "Signal Value", "Adopted", "Checked At"]
    green_fill = PatternFill("solid", fgColor="C6EFCE")
    red_fill   = PatternFill("solid", fgColor="FFC7CE")
    grey_fill  = PatternFill("solid", fgColor="D9D9D9")
    green_font = Font(name="Arial", color="276221")
    red_font   = Font(name="Arial", color="9C0006")
    bold       = Font(name="Arial", bold=True)
    arial      = Font(name="Arial")

    # Header row
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = bold
        cell.fill = grey_fill
        cell.alignment = Alignment(horizontal="center")

    # Data rows
    for row_idx, r in enumerate(results, 2):
        adopted = r["adopted"]
        fill = green_fill if adopted else (red_fill if adopted is False else PatternFill("solid", fgColor="FFEB9C"))
        font = green_font if adopted else (red_font if adopted is False else Font(name="Arial", color="9C6500"))

        values = [
            r["market"], r["warehouse"], r["feature"],
            r["signal"], r["signal_value"],
            "Yes" if adopted else ("No" if adopted is False else "Error"),
            r["checked_at"],
        ]
        for col_idx, val in enumerate(values, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.font = font
            cell.fill = fill
            cell.alignment = Alignment(horizontal="left" if col_idx in (3, 4) else "center")

    # Summary row
    total = len(results)
    adopted_total = sum(1 for r in results if r["adopted"] is True)
    summary_row = total + 2
    ws.cell(row=summary_row, column=1, value="TOTAL").font = bold
    ws.cell(row=summary_row, column=6, value=f"{adopted_total} / {total} adopted ({int(adopted_total/total*100) if total else 0}%)").font = bold

    # Column widths
    widths = [8, 10, 30, 42, 14, 10, 22]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    ws.freeze_panes = "A2"

    # Summary sheet (pivot by feature)
    ws2 = wb.create_sheet("Summary by Feature")
    ws2.cell(row=1, column=1, value="Feature").font = bold
    ws2.cell(row=1, column=2, value="Total Warehouses").font = bold
    ws2.cell(row=1, column=3, value="Adopted").font = bold
    ws2.cell(row=1, column=4, value="Adoption %").font = bold
    for c in range(1, 5):
        ws2.cell(row=1, column=c).fill = grey_fill
        ws2.cell(row=1, column=c).alignment = Alignment(horizontal="center")

    from collections import defaultdict
    by_feature = defaultdict(list)
    for r in results:
        by_feature[r["feature"]].append(r)

    for row_i, (feat, rows) in enumerate(by_feature.items(), 2):
        total_f = len(rows)
        adopted_f = sum(1 for r in rows if r["adopted"] is True)
        pct = f"{int(adopted_f/total_f*100)}%" if total_f else "0%"
        ws2.cell(row=row_i, column=1, value=feat).font = arial
        ws2.cell(row=row_i, column=2, value=total_f).font = arial
        ws2.cell(row=row_i, column=3, value=adopted_f).font = arial
        ws2.cell(row=row_i, column=4, value=pct).font = arial
        for c in range(1, 5):
            ws2.cell(row=row_i, column=c).alignment = Alignment(horizontal="center")

    for i, w in enumerate([35, 18, 10, 14], 1):
        ws2.column_dimensions[get_column_letter(i)].width = w

    wb.save(OUTPUT_FILE)


# ─── ENTRY POINT ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    asyncio.run(run())
