"""
Feature + Market Configuration
================================
Maintained by BPM / PM team.

To add a feature:
  1. Drop a new checker file in checkers/
  2. Add an entry to FEATURES below (feature name must match FEATURE_NAME in the checker)

To add a market:
  1. Add it to MARKETS (leave the list empty — warehouses are auto-discovered)
  2. Add the market code to each relevant feature's "markets" list

params keys are passed directly to checker.check() — they are not read by runner.py.
See each checker file for the params it expects.

If a feature omits the "markets" key entirely, it will be run against ALL markets
defined in MARKETS above.
"""

# ─── MARKETS ─────────────────────────────────────────────────────────────────
# Provide the warehouse list, or leave empty for auto-discovery from the WMS dropdown.

MARKETS = {
    "BR": [
        "BRFGO1", "BRFMG1", "BRFPE1", "BRFRS1", "BRFSP1",
    ],
    "ID": [
        "IDBGR1", "IDDPR1", "IDG", "IDH", "IDK", "IDLSC1", "IDM", "IDMSC1",
        "IDN", "IDNSC1", "IDP", "IDPBR1", "IDQ", "IDR", "IDS",
    ],
    "MY": [
        "MYE", "MYJ", "MYK", "MYM", "MYP", "MYV", "MYX",
    ],
    "PH": [
        "PHA", "PHB", "PHE", "PHG", "PHIXC", "PHIXP", "PHK", "PHL",
        "PHM", "PHP", "PHS", "PHTSDS", "PHU", "PHX",
    ],
    "SG": [
        "SGC", "SGL", "SGP",
    ],
    "TH": [
        "TH3PFW", "THA", "THBSC1", "THBWN1", "THO", "THP",
    ],
    "TW": [
        "TWA", "TWE", "TWG", "TWH", "TWK", "TWT", "TWW", "TWX",
    ],
    "VN": [
        "VNA", "VNCB", "VNCL", "VNDB", "VNDL", "VNN", "VNNL", "VNS", "VNVL", "VNWL",
    ],
}

# ─── FEATURES ────────────────────────────────────────────────────────────────

def get_markets(feature: dict) -> list:
    """Return the markets list for a feature.
    Falls back to all keys in MARKETS if the feature omits the 'markets' key."""
    return feature.get("markets", list(MARKETS.keys()))


FEATURES = [

# ── admin_portal ─────────────────────────────────────────────────────────

    {
        "feature":      "MTO Picking Task Generation",
        "domain":       "Move Transfer",
        "description":  "Adopted if the 'Split MTO into multiple picking tasks' toggle is set to Yes in Rule Center → Picking Rule.",
        "params": {
            "url_path":    "/rulecenter/pickingrule/mtoPickingRule",
            "signal_text": "Split MTO into multiple picking tasks",
        },
    },

    {
        "feature":      "Dynamic Wave Rule Setting",
        "domain":       "Outbound",
        "description":  "Adopted if at least 1 rule is toggled ON in the Dynamic Wave Rule table (Rule Center → Wave Rule).",
        "params": {
            "url_path": "/rulecenter/waverule/dynamicWaveRule",
        },
    },

    {
        "feature":      "Picking While Sorting",
        "domain":       "Outbound",
        "description":  "Adopted if ≥5 operators have Picking Method = 'Sorting While Picking' in operator skill settings.",
        "params": {
            "url_path":     "/rulecenter/skillManagementRule/operatorSkill/salesOutbound/picking",
            "filter_label": "Picking Method",
            "filter_value": "Sorting While Picking",
            "min_count":    5,
        },
    },

    {
        "feature":      "Dynamic Replenishment",
        "domain":       "Inventory",
        "description":  "Adopted if any replenishment orders with Source From = 'Replenishment Demand Pool' exist in the last 7 days.",
        "params": {
            "url_path":     "/inventorymanage/racktransfer/order",
            "filter_label": "Source from",
            "filter_value": "Replenishment Demand Pool",
            "days":         7,
        },
    },

    {
        "feature":      "MTO Exclusion of Non-Sellable Stock",
        "domain":       "Move Transfer",
        "description":  "Adopted if at least 1 Allocate Exclusion Rule is toggled ON in Rule Center → Allocate Rule (MTO tab).",
        "params": {
            "url_path": "/rulecenter/allocateRule/mt",
        },
    },

    {
        "feature":      "Basic Outbound Operation",
        "domain":       "Outbound",
        "description":  "Active warehouse signal — adopted if at least 1 sales outbound order was created in the last 7 days.",
        "params": {
            "url_path": "/salesoutbound/order",
            "days":     7,
        },
    },

    {
        "feature":      "Basic Inbound Operation",
        "domain":       "Inbound",
        "description":  "Active warehouse signal — adopted if at least 1 inbound ASN has an Actual Arrival time recorded in the last 7 days.",
        "params": {
            "url_path": "/inbound/order",
            "days":     7,
        },
    },

]
