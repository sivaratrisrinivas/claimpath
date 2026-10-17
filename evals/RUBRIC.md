# Labelling rubric (written BEFORE labelling; labels made blind to the mapper's output)

Unit: one real past decision (58 India Ombudsman awards 2009-2012, 60 California DMHC IMRs 2024-2026).
Labeller: one reader (an AI assistant, reading each text; no mapper output shown). Single labeller, NOT independent of the person who wrote the mapper - see README caveats.

## A. Clause label = which sample-policy clause is the insurer's stated ground for denying/short-paying?
India (read the insurer's ground, not just words that appear somewhere):
- IN-7.2  non-disclosure / misrepresentation / concealment / fraud / false statement as the ground (including a repudiation that pairs non-disclosure with pre-existing disease).
- IN-4.1  pre-existing disease, or a time-bound exclusion/waiting period (30-day, 1-year, 2-year, 4-year exclusion clauses) as the ground.
- IN-3.1  room rent / room category / proportionate deduction as the ground (the sample's rent-limit and proportionate-deduction clauses).
- IN-9.1  cosmetic / aesthetic / plastic-surgery type exclusion as the ground.
- NONE    none of the above fits (e.g. hospitalisation not necessary, OPD/domiciliary, delayed intimation, missing documents, non-payable items, sum-insured/cap, TPA process, cancellation, other exclusion).
US (California IMR; every case is a plan denial reviewed for medical necessity or experimental/investigational status):
- US-9.4  the case itself concerns advanced imaging (CT, MRI, PET) or emergency/urgent/ambulance services, i.e. the kind of service the sample's authorization clause is about.
- US-3.5  medical necessity / experimental-investigational denial for any other service.
- US-11.3 the service is cosmetic / appearance-driven.
- NONE    cannot tell.
Rule label is derived: the rules a clause is LIMITED_BY in the graph (IN-7.2 -> R-IN-MORATORIUM + R-IN-CITE; IN-4.1 -> R-IN-PED36 + R-IN-CITE; US-9.4 -> R-US-EMERG + R-US-NOTICE; US-3.5 -> R-US-NOTICE; IN-3.1, IN-9.1, US-11.3, NONE -> no rule). A predicted rule set is correct iff it equals the rule set of the true clause.

## B. Outcome label (India only; US outcome is the dataset's Determination field)
- CLAIMANT  the Ombudsman allowed/partly allowed, directed payment/reconsideration in favour of the complainant.
- INSURER   the Ombudsman upheld the insurer's decision / dismissed.
- UNCLEAR   closed without a merits ruling, or genuinely mixed.
Positive class for TPR/TNR = CLAIMANT.
