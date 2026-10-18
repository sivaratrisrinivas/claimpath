# Real past decisions (Precedent nodes)

Back to the [README](../README.md).


Beyond the two synthetic cases, the graph holds **118 real, public, past decisions** shown under "show my working" after the agent runs. They are context only: the verdict is still driven by the synthetic cases and the real rules. Counts loaded (exactly what `backend/precedents.json` contains):

| Source | Loaded | Years | What each record has |
|---|---|---|---|
| Insurance Ombudsman award summaries, Council for Insurance Ombudsmen compilations on cioins.co.in (Mediclaim-Book12/13/14/16/17 PDFs) | **58** (of 111 that passed filters; ~700 entries parsed from the books) | 2009-2012 | case no., centre (when printed), year, claim type, first Rs amount, policy clause number as quoted, reason, outcome, excerpt, source URL |
| California DMHC Independent Medical Review determinations (CHHS open data CSV, 42,749 rows in total; 5,991 rows from 2024-2026 passed filters) | **60** (8+8 on imaging/emergency/urgent-type treatments, 22+22 other medical necessity; half overturned, half upheld) | 2024-2026 | reference id, year, diagnosis/treatment category, determination, Findings excerpt, source URL |

Each precedent is linked to the nearest sample Clause (keyword match) and, through it, to the Rule that limits that clause. `scripts/build_precedents.py` regenerates the JSON from the downloaded sources; selection is seeded and deterministic.

**Caveats (also shown in the app):**
- **India awards pre-date current rules.** They are 2009-2012, before the Ombudsman Rules 2017 and the IRDAI 2024 Master Circular (60-month moratorium, 36-month PED cap). The CIO no longer publishes awards publicly (parties download with an OTP), so no newer set exists. They show how disputes were argued, not how they would be decided today.
- **Not a success rate.** The sample is keyword-selected and balanced by outcome (India's non-disclosure set is only 2 claimant-favoured of 16 because the books contain few). Never read the counts as win rates.
- **Approximate links.** Clause mapping is automatic keyword matching. India text was OCR'd from PDFs and can contain errors. Complainant/patient names are removed (a test checks for honorifics + names; it is a heuristic, not a guarantee).
- **California IMRs** cover state-regulated plans only, contain no policy clause, dates or amounts, and decide medical necessity (a different question from a prior-authorization technicality). The US-01 sample's "imaging/emergency" group is matched by treatment keywords, so it is the nearest available, not an exact analogue.
- **Licences/terms.** CIO PDFs: no licence statement found; public official documents, abbreviated with attribution. DMHC data: one portal page lists Creative Commons Attribution, another "CHHS Terms of Use"; attribution is given. I did not use CourtListener, Indian Kanoon or any scraping; the two sources are direct file downloads. Check terms before any larger redistribution.
