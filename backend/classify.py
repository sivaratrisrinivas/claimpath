"""Rules that assign a real past decision to the nearest sample Clause, and tag its outcome. Pure functions (no I/O) so evals/ can test them.
Used by scripts/build_precedents.py; evals/run_eval.py measures them against hand labels."""
import re

IN_MAP = [("IN-7.2", r"non[- ]?disclos|suppress(?:ion|ed)|misrepresent|conceal(?:ed|ment)|false statement|fraud"),
          ("IN-4.1", r"pre[- ]?existing|waiting period|exclusion clause 4\.[123]|clause 4\.[123]|first (?:30|thirty) days"),
          ("IN-3.1", r"room rent|proportionate|room category|entitled room|room charges? (?:in excess|limited|restrict)|restricting room charges|disallow\w* .{0,80}room charges|1% of (?:the )?(?:basic )?s(?:um)?\.? ?i"),
          ("IN-9.1", r"cosmetic|plastic surgery|aesthetic")]
US_MAP = [("US-9.4", r"\b(?:CT|MRI|PET|tomograph\w*|magnetic resonance|emergency|emergent|urgent|prior authori[sz]ation|preauthori[sz]ation|ambulance)\b"),
          ("US-11.3", r"cosmetic|aesthetic|appearance|reconstruct"),
          ("US-3.5", r".")]
IN_WINDOW = 650
US_FINDINGS_WINDOW = 260  # the service requested is named in the first sentence; later text often compares against other tests (MRI, CT)
CASE_NO = re.compile(r"\b\d{2}-\d{2,3}-\d{3,4}-\d{2}\b")


def trim_to_first_case(body):
    """Some compilation entries run into the next case (no separator). Cut at the next case number."""
    m = CASE_NO.search(body, 80)
    return body[:m.start()] if m else body


def india_clause(body):
    """IN-7.2 wins if its words appear in the first IN_WINDOW chars; otherwise the earliest-mentioned of the other clauses."""
    w = trim_to_first_case(body)[:IN_WINDOW]
    if re.search(IN_MAP[0][1], w, re.I):
        return "IN-7.2"
    hits = [(m.start(), cid) for cid, rx in IN_MAP[1:] if (m := re.search(rx, w, re.I))]
    return min(hits)[1] if hits else None


def us_clause(treatment_category, treatment_sub, findings, typ):
    f = re.sub(r"^(?:Findings:\s*)?(?:The physician reviewer found that\s*)?(?:Nature of Statutory Criteria/Case Summary:\s*)?", "", findings)
    t = treatment_category + " " + treatment_sub + " " + f[:US_FINDINGS_WINDOW] + " " + typ
    cid = None
    for c, rx in US_MAP:
        if rx == "." or re.search(rx, t, 0 if c == "US-9.4" else re.I):
            cid = c
            break
    if cid == "US-11.3":
        cid = "US-3.5"  # the sample US policy has a cosmetic clause but no rule limits it; folded into medical necessity
    if typ != "Medical Necessity" and cid == "US-9.4":
        return None  # excluded by the builder
    return cid


def outcome_of(t):
    tail = trim_to_first_case(t)[-450:].lower()
    neg = re.search(r"(?<!not )(?<!un)justified|upheld|fails? to succeed|without any relief|dismissed|not entitled|rightly repudiated|no infirmity in the decision|complaint is not tenable|not allowed|\bin order\b", tail)
    pos = re.search(r"\ballowed\b|directed (?:the )?(?:respondent|insurer|company)|award(?:ed)? (?:a |an )?(?:sum|amount)|shall pay|to pay|settle the claim|set aside|in favour of the complainant|liable to pay|(?<!fails to )succeed(?:s|ed)\b|not justified", tail)
    if neg and not pos: return "insurer's decision upheld"
    if pos and not neg: return "complainant succeeded (in whole or part)"
    return None
