# ClaimPath accuracy check: results

Ground truth: `labels.csv`, hand-labelled blind from the case text using `RUBRIC.md` (no LLM, no mapper output seen). Split: `split.json` (stratified, seed 42): dev 72 cases, held-out 46 (39%). Raw numbers: `results.json`. Reproduce: `python evals/run_eval.py --split dev --verdicts`.

## (a) Clause / rule mapping (118 real precedents)
| Set | n | Clause accuracy (95% Wilson CI) | Rule-set accuracy | India | US |
|---|---|---|---|---|---|
| Dev, **before** fixes | 72 | 88.9% (79.6-94.3) | 90.3% | 80.6% (29/36) | 97.2% (35/36) |
| Dev, after fixes (**tuned on dev, optimistic**) | 72 | 94.4% (86.6-97.8) | 94.4% | 88.9% (32/36) | 100% (36/36) |
| **Held-out, after fixes (run once)** | 46 | **95.7% (85.5-98.8)** | 95.7% | 90.9% (20/22) | 100% (24/24) |

No held-out number exists for the pre-fix mapper (measuring it would have used up the held-out set).

Held-out per-class (precision / recall, support): IN-7.2 1.00/0.86 (7), IN-4.1 0.83/1.00 (10), IN-3.1 1.00/1.00 (3), IN-9.1 1.00/1.00 (1), US-9.4 1.00/1.00 (6), US-3.5 1.00/1.00 (18). Held-out errors (2): one IN-7.2 case mapped to IN-4.1 (policy ground and non-disclosure both present); one case with no matching clause (label NONE) forced into IN-4.1.

Top error types (found on dev, before fixes; 8 clause errors):
1. Fixed clause priority ignored what the case is mainly about: room-rent vs waiting-period cases mapped to IN-4.1 whenever "waiting period" appeared anywhere in the first 650 chars (3 cases). Fix: earliest mention wins among 4.1/3.1/9.1.
2. Generic words as evidence: "room charges" in a policy schedule, "MRI" mentioned as a comparison test in a US case (2 cases). Fix: stricter 3.1 pattern; US text window cut to the requested service.
3. Compilation entries that run into the next case (1 case, still wrong: the cut pattern does not catch that entry's separator).
4. Mixed-ground cases (non-disclosure stated after the first 650 chars; two clauses cited): not fixable by keywords (2 cases).
5. Structural, by design: the mapper never answers "none"; IN-3.1, IN-9.1 and US-11.3 have no rule edges, so those cases link to a clause but to no rule.

## (b) Outcome tag, India awards (CLAIMANT = positive)
| Set | n scored | Accuracy (CI) | TPR (claimant won) | TNR (insurer won) |
|---|---|---|---|---|
| Dev, before | 36 | 75.0% (58.9-86.2) | 63.2% (12/19) | 88.2% (15/17) |
| Dev, after (tuned on dev) | 36 | 100% (90.4-100) | 100% | 100% |
| **Held-out, after (once)** | 20 (+2 labelled UNCLEAR) | **95.0% (76.4-99.1)** | 88.9% (8/9) | 100% (11/11) |

Before the fix, 9 of 36 dev tags were wrong, 7 of them real wins tagged "insurer upheld" because "not justified" matched "justified", and "complaint succeeds" was not a recognised phrase. The 100% dev figure is just the fitted rule set and should not be quoted. Held-out misses: 1 claimant win with no recognised closing phrase (tag abstains), and 2 UNCLEAR cases (outcome not stated in the entry) that the tagger still labelled "complainant succeeded". Applying the fixed rules changed 12 of the 58 stored India outcome tags in `precedents.json`; 2 India precedents lost their clause link (no clause fits) and 2 US ones moved from US-9.4 to US-3.5.

## (c) Verdict logic
17/17 checks pass (the two synthetic cases, what-if facts, and variants whose answer follows from the rule text; V15-V17 feed ambiguous pasted text through the clause matcher). These cases were designed by the same author as the logic, so they confirm the rules behave as written and do not independently validate the rules.
