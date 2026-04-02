"""
Checker: MTO Picking Task Generation
Finds the label "Split MTO into multiple picking tasks" and reads the adjacent Yes/No.
"""
import re

FEATURE_NAME = "MTO Picking Task Generation"
CHECK_TYPE   = "wms_frontend"
SIGNAL       = "Split MTO into multiple picking tasks = Yes"


async def check(page, warehouse: str, market: str, params: dict) -> tuple:
    signal_text = params.get("signal_text", "Split MTO into multiple picking tasks")
    try:
        await page.wait_for_function(
            f"document.body.innerText.includes({repr(signal_text)})",
            timeout=15000,
        )
        text  = await page.evaluate("document.body.innerText")
        match = re.search(
            re.escape(signal_text) + r"[\s\n]+(Yes|No|YES|NO|Enabled|Disabled|On|Off)",
            text, re.IGNORECASE,
        )
        if not match:
            return "element_not_found", None
        val = match.group(1).capitalize()
        return val, val.lower() in ("yes", "enabled", "on")
    except Exception as e:
        return f"error: {e}", None
