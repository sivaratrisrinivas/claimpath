"""Letter drafting by template from the graph results. The product never files or sends anything: this is text for the user.
Anything that came from a what-if is bracketed so the user only asserts facts they can actually prove."""
import re


def _money(cur, n):
    return f"Rs {n:,.0f}" if cur == "INR" else f"${n:,.2f}"


def build(r):
    case, pol, v, rule, clock = r["case"], r["policy"], r["verdict"], r["strongest"], r["clock"]
    country, cur = case["country"], case["currency"]
    rej = r["rejection"]
    lines = []
    A = lines.append
    due = {d["id"]: d for d in clock["deadlines"]}
    facts = {}
    if rule:
        for f in rule["facts"]:
            facts[f["key"]] = f
    prior = facts.get("prior_cover_start")
    ed = facts.get("ed_encounter_record")

    if country == "IN":
        A(f"To: The Grievance Redressal Officer, {pol['insurer'].replace(' (fictional)', '')}")
        A("Date: [DATE]")
        A(f"Policy no.: [POLICY NUMBER]    Claim no.: [CLAIM NUMBER]    Insured: [YOUR NAME]")
        A("Subject: Grievance against repudiation of my claim - request for reconsideration (sent in writing under the IRDAI grievance process)")
        A("")
        A("Dear Sir/Madam,")
        A("")
        A(f"1. My claim for hospitalisation from {case['claim_date']} (claimed {_money(cur, rej['amount'])}) was repudiated by your letter received on {case['rejection_received']}. "
          f"The stated reason was: \"{r['reason']}\" You relied on Clause {r['clause']['no']} ({r['clause']['title']}) of the policy.")
        A("")
        if v["code"] == "likely_contestable" and rule:
            if prior and prior["assumed"]:
                A(f"2. [CONFIRM AND ATTACH BEFORE SENDING - only if true] My cover with {pol['insurer'].replace(' (fictional)', '')} began on {pol['start_date']}, but I held continuous health cover from {prior['value']} "
                  "and ported it to you without a break. Under the portability rules, the credits earned (including the moratorium period) carry over.")
            elif prior and prior["provided"]:
                A(f"2. I held continuous health cover from {prior['value']}, evidenced by the enclosed documents, and ported it to you without a break.")
            A(f"   {rule['eval']['why']}")
            A(f"   {rule['citation']} states: {rule['summary']} (Source: {rule['source_url']})")
            A(f"   Accordingly, a claim cannot be contested on grounds of non-disclosure or misrepresentation, absent established fraud, and I request that the repudiation be withdrawn and the claim settled as per the policy terms.")
        elif v["code"] == "undecidable" and rule:
            A(f"2. {rule['citation']} states: {rule['summary']} (Source: {rule['source_url']})")
            A(f"   Your letter does not say how much continuous cover (including any ported/migrated credit) you counted for this policy. Please state in writing the continuous-coverage start date you recorded, "
              "and the dates of every earlier policy you hold on record for me.")
            A("   [IF YOU FIND PROOF OF EARLIER CONTINUOUS COVER, ADD IT HERE AND ATTACH IT - see the missing-facts list]")
        else:
            A(f"2. I request the full basis of the decision. {'; '.join(r['verdict']['because'])}")
            A("   Please provide a copy of the Claims Review Committee / PMC approval record and the specific policy terms relied on (IRDAI Master Circular on Health Insurance Business, 29 May 2024, item 17; "
              f"Source: {r['candidates'][0]['source_url'] if r['candidates'] else 'https://irdai.gov.in'}).")
        b = r.get("bill") or {}
        if b.get("has_bill"):
            A("")
            A(f"3. Bill reconciliation: total billed {_money(cur, b['total_billed'])}; on the policy's room-rent clause the room-linked charges ({_money(cur, b['room_linked_total'])}) may be reduced proportionately "
              f"(about {_money(cur, b['proportionate_deduction'])}); I ask that medicines, diagnostics and implants are not reduced and that any deduction is shown line by line.")
        A("")
        A("4. Kindly resolve this within two weeks of receipt (IRDAI policyholder portal: https://policyholder.gov.in/how-to-make-a-complaint) and send me a written, reasoned reply. "
          "If it is rejected, unanswered for one month, or unsatisfactory, I intend to approach the Insurance Ombudsman under rule 14(3) of the Insurance Ombudsman Rules, 2017.")
        d4 = due.get("D-IN-4")
        encl = ["Rejection letter", "Policy schedule", "Discharge summary and hospital bills"] + (["Proof of earlier continuous cover [ATTACH ONLY IF YOU HAVE IT]"] if prior else [])
    else:
        A("To: Appeals Department / Plan Administrator, " + pol["insurer"].replace(" (fictional)", ""))
        A("Date: [DATE]")
        A("Member ID: [MEMBER ID]    Claim no.: [CLAIM NUMBER]    Patient: [YOUR NAME]")
        A("Subject: Appeal of adverse benefit determination - request for full and fair review")
        A("")
        A("To the Appeals Department:")
        A("")
        A(f"1. I am appealing the denial (notice received {case['rejection_received']}) of {_money(cur, rej['amount'])} for services on {case['claim_date']}. Stated reason: \"{r['reason']}\" "
          f"You cited Plan section {r['clause']['no']} ({r['clause']['title']}).")
        A("")
        if v["code"] == "likely_contestable" and rule:
            if ed and ed["assumed"]:
                A(f"2. [CONFIRM AND ATTACH BEFORE SENDING - only if true] The enclosed hospital record shows the service was ordered during my emergency-department visit on {case['claim_date']}.")
            else:
                A(f"2. The enclosed hospital record shows the service was ordered during my emergency-department visit on {case['claim_date']}.")
            A(f"   {rule['citation']}: {rule['summary']} (Source: {rule['source_url']})")
            A("   Prior authorization therefore could not be required, and the denial should be reversed and the claim reprocessed.")
        elif v["code"] == "undecidable" and rule:
            A(f"2. {rule['citation']}: {rule['summary']} (Source: {rule['source_url']})")
            A("   Please confirm whether the service was furnished as part of an emergency-department encounter, and identify the records you reviewed.")
            A("   [IF YOU OBTAIN THE ED RECORD SHOWING THE ORDER TIME, ADD IT HERE AND ATTACH IT - see the missing-facts list]")
        else:
            A(f"2. I request the specific basis for this decision. {'; '.join(r['verdict']['because'])}")
            A("   For a medical-necessity decision, please provide the clinical explanation and the internal criteria used (29 CFR 2560.503-1(g)(1)(v); Source: https://www.ecfr.gov/current/title-29/subtitle-B/chapter-XXV/subchapter-F/part-2560/section-2560.503-1).")
        A("")
        A("3. Under 29 CFR 2560.503-1(h)(2)(iii) I request, free of charge, copies of all documents, records and other information relevant to this claim, including the authorization log and any criteria applied. "
          "I also request that the review be conducted by a fiduciary who did not make the initial decision and, where medical judgment is involved, with a qualified health professional (h)(3)(ii)-(iii).")
        b = r.get("bill") or {}
        if b.get("has_bill"):
            A("")
            A(f"4. Claim reconciliation: {b['note']} Please reprocess the denied line(s) and issue a corrected explanation of benefits.")
        A("")
        A("5. Please decide this appeal within the time allowed for post-service claims (60 days for a single-level plan; 30 days per level if the plan has two). "
          "I reserve my right to independent external review (45 CFR 147.136) and all other remedies.")
        d4 = due.get("D-US-1")
        encl = ["Denial notice / EOB", "Plan summary page with the cited section", "Hospital ED record [ATTACH ONLY IF YOU HAVE IT]"]
    A("")
    A("Sincerely,")
    A("[YOUR NAME]    [ADDRESS]    [PHONE / EMAIL]")
    A("")
    A("Enclosures: " + "; ".join(encl))
    A("")
    if d4 and d4["due"]:
        A(f"[NOT PART OF THE LETTER] Your clock: {d4['label']} -> {d4['due']} ({d4['days_left']} days from {clock['as_of']}).")
    A("[NOT PART OF THE LETTER] Draft prepared by ClaimPath from public rules and your sample data. Not legal or medical advice. You send it yourself; ClaimPath files and contacts no one.")
    text = "\n".join(lines)
    ph = [x for x in sorted(set(re.findall(r"\[[A-Z][^\]]*\]", text))) if not x.startswith("[NOT PART")]
    return {"text": text, "placeholders": ph[:12]}
