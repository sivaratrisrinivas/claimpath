"""ClaimPath seed data. EVERYTHING about the two sample cases is SYNTHETIC (invented people, insurers, numbers).
The RULES are real: each has a source_url to the official text it was read from, plus a `verification` note."""

REV = 5  # bump when the data changes: the app re-seeds on cold start when the stored revision differs

IRDAI_MC = ("https://irdai.gov.in/documents/37343/365525/%e0%a4%b8%e0%a5%8d%e0%a4%b5%e0%a4%be%e0%a4%b8%e0%a5%8d%e0%a4%a5%e0%a5%8d%e0%a4%af+"
            "%e0%a4%ac%e0%a5%80%e0%a4%ae%e0%a4%be+%e0%a4%b5%e0%a5%8d%e0%a4%af%e0%a4%b5%e0%a4%b8%e0%a4%be%e0%a4%af+%e0%a4%aa%e0%a4%b0+"
            "%e0%a4%ae%e0%a4%be%e0%a4%b8%e0%a5%8d%e0%a4%9f%e0%a4%b0+%e0%a4%aa%e0%a4%b0%e0%a4%bf%e0%a4%aa%e0%a4%a4%e0%a5%8d%e0%a4%b0+_+"
            "Master+Circular++on+Health++Insurance+Business++29052024.pdf/5e707a91-b5de-1ec1-cf18-b66273a6839d?t=1716962621002&version=1.0")
ECFR_29_2560 = "https://www.ecfr.gov/current/title-29/subtitle-B/chapter-XXV/subchapter-F/part-2560/section-2560.503-1"
ECFR_45_147_136 = "https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-B/part-147/section-147.136"
ECFR_45_149_110 = "https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-B/part-149/subpart-B/section-149.110"

CASES = [
    dict(id="IN-01", country="IN", flag="IN", currency="INR", title="Meera, 41 - angioplasty claim rejected for 'non-disclosure'",
         summary="SYNTHETIC SAMPLE. Insurer rejected a Rs 3,18,500 cashless-turned-reimbursement claim saying hypertension and diabetes were not disclosed in the 2023 proposal form. Meera had been insured with another insurer since 2018 and ported in 2023.",
         claim_date="2026-08-12", rejection_received="2026-09-28", insurer="Sample Suraksha Health Insurance Ltd (fictional)"),
    dict(id="US-01", country="US", flag="US", currency="USD", title="Daniel, 52 - ER chest-pain CT denied: 'no prior authorization'",
         summary="SYNTHETIC SAMPLE. Employer-sponsored PPO denied a $3,850 CT angiogram after an ER visit for chest pain, saying prior authorization was not on file. The same plan paid the ER visit itself.",
         claim_date="2026-07-03", rejection_received="2026-09-14", insurer="Sample Mutual Health Plan (fictional)"),
]

POLICIES = [
    dict(id="POL-IN-01", case_id="IN-01", insurer="Sample Suraksha Health Insurance Ltd (fictional)", product="Suraksha Family Floater (synthetic)",
         start_date="2023-01-15", sum_insured=500000, currency="INR", doc="Policy wording v4, synthetic"),
    dict(id="POL-US-01", case_id="US-01", insurer="Sample Mutual Health Plan (fictional)", product="Employer PPO 2026 (synthetic)",
         start_date="2026-01-01", sum_insured=0, currency="USD", doc="Summary Plan Description, synthetic"),
]

# kind: exclusion | condition | limit
CLAUSES = [
    dict(id="IN-3.1", policy_id="POL-IN-01", no="3.1", title="Room rent limit", kind="limit", page="p.6",
         text="Room rent, boarding and nursing charges are payable up to 1% of the Sum Insured per day for a normal room.",
         keywords=["room rent", "room category", "boarding", "eligible room"], room_pct=0.01),
    dict(id="IN-3.2", policy_id="POL-IN-01", no="3.2", title="Proportionate deduction", kind="limit", page="p.6",
         text="If the room occupied is costlier than the eligible room, all room-linked charges (surgeon, anaesthetist, OT, nursing and procedure charges) are reduced in the same proportion. Medicines, diagnostics and implants are not reduced.",
         keywords=["proportionate", "proportion", "deduction", "pro-rata", "pro rata"]),
    dict(id="IN-4.1", policy_id="POL-IN-01", no="4.1", title="Pre-existing disease waiting period", kind="exclusion", page="p.8",
         text="Pre-existing diseases are not covered until 36 months of continuous coverage have been completed.",
         keywords=["waiting period", "pre-existing", "pre existing", "ped", "36 months"]),
    dict(id="IN-7.2", policy_id="POL-IN-01", no="7.2", title="Non-disclosure / misrepresentation", kind="condition", page="p.14",
         text="The Company may repudiate a claim if any material fact was misrepresented or not disclosed in the proposal form.",
         keywords=["non-disclosure", "non disclosure", "not disclosed", "misrepresent", "concealed", "suppress", "material fact", "proposal form", "hypertension", "diabetes"]),
    dict(id="IN-9.1", policy_id="POL-IN-01", no="9.1", title="Exclusion: cosmetic surgery", kind="exclusion", page="p.17",
         text="Cosmetic, aesthetic or plastic surgery is excluded unless it is reconstructive surgery following an accident or cancer.",
         keywords=["cosmetic", "aesthetic", "plastic", "beauty"]),
    dict(id="US-9.4", policy_id="POL-US-01", no="9.4", title="Prior authorization for advanced imaging", kind="condition", page="p.31",
         text="Benefits for CT, MRI and PET imaging are payable only when the Plan has approved the service in advance (prior authorization).",
         keywords=["prior authorization", "preauthorization", "pre-authorization", "precertification", "authorization", "not authorized", "advanced imaging", "ct", "mri"]),
    dict(id="US-3.5", policy_id="POL-US-01", no="3.5", title="Medical necessity", kind="condition", page="p.12",
         text="The Plan pays only for services it determines are medically necessary under its clinical criteria.",
         keywords=["medical necessity", "medically necessary", "not necessary", "experimental", "investigational"]),
    dict(id="US-11.3", policy_id="POL-US-01", no="11.3", title="Exclusion: cosmetic services", kind="exclusion", page="p.44",
         text="Services whose primary purpose is to improve appearance are excluded.",
         keywords=["cosmetic", "appearance", "aesthetic"]),
]

REJECTIONS = [
    dict(id="REJ-IN-01", case_id="IN-01", cites="IN-7.2", received="2026-09-28", amount=318500,
         reason="Claim repudiated under Clause 7.2: hypertension and type-2 diabetes were not disclosed in the proposal form dated 15 Jan 2023 (non-disclosure of material facts)."),
    dict(id="REJ-US-01", case_id="US-01", cites="US-9.4", received="2026-09-14", amount=3850,
         reason="Denied: no prior authorization on file for CT angiography of the chest (CPT 71275), as required by Plan section 9.4. Remark code CO-197."),
]

# FactType: something a rule needs to know. assume_* = what you would be asserting in the what-if (clearly labelled synthetic).
FACTS = [
    dict(key="claim_date", label="Date of admission / service", how_to_find="Discharge summary or bill.", assume_label="", assume_value=""),
    dict(key="current_cover_start", label="Cover start date with this insurer", how_to_find="Policy schedule / first policy certificate.", assume_label="", assume_value=""),
    dict(key="prior_cover_start", label="Proof of earlier continuous cover (previous policy start + portability acceptance)",
         how_to_find="Old policy schedules and renewal receipts, the portability acceptance mail, or the insurer's own policy history (ask the insurer in writing). Look for a gap of more than the grace period between policies.",
         assume_label="Add proof: earlier policy began 1 Apr 2018 and was ported in without a break", assume_value="2018-04-01"),
    dict(key="ed_encounter_record", label="Hospital record showing the CT was ordered during an emergency-department visit",
         how_to_find="Ask the hospital's medical-records office for the ED discharge summary and the CT order timestamp (you have a right of access to your own records).",
         assume_label="Add record: ED discharge summary shows CT ordered by the ED physician at 21:14 on 3 Jul 2026 (synthetic)", assume_value="ED discharge summary, CT ordered 2026-07-03 21:14"),
]

# Evidence (kind: document | adverse | bill_line). proves = [(fact_key, value)]
EVIDENCE = [
    dict(id="EV-IN-1", case_id="IN-01", kind="document", label="Policy schedule: cover start 15 Jan 2023, Sum Insured Rs 5,00,000", doc="Policy schedule p.1", date="2023-01-15", proves=[("current_cover_start", "2023-01-15")]),
    dict(id="EV-IN-2", case_id="IN-01", kind="document", label="Discharge summary: admitted 12 Aug 2026, angioplasty with stent", doc="Hospital discharge summary", date="2026-08-12", proves=[("claim_date", "2026-08-12")]),
    dict(id="EV-IN-3", case_id="IN-01", kind="adverse", label="Proposal form (15 Jan 2023): 'Any pre-existing disease?' answered 'No'", doc="Proposal form q.14", date="2023-01-15", proves=[]),
    dict(id="EV-IN-4", case_id="IN-01", kind="document", label="Rejection letter dated 26 Sep 2026, received 28 Sep 2026", doc="Insurer letter", date="2026-09-28", proves=[]),
    # hospital bill lines (INR). room_linked: reduced under proportionate deduction. payable False = non-payable item.
    dict(id="BL-IN-1", case_id="IN-01", kind="bill_line", seq=1, label="Room rent, 4 days x Rs 7,500", category="Room rent", amount=30000, room_linked=False, payable=True, days=4, rate=7500),
    dict(id="BL-IN-2", case_id="IN-01", kind="bill_line", seq=2, label="Surgeon & anaesthetist fees", category="Professional fees", amount=80000, room_linked=True, payable=True),
    dict(id="BL-IN-3", case_id="IN-01", kind="bill_line", seq=3, label="OT & procedure charges", category="OT charges", amount=45000, room_linked=True, payable=True),
    dict(id="BL-IN-4", case_id="IN-01", kind="bill_line", seq=4, label="Coronary stent (implant)", category="Implants", amount=95000, room_linked=False, payable=True),
    dict(id="BL-IN-5", case_id="IN-01", kind="bill_line", seq=5, label="Medicines", category="Medicines", amount=38000, room_linked=False, payable=True),
    dict(id="BL-IN-6", case_id="IN-01", kind="bill_line", seq=6, label="Diagnostics (ECG, echo, angiogram)", category="Diagnostics", amount=22000, room_linked=False, payable=True),
    dict(id="BL-IN-7", case_id="IN-01", kind="bill_line", seq=7, label="Consumables on non-payable list", category="Non-payable", amount=8500, room_linked=False, payable=False),
    dict(id="EV-US-1", case_id="US-01", kind="document", label="ER visit and CT on 3 Jul 2026 (hospital claim, same date of service)", doc="EOB p.1", date="2026-07-03", proves=[("claim_date", "2026-07-03")]),
    dict(id="EV-US-2", case_id="US-01", kind="document", label="Denial notice dated 12 Sep 2026, received 14 Sep 2026: CO-197 'authorization absent'", doc="EOB / denial notice", date="2026-09-14", proves=[]),
    dict(id="EV-US-3", case_id="US-01", kind="adverse", label="Plan's authorization log: no request on file for CPT 71275", doc="Denial notice", date="2026-09-12", proves=[]),
    dict(id="EV-US-4", case_id="US-01", kind="document", label="Plan PAID the ER visit (99285) the same day - suggests an emergency presentation but does not show the CT was ordered in the ED", doc="EOB line 1", date="2026-07-03", proves=[]),
    dict(id="BL-US-1", case_id="US-01", kind="bill_line", seq=1, label="ED visit, level 5 (99285)", category="ER visit", amount=2900, paid=2320, patient=580, carc="", room_linked=False, payable=True),
    dict(id="BL-US-2", case_id="US-01", kind="bill_line", seq=2, label="Troponin x2 (84484)", category="Lab", amount=410, paid=328, patient=82, carc="", room_linked=False, payable=True),
    dict(id="BL-US-3", case_id="US-01", kind="bill_line", seq=3, label="ECG (93005)", category="ECG", amount=180, paid=144, patient=36, carc="", room_linked=False, payable=True),
    dict(id="BL-US-4", case_id="US-01", kind="bill_line", seq=4, label="CT angiogram chest (71275)", category="Advanced imaging", amount=3850, paid=0, patient=3850, carc="CO-197", room_linked=False, payable=True),
]

# Rules: REAL, each with a source URL. kind: months_threshold | all_facts | none.  effect: bars | procedural | remedy
RULES = [
    dict(id="R-IN-MORATORIUM", jurisdiction="IN", name="60-month moratorium on contesting for non-disclosure", effect="bars", kind="months_threshold", threshold=60, terminal=False,
         citation="IRDAI Master Circular on Health Insurance Business, 29 May 2024, item 13 ('Policy/Claim cannot be contested')",
         summary="No health policy or claim is contestable for non-disclosure or misrepresentation after 60 months of continuous coverage, except established fraud. Credits from ported/migrated policies count.",
         source_url=IRDAI_MC, source_alt="https://taxguru.in/corporate-law/master-circular-irdai-insurance-productsregulations-2024health-insurance.html",
         verification="Wording read from the IRDAI PDF text (via search extract) and a TaxGuru copy. Applies to policies under the 2024 framework; older-policy applicability not checked."),
    dict(id="R-IN-PED36", jurisdiction="IN", name="Pre-existing disease waiting period is capped at 36 months; earned credit carries over", effect="bars", kind="months_threshold", threshold=36, terminal=False,
         citation="IRDAI Master Circular on Health Insurance Business, 29 May 2024 (credit carry-forward on porting/migration); 36-month cap per IRDAI 2024 amendments",
         summary="PED waiting periods may not exceed 36 months and waiting-period credit accrued earlier is carried forward to the new policy.",
         source_url=IRDAI_MC, source_alt="https://www.cnbctv18.com/personal-finance/insurance-irdai-reduces-waiting-period-moratorium-lower-how-will-health-policies-benefit-19396754.htm",
         verification="Carry-forward is in the circular text; the 36-month cap is confirmed only by secondary reporting (CNBC-TV18, BusinessLine). Verify in the gazette before relying on it."),
    dict(id="R-IN-CITE", jurisdiction="IN", name="Repudiation needs committee approval and must cite the specific policy terms", effect="procedural", kind="none", threshold=0, terminal=False,
         citation="IRDAI Master Circular on Health Insurance Business, 29 May 2024, item 17 (Settlement of claims)",
         summary="No claim may be repudiated without approval of the Product Management Committee or a three-member Claims Review Committee, and the insurer must give full details referencing the specific terms of the policy.",
         source_url=IRDAI_MC, source_alt="https://taxguru.in/corporate-law/master-circular-irdai-insurance-productsregulations-2024health-insurance.html",
         verification="Wording read from the IRDAI PDF text and a TaxGuru copy."),
    dict(id="R-IN-GRO", jurisdiction="IN", name="Step 1 - written grievance to the insurer (to be resolved within two weeks)", effect="remedy", kind="none", threshold=0, terminal=False,
         citation="IRDAI policyholder portal: 'How to make a complaint'",
         summary="Complain in writing with supporting documents, keep a dated acknowledgement. The insurer should resolve it not later than two weeks from receipt; if not resolved or unsatisfactory you may escalate.",
         source_url="https://policyholder.gov.in/how-to-make-a-complaint", source_alt="",
         verification="Read on the official IRDAI policyholder portal."),
    dict(id="R-IN-BB", jurisdiction="IN", name="Step 2 - IRDAI Bima Bharosa complaint portal", effect="remedy", kind="none", threshold=0, terminal=False,
         citation="IRDAI Bima Bharosa grievance management system",
         summary="Complaints registered on Bima Bharosa are shown as 'attended to within 14 days'. You file it yourself, as the insured.",
         source_url="https://bimabharosa.irdai.gov.in/", source_alt="",
         verification="Read the 14-day statement on the portal home page. Escalation conditions beyond that not encoded."),
    dict(id="R-IN-OMB", jurisdiction="IN", name="Step 3 - Insurance Ombudsman (free, claims up to Rs 50 lakh)", effect="remedy", kind="none", threshold=0, terminal=True,
         citation="Insurance Ombudsman Rules, 2017, rule 14(3); Council for Insurance Ombudsmen procedure page",
         summary="First make a written representation to the insurer. You may go to the Ombudsman if it is rejected, unanswered for one month, or unsatisfactory, and must file within one year. Not allowed if the same matter is in court, consumer forum or arbitration.",
         source_url="https://www.indiacode.nic.in/ViewFileUploaded?file=the_insurance_ombudsman_rules%2C_2017_-_last_amended_on_18.5.2021.pdf&path=AC_CEN_2_45_00001_199941_1517807320115%2Frulesindividualfile%2F",
         source_alt="https://www.cioins.co.in/Procedure/Index",
         verification="Rule 14(3) text and the Rs 50 lakh / one-year guidance read on indiacode.nic.in and cioins.co.in."),
    dict(id="R-US-EMERG", jurisdiction="US", name="Emergency services must be covered without prior authorization", effect="bars", kind="all_facts", threshold=0, terminal=False,
         citation="45 CFR 149.110(b)(1) (Public Health Service Act sec. 2799A-1), applies to group health plans and issuers",
         summary="If a plan covers emergency-department services, it must cover emergency services without any prior-authorization determination, even out of network.",
         source_url=ECFR_45_149_110, source_alt="https://www.law.cornell.edu/uscode/text/42/300gg-111",
         verification="Operative text read on eCFR (45 CFR 149.110). Whether a specific service counts as 'emergency services' is a question of fact for the plan and, on appeal, a reviewer."),
    dict(id="R-US-NOTICE", jurisdiction="US", name="A denial must state the specific reason and the plan provisions relied on", effect="procedural", kind="none", threshold=0, terminal=False,
         citation="29 CFR 2560.503-1(g)(1) (ERISA claims procedure); medical-necessity explanation at (g)(1)(v)(B)",
         summary="The notice must give the specific reason, reference the specific plan provisions, describe info needed to perfect the claim, and explain review procedures and time limits. For medical-necessity denials the plan must give the clinical explanation (or offer it free on request).",
         source_url=ECFR_29_2560, source_alt="",
         verification="Operative text read on eCFR."),
    dict(id="R-US-INT", jurisdiction="US", name="Step 1 - internal appeal (at least 180 days to file; decision within 60 days)", effect="remedy", kind="none", threshold=0, terminal=False,
         citation="29 CFR 2560.503-1(h)(3)(i), (h)(2)(iii), (i)(2)(iii); Public Health Service Act sec. 2719 / 45 CFR 147.136",
         summary="Group health plans must allow at least 180 days to appeal, give you free copies of the claim file, and decide a post-service appeal within 60 days (30 days per level if the plan has two levels).",
         source_url=ECFR_29_2560, source_alt=ECFR_45_147_136,
         verification="Operative text read on eCFR. Fully insured plans may also be subject to stricter state rules."),
    dict(id="R-US-EXT", jurisdiction="US", name="Step 2 - independent external review (4 months to request; 45-day decision)", effect="remedy", kind="none", threshold=0, terminal=True,
         citation="45 CFR 147.136(c)-(d); HHS-administered federal external review process",
         summary="After a final internal denial you have four months to request review by an independent review organization, which must decide a standard review within 45 days. The decision is binding on the plan.",
         source_url=ECFR_45_147_136, source_alt="https://www.cms.gov/cciio/programs-and-initiatives/consumer-support-and-information/csg-ext-appeals-facts",
         verification="Four-month and 45-day figures read on eCFR and CMS. State vs federal process depends on the plan type."),
]

# Rule graph edges (for PageRank and shortestPath): (from, to, kind)
RULE_EDGES = [
    ("R-IN-PED36", "R-IN-MORATORIUM", "supports"), ("R-IN-CITE", "R-IN-MORATORIUM", "supports"),
    ("R-IN-CITE", "R-IN-PED36", "supports"),
    ("R-IN-GRO", "R-IN-BB", "escalates"), ("R-IN-GRO", "R-IN-OMB", "escalates"), ("R-IN-BB", "R-IN-OMB", "escalates"),
    ("R-US-NOTICE", "R-US-EMERG", "supports"),
    ("R-US-INT", "R-US-EXT", "escalates"),
]
# Clause -[:LIMITED_BY]-> Rule : the rule that limits how the clause may be applied
LIMITED_BY = [
    ("IN-7.2", "R-IN-MORATORIUM", "A non-disclosure repudiation cannot stand once 60 months of continuous cover are complete"),
    ("IN-7.2", "R-IN-CITE", "Any repudiation must cite specific policy terms and be committee-approved"),
    ("IN-4.1", "R-IN-PED36", "Waiting period is capped at 36 months and credit carries over on porting"),
    ("IN-4.1", "R-IN-CITE", "Any repudiation must cite specific policy terms and be committee-approved"),
    ("US-9.4", "R-US-EMERG", "Prior authorization cannot be required for emergency services"),
    ("US-9.4", "R-US-NOTICE", "Denial must state the specific reason and plan provision"),
    ("US-3.5", "R-US-NOTICE", "Medical-necessity denial needs a clinical explanation"),
]
# Rule -[:REQUIRES {role}]-> FactType
REQUIRES = [
    ("R-IN-MORATORIUM", "claim_date", "core"), ("R-IN-MORATORIUM", "current_cover_start", "core"), ("R-IN-MORATORIUM", "prior_cover_start", "extends"),
    ("R-IN-PED36", "claim_date", "core"), ("R-IN-PED36", "current_cover_start", "core"), ("R-IN-PED36", "prior_cover_start", "extends"),
    ("R-US-EMERG", "ed_encounter_record", "core"),
]
# Rejection -[:APPEAL_VIA]-> first remedy rule
APPEAL_VIA = [("REJ-IN-01", "R-IN-GRO"), ("REJ-US-01", "R-US-INT")]

# Deadline: anchor = rejection_received | filing | final_determination | external_request ; kind = you_must | they_must
DEADLINES = [
    dict(id="D-IN-1", rule="R-IN-GRO", ord=1, label="Insurer should resolve your written grievance", amount=14, unit="days", anchor="filing", kind="they_must"),
    dict(id="D-IN-2", rule="R-IN-BB", ord=2, label="Bima Bharosa: complaint 'attended to' (portal statement)", amount=14, unit="days", anchor="filing", kind="they_must"),
    dict(id="D-IN-3", rule="R-IN-OMB", ord=3, label="Ombudsman door opens if the insurer has not replied", amount=1, unit="months", anchor="filing", kind="they_must"),
    dict(id="D-IN-4", rule="R-IN-OMB", ord=4, label="LAST DAY to file with the Ombudsman (conservative: 1 year from the rejection)", amount=12, unit="months", anchor="rejection_received", kind="you_must"),
    dict(id="D-US-1", rule="R-US-INT", ord=1, label="LAST DAY to file your internal appeal (180 days)", amount=180, unit="days", anchor="rejection_received", kind="you_must"),
    dict(id="D-US-2", rule="R-US-INT", ord=2, label="Plan should decide a post-service appeal", amount=60, unit="days", anchor="filing", kind="they_must"),
    dict(id="D-US-3", rule="R-US-EXT", ord=3, label="Request external review (4 months after the final internal denial)", amount=4, unit="months", anchor="final_determination", kind="you_must"),
    dict(id="D-US-4", rule="R-US-EXT", ord=4, label="Independent reviewer should decide (standard review)", amount=45, unit="days", anchor="external_request", kind="they_must"),
]


# ---- Precedents: REAL, PUBLIC, PAST decisions (built by scripts/build_precedents.py; see README for sources and caveats).
# They never feed the live verdict (that stays driven by the synthetic cases + real rules); they are context shown after the agent runs.
import json as _json, os as _os
_P = _json.load(open(_os.path.join(_os.path.dirname(__file__), "precedents.json"), encoding="utf8"))
PRECEDENTS = []
for _x in _P["india"] + _P["us"]:
    _won = ("succeeded" in _x["outcome"]) or ("overturned" in _x["outcome"])
    PRECEDENTS.append(dict(id=_x["id"], jurisdiction=_x["jurisdiction"], source_kind=_x["source_kind"], case_ref=_x["case_ref"], forum=_x["forum"],
                           year=_x["year"], claim_type=_x["claim_type"], amount=_x["amount"], currency=_x["currency"], clause_id=_x["clause_id"],
                           clause_ref=_x.get("clause_ref", ""), reason=_x["reason"], outcome=_x["outcome"], outcome_class="claimant" if _won else "insurer",
                           excerpt=_x["excerpt"], source_url=_x["source_url"], source_note=_x["source_note"], pre_current_rules=bool(_x["pre_current_rules"])))
