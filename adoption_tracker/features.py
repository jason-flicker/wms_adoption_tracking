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
"""

# ─── MARKETS ─────────────────────────────────────────────────────────────────
# Provide the warehouse list, or leave empty for auto-discovery from the WMS dropdown.

MARKETS = {
    "PH": [
        "PHA", "PHB", "PHD", "PHE", "PHG", "PHIXC", "PHIXP",
        "PHJ", "PHK", "PHL", "PHM", "PHN", "PHO", "PHP",
        "PHR", "PHS", "PHT", "PHTSDS", "PHU", "PHV", "PHX", "PHY",
    ],
    "SG": [],   # auto-discovered
    "MY": [],   # auto-discovered
}

# ─── FEATURES ────────────────────────────────────────────────────────────────

FEATURES = [

    # ── wms_frontend ─────────────────────────────────────────────────────────

    {
        "feature": "MTO Picking Task Generation",
        "markets": ["PH", "SG", "MY"],
        "params": {
            "url_path":    "/rulecenter/pickingrule/mtoPickingRule",
            "signal_text": "Split MTO into multiple picking tasks",
        },
    },

    {
        "feature": "Dynamic Wave Rule Setting",
        "markets": ["SG", "MY"],
        "params": {
            "url_path": "/rulecenter/waverule/dynamicWaveRule",
        },
    },

    {
        "feature": "Picking While Sorting",
        "markets": ["SG", "MY"],
        "params": {
            "url_path":     "/rulecenter/skillManagementRule/operatorSkill/salesOutbound/picking",
            "filter_label": "Picking Method",
            "filter_value": "Sorting While Picking",
            "min_count":    5,
        },
    },

    {
        "feature": "Dynamic Replenishment",
        "markets": ["SG", "MY"],
        "params": {
            "url_path":     "/inventorymanage/racktransfer/order",
            "filter_label": "Source from",
            "filter_value": "Replenishment Demand Pool",
            "days":         7,
        },
    },

    {
        "feature": "MTO Exclusion of Non-Sellable Stock",
        "markets": ["SG", "MY"],
        "params": {
            "url_path": "/rulecenter/allocateRule/mt",
        },
    },

    # ── admin_portal ─────────────────────────────────────────────────────────

    {
        "feature": "Inbound Boxing",
        "markets": ["SG", "MY"],
        "params": {
            "checks": [
                {
                    "url":          "https://ops.ssc.shopeemobile.com/wms/configurationmanagement/configuration/view?conf_key=Non_QC_Item_Putaway_Directly",
                    "key":          "Non_QC_Item_Putaway_Directly",
                    "target_value": "1",
                }
            ],
        },
    },

    {
        "feature": "Dynamic Wave Toggle",
        "markets": ["SG", "MY"],
        "params": {
            "checks": [
                {
                    "url":          "https://ops.ssc.shopeemobile.com/wms/configurationmanagement/configuration/view?conf_key=wave_dynamic_wave_task_enable",
                    "key":          "wave_dynamic_wave_task_enable",
                    "target_value": "1",
                },
                {
                    "url":          "https://ops.ssc.shopeemobile.com/wms/configurationmanagement/configuration/view?conf_key=wave_algorithm_switch",
                    "key":          "wave_algorithm_switch",
                    "target_value": "1",
                },
                {
                    "url":          "https://ops.ssc.shopeemobile.com/wms/configurationmanagement/configuration/view?conf_key=pre_allocate_zone_inventory",
                    "key":          "pre_allocate_zone_inventory",
                    "target_value": "1",
                },
            ],
        },
    },
]
