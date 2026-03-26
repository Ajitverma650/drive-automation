"""Generate discrepancy reports for Phase 2 verification."""

import csv
import io
from datetime import datetime


def generate_report(
    merchant_name: str,
    discrepancies: list[dict],
    total_modes: int,
    matched_entries: list[dict] = None,
) -> dict:
    """
    Generate a verification report with ALL entries (matched + mismatched).

    Returns dict with:
      - summary: text summary
      - csv_content: CSV string with ALL entries (matched + mismatched)
      - has_discrepancies: bool
      - matched: int
      - mismatched: int
      - total: int
      - discrepancies: list of mismatched entries
    """
    mismatched = len(discrepancies)
    matched = total_modes - mismatched

    now = datetime.now().strftime('%d/%m/%Y %H:%M IST')

    if mismatched == 0:
        summary = (
            f"Rate Capture Verification Report\n"
            f"{'=' * 35}\n"
            f"Merchant:    {merchant_name}\n"
            f"Checked by:  Automation (Phase 2)\n"
            f"Date:        {now}\n\n"
            f"RESULT: ALL RATES MATCH - CONFIRMED\n\n"
            f"Summary: {matched} matched, 0 mismatched out of {total_modes} modes\n"
        )
    else:
        disc_lines = []
        for d in discrepancies:
            disc_lines.append(
                f"  {d['mode']:25s} -> Expected {d['expected_rate']}% (Rate PDF), "
                f"Found {d['actual_rate']}% (Dashboard)"
            )

        summary = (
            f"Rate Capture Verification Report\n"
            f"{'=' * 35}\n"
            f"Merchant:    {merchant_name}\n"
            f"Checked by:  Automation (Phase 2)\n"
            f"Date:        {now}\n\n"
            f"RESULT: DISCREPANCIES FOUND - DO NOT CONFIRM\n\n"
            f"Summary: {matched} matched, {mismatched} mismatched out of {total_modes} modes\n\n"
            f"Discrepancies:\n" + "\n".join(disc_lines) + "\n\n"
            f"Action Required:\n"
            f"  1. Maker to correct the above modes\n"
            f"  2. Re-run Phase 1 for corrections\n"
            f"  3. Re-run Phase 2 to verify\n"
        )

    # Generate CSV with ALL entries (matched + mismatched)
    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer)
    writer.writerow(['Mode', 'Tab', 'Method', 'Expected Rate (%)', 'Actual Rate (%)', 'Status'])

    # Write matched entries first
    if matched_entries:
        for m in matched_entries:
            writer.writerow([
                m.get('mode', ''), m.get('tab', ''), m.get('method', ''),
                m.get('expected_rate', ''), m.get('actual_rate', ''), 'MATCHED'
            ])

    # Write mismatched entries
    for d in discrepancies:
        writer.writerow([
            d['mode'], d.get('tab', ''), d.get('method', ''),
            d['expected_rate'], d['actual_rate'], 'MISMATCH'
        ])

    return {
        "summary": summary,
        "csv_content": csv_buffer.getvalue(),
        "has_discrepancies": mismatched > 0,
        "matched": matched,
        "mismatched": mismatched,
        "total": total_modes,
        "discrepancies": discrepancies,
    }
