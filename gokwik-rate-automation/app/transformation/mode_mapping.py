"""
Mode mapping: Rate PDF mode names -> Dashboard tab + method.
From Section 6 of the docs.
"""

from difflib import get_close_matches

# Maps Rate PDF mode names -> Dashboard (tab, method)
# method values MUST EXACTLY match real GoKwik dashboard dropdown options:
#   EMI:         ['Cardless', 'Credit Card', 'Debit Card', 'Default']
#   UPI:         ['Credit Card', 'Debit Card', 'Default']
#   NetBanking:  ['Airtel', 'AXIS', 'Default', 'HDFC', 'ICICI', 'KOTAK', 'SBI']
#   Wallet:      ['Default', 'FreeCharge', 'HDFC', 'Payzapp']
#   Credit Card: ['Amex', 'Corporate', 'Default', 'Diners', 'International', 'Maestro', 'Master', 'Visa']
#   Debit Card:  ['Below 2K', 'Above 2K', 'Default', 'Rupay']
#   BNPL:        ['Default', 'Lazypay', 'Pay Later', 'Simple', 'Snapmint']
#   Others:      ['CreditPay', 'Default', 'TwidPay']
MODE_MAP = {
    "UPI":                          {"tab": "UPI",         "method": "Default"},
    "DC Below2K":                   {"tab": "Debit Card",  "method": "Below 2K"},
    "DC Above2K":                   {"tab": "Debit Card",  "method": "Above 2K"},
    "Credit Card":                  {"tab": "Credit Card", "method": "Default"},
    "CC EMI":                       {"tab": "EMI",         "method": "Credit Card"},
    "DC EMI":                       {"tab": "EMI",         "method": "Debit Card"},
    "Debit Card EMI":               {"tab": "EMI",         "method": "Debit Card"},
    "Card Less EMI":                {"tab": "EMI",         "method": "Cardless"},
    "Amex":                         {"tab": "Credit Card", "method": "Amex"},
    "UPI Credit Card (Rupay only)": {"tab": "UPI",         "method": "Credit Card"},
    "Net Banking":                  {"tab": "NetBanking",  "method": "Default"},
    "Diners Credit Card":           {"tab": "Credit Card", "method": "Diners"},
    "Corporate Credit Card":        {"tab": "Credit Card", "method": "Corporate"},
    "Wallets":                      {"tab": "Wallet",      "method": "Default"},
    "BNPL":                         {"tab": "BNPL",        "method": "Default"},
    "International CC":             {"tab": "Credit Card", "method": "International"},
}

# Aliases for fuzzy matching
ALIASES = {
    "upi": "UPI",
    "dc below 2k": "DC Below2K",
    "dc above 2k": "DC Above2K",
    "debit card below 2k": "DC Below2K",
    "debit card above 2k": "DC Above2K",
    "credit card": "Credit Card",
    "cc emi": "CC EMI",
    "credit card emi": "CC EMI",
    "dc emi": "DC EMI",
    "debit card emi": "Debit Card EMI",
    "card less emi": "Card Less EMI",
    "cardless emi": "Card Less EMI",
    "amex": "Amex",
    "american express": "Amex",
    "upi credit card": "UPI Credit Card (Rupay only)",
    "upi credit card (rupay only)": "UPI Credit Card (Rupay only)",
    "rupay credit card": "UPI Credit Card (Rupay only)",
    "net banking": "Net Banking",
    "netbanking": "Net Banking",
    "diners": "Diners Credit Card",
    "diners credit card": "Diners Credit Card",
    "corporate credit card": "Corporate Credit Card",
    "corporate cc": "Corporate Credit Card",
    "wallets": "Wallets",
    "wallet": "Wallets",
    "bnpl": "BNPL",
    "buy now pay later": "BNPL",
    "international cc": "International CC",
    "international credit card": "International CC",
}


def normalize_mode_name(raw_name: str) -> str | None:
    """Normalize a mode name from Rate PDF to a known key in MODE_MAP."""
    cleaned = raw_name.strip()

    # Exact match
    if cleaned in MODE_MAP:
        return cleaned

    # Alias match (case-insensitive)
    lower = cleaned.lower()
    if lower in ALIASES:
        return ALIASES[lower]

    # Fuzzy match against all known names + aliases
    all_names = list(ALIASES.keys())
    matches = get_close_matches(lower, all_names, n=1, cutoff=0.6)
    if matches:
        return ALIASES[matches[0]]

    return None


def map_rates_to_dashboard(extracted_rates: list[dict]) -> dict:
    """
    Map extracted rates to dashboard format.

    Input: [{"mode": "UPI", "rate": 2.5}, ...]
    Output: {
        "mapped": [{"mode": "UPI", "tab": "UPI", "method": "Default", "rate": 2.5}, ...],
        "unmapped": [{"mode": "Unknown Mode", "rate": 1.5}, ...],
    }
    """
    mapped = []
    unmapped = []

    for entry in extracted_rates:
        raw_mode = entry["mode"]
        rate = entry["rate"]
        normalized = normalize_mode_name(raw_mode)

        if normalized and normalized in MODE_MAP:
            mapping = MODE_MAP[normalized]
            mapped.append({
                "original_mode": raw_mode,
                "normalized_mode": normalized,
                "tab": mapping["tab"],
                "method": mapping["method"],
                "rate": rate,
            })
        else:
            unmapped.append({
                "mode": raw_mode,
                "rate": rate,
            })

    return {"mapped": mapped, "unmapped": unmapped}


def group_by_tab(mapped_rates: list[dict]) -> dict:
    """
    Group mapped rates by dashboard tab.

    Returns: {
        "EMI": [{"method": "Credit Card", "rate": 0, ...}, ...],
        "UPI": [{"method": "Default", "rate": 2.5, ...}, ...],
        ...
    }
    """
    tabs = {}
    for entry in mapped_rates:
        tab = entry["tab"]
        if tab not in tabs:
            tabs[tab] = []
        tabs[tab].append({
            "method": entry["method"],
            "rate": entry["rate"],
            "original_mode": entry["original_mode"],
        })
    return tabs
