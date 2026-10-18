# Honest limitations (full)

Back to the [README](../README.md).


- **Two synthetic sample cases.** The insurers, people, policies and bills are invented. The rules are real; the facts are not.
- **A small rules graph (10 rules).** "Likely valid" means *no rule in this graph defeats the clause*, not that the insurer is right. It is a triage aid, not a prediction of outcome; the real past decisions are an illustrative, non-representative sample, so there is still no win-rate data.
- **Verification varies per rule** and each rule node states it. The IRDAI 60-month moratorium and rejection-letter rules were read from the IRDAI Master Circular text (29 May 2024); the 36-month PED cap is confirmed only through secondary reporting; US rules were read on eCFR. Paragraph numbering follows the circular's own table. Applicability to older policies was not checked.
- **India Ombudsman deadline is conservative:** Rule 14(3) counts one year from the insurer's reply to your representation; ClaimPath shows one year from the claim rejection (the Council of Insurance Ombudsmen's guidance) so you are never late.
- **US:** plan type matters (self-funded ERISA vs fully insured, state vs federal external review). ClaimPath encodes the federal floor only. The "emergency" question is ultimately a fact decision by the plan or reviewer.
- **Pasted text** is matched to a clause by keyword overlap, not by a language model.
- No OCR / document upload, no tracking of real claims, no state insurance-department rules, no Indian consumer-court limitation (not encoded).
- Competitors exist (ClaimRights, ClaimBhai, Counterforce Health, Fight Health Insurance, and others). The wedge here is the auditable path with a source at every hop plus bill-vs-policy reconciliation; we did not benchmark against them.
- Figure status (updated): the 31,490 Ombudsman complaints (and ~95% rejection share) were checked in the primary CIO annual report, and KFF <1% / 56% at KFF's own pages; only the FY2022-23 count (25,873) and the +21.7% growth remain secondary-only. See [problem-evidence.md](problem-evidence.md).
