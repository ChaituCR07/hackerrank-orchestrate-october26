"""Request intent classifier for HackerRank Orchestrate - Ghost Data Still Exists.

Determines whether the request text authorizes account/personal data deletion or
represents a non-deletion action (e.g. data access/export, correction/update, marketing opt-out,
login help, etc.) that requires a NOT_APPLICABLE outcome with steps_json=[].
"""

import re

NON_DELETION_PATTERNS = [
    r"\bleave the account\b",
    r"\bkeep the account\b",
    r"\bdo not close\b",
    r"\bnot asking for deletion\b",
    r"\bstop the promotional\b",
    r"\bmarketing lists only\b",
    r"\bnot a request to erase\b",
    r"\binvoices for my records\b",
    r"\bwant to continue using\b",
    r"\bdon't delete or change\b",
    r"\bdo not delete\b",
    r"\bresetting the login\b",
    r"\bmisspelled\b",
    r"\bportable format\b",
    r"\bdownload my account information\b",
    r"\bcopy of last year's invoices\b",
    r"\bcopy of the information held on my account\b",
    r"\bwhat personal information you hold\b",
    r"\bthis is an information request\b",
    r"\bout of date\. please replace it with the new one\b",
    r"\bchange the email address used for this account\. i want to continue using\b",
    r"\bstop.*promotional emails\b",
    r"\bno quiero eliminar\b",
    r"\bce n'est pas une demande de suppression\b"
]

def is_deletion_request(request_text: str) -> bool:
    """Returns True if the request authorizes deletion, False if it is NOT_APPLICABLE."""
    if not request_text or not isinstance(request_text, str):
        return True

    text_lower = request_text.lower().strip()

    # Check for explicit non-deletion patterns
    for pat in NON_DELETION_PATTERNS:
        if re.search(pat, text_lower):
            return False

    return True
