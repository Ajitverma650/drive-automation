"""Extraction orchestration service: builds step-by-step logs for Phase 1."""


def build_phase1_steps(agreement: dict, tabs: dict, mapping: dict) -> list[dict]:
    """Build a step-by-step log of what the automation will do."""
    steps = []

    steps.append({
        "step": 1,
        "action": "extract_pdfs",
        "description": "Extract data from both PDFs",
        "details": {
            "start_date": agreement["start_date"],
            "end_date": agreement.get("end_date"),
            "rates_found": sum(len(v) for v in tabs.values()),
            "unmapped": len(mapping.get("unmapped", [])),
        }
    })

    steps.append({
        "step": 2,
        "action": "upload_agreement",
        "description": f"Upload Agreement PDF: {agreement['file_name']}",
    })

    steps.append({
        "step": 3,
        "action": "fill_agreement",
        "description": "Fill Agreement Details",
        "details": {
            "start_date": agreement["start_date"],
            "end_date": agreement.get("end_date"),
            "merchant_size": agreement["merchant_size"],
            "merchant_type": agreement["merchant_type"],
            "purchased_products": agreement["purchased_products"],
        }
    })

    steps.append({
        "step": 4,
        "action": "save_agreement",
        "description": "Click Save -> Checkout section appears",
    })

    step_num = 5
    for tab_name, entries in tabs.items():
        for entry in entries:
            steps.append({
                "step": step_num,
                "action": "fill_rate",
                "description": f"[{tab_name}] Set {entry['method']} = {entry['rate']}%",
                "details": {
                    "tab": tab_name,
                    "method": entry["method"],
                    "rate": entry["rate"],
                    "original_mode": entry["original_mode"],
                    "pricing_type": "Flat",
                    "commission_type": "Percentage",
                }
            })
            step_num += 1

    steps.append({
        "step": step_num,
        "action": "save_checkout",
        "description": "Click Save (NOT Confirm - awaits Phase 2)",
    })

    return steps
