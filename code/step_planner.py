"""Step planning and ordering module for HackerRank Orchestrate - Ghost Data Still Exists.

Ensures strict phase ordering, operation ordering, system_id/resource_id tie-breaking,
and 1-based sequential step numbering.
"""

from typing import List, Dict, Any

PHASE_ORDER = {
    "FINDING": 1,
    "REMEDIATION": 2,
    "VERIFICATION": 3
}

OPERATION_ORDER = {
    # Findings
    "REPORT_REMAINING_RECORD": 1,
    "REPORT_EXPOSED_PII": 2,
    "REPORT_ACTIVE_DATA_FLOW": 3,
    "REPORT_RESTORE_RISK": 4,
    
    # Remediation
    "DISABLE_DATA_FLOW": 1,
    "BLOCK_RESTORE": 2,
    "DELETE_RECORD": 3,
    "REDACT_RECORD": 4,
    "ANONYMIZE_RECORD": 5,
    
    # Verification
    "VERIFY_RECORD_ABSENT": 1,
    "VERIFY_RECORD_PRESENT": 2,
    "VERIFY_RECORD_REDACTED": 3,
    "VERIFY_RECORD_ANONYMIZED": 4,
    "VERIFY_DATA_FLOW_DISABLED": 5,
    "VERIFY_RESTORE_BLOCKED": 6
}

def sort_and_number_steps(steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sorts step objects by phase, operation, system_id, resource_id and assigns step_no."""
    def sort_key(s: Dict[str, Any]):
        p_val = PHASE_ORDER.get(s["phase"], 99)
        op_val = OPERATION_ORDER.get(s["operation"], 99)
        sys_val = str(s.get("system_id", ""))
        res_val = str(s.get("resource_id", ""))
        return (p_val, op_val, sys_val, res_val)

    sorted_steps = sorted(steps, key=sort_key)
    
    # Re-number consecutively starting at 1
    result = []
    for idx, s in enumerate(sorted_steps, 1):
        item = {
            "step_no": idx,
            "phase": s["phase"],
            "system_id": s["system_id"],
            "resource_id": s["resource_id"],
            "operation": s["operation"],
            "state": s["state"],
            "evidence_id": s["evidence_id"] if s.get("evidence_id") else ""
        }
        result.append(item)
    return result
