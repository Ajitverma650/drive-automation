"""Rate comparison service: compare expected rates (from PDF) against actual rates (from dashboard)."""


def compare_rates(expected_mapped: list[dict], actual_tabs: dict) -> tuple[list[dict], list[dict], int]:
    """
    Compare expected rates (from PDF) against actual rates (from dashboard).

    Returns: (discrepancies, matched_entries, total_modes)
    """
    discrepancies = []
    matched_entries = []
    total_modes = 0
    dash_entries_used = set()

    for entry in expected_mapped:
        total_modes += 1
        tab = entry["tab"]
        method = entry["method"]
        original_mode = entry["original_mode"]
        expected_rate = entry["rate"]

        actual_rate = None
        matched_idx = None

        if tab in actual_tabs:
            # Strategy 1: exact match by originalMode
            for i, dash_entry in enumerate(actual_tabs[tab]):
                dash_key = f"{tab}_{i}"
                if dash_key in dash_entries_used:
                    continue
                dash_original = dash_entry.get("originalMode", "") or dash_entry.get("original_mode", "")
                if dash_original == original_mode:
                    actual_rate = dash_entry.get("rate")
                    matched_idx = dash_key
                    break

            # Strategy 2: match by method + exact rate value
            if actual_rate is None:
                for i, dash_entry in enumerate(actual_tabs[tab]):
                    dash_key = f"{tab}_{i}"
                    if dash_key in dash_entries_used:
                        continue
                    if dash_entry.get("method") == method:
                        try:
                            r = float(dash_entry.get("rate", ""))
                            if abs(r - expected_rate) < 0.001:
                                actual_rate = r
                                matched_idx = dash_key
                                break
                        except (ValueError, TypeError):
                            continue

            # Strategy 3: match by method only (first unused)
            if actual_rate is None:
                for i, dash_entry in enumerate(actual_tabs[tab]):
                    dash_key = f"{tab}_{i}"
                    if dash_key in dash_entries_used:
                        continue
                    if dash_entry.get("method") == method:
                        try:
                            actual_rate = float(dash_entry.get("rate", ""))
                        except (ValueError, TypeError):
                            actual_rate = dash_entry.get("rate")
                        matched_idx = dash_key
                        break

        if matched_idx:
            dash_entries_used.add(matched_idx)

        if actual_rate is None:
            discrepancies.append({
                "mode": original_mode,
                "tab": tab,
                "method": method,
                "expected_rate": expected_rate,
                "actual_rate": "NOT FOUND",
            })
        else:
            try:
                actual_float = float(actual_rate)
            except (ValueError, TypeError):
                actual_float = None

            if actual_float is None or abs(actual_float - expected_rate) > 0.001:
                discrepancies.append({
                    "mode": original_mode,
                    "tab": tab,
                    "method": method,
                    "expected_rate": expected_rate,
                    "actual_rate": actual_float if actual_float is not None else str(actual_rate),
                })
            else:
                matched_entries.append({
                    "mode": original_mode,
                    "tab": tab,
                    "method": method,
                    "expected_rate": expected_rate,
                    "actual_rate": actual_float,
                })

    return discrepancies, matched_entries, total_modes
