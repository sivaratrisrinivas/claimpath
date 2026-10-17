#!/usr/bin/env python3
"""Build backend/precedents.json from REAL public sources (run once; the JSON is committed).
  India : Council for Insurance Ombudsmen award compilations  https://www.cioins.co.in/GIC/mediclaim/Mediclaim-Book{N}.pdf  (2009-2012 awards)
  US    : California DMHC Independent Medical Review determinations (CSV, CHHS open data portal)
Usage: build_precedents.py BOOKS_DIR(with b12.txt b13.txt b14.txt b16.txt b17.txt from pdftotext -layout) IMR_CSV OUT_JSON
Complainant/patient names are stripped. Selection is deterministic (seeded). Counts are whatever the filters yield; nothing is invented."""
import csv, json, random, re, sys, html

BOOKS = {"b12": ("Mediclaim-Book12.pdf", "Ahmedabad / Bhubaneswar"), "b13": ("Mediclaim-Book13.pdf", "Ahmedabad"),
         "b14": ("Mediclaim-Book14.pdf", "Bhubaneswar"), "b16": ("Mediclaim-Book16.pdf", "Bhubaneswar"), "b17": ("Mediclaim-Book17.pdf", "Ahmedabad")}
BASE = "https://www.cioins.co.in/GIC/mediclaim/"
NAME = re.compile(r"\b(?:Mr|Mrs|Ms|Miss|Smt|Shri|Sri|Dr|Late|Kum)\.?\s+(?:[A-Z][\w.]*\s?){1,4}", re.I)
CENTRE = re.compile(r"\b(AHMEDABAD|BHUBANESWAR|BHUBANESHWAR|BHOPAL|CHANDIGARH|CHENNAI|DELHI|MUMBAI|KOLKATA|LUCKNOW|PUNE|COCHIN|KOCHI|HYDERABAD|GUWAHATI|JAIPUR|NOIDA|BENGALURU)\b", re.I)

sys.path.insert(0, __import__('os').path.join(__import__('os').path.dirname(__import__('os').path.abspath(__file__)), '..', 'backend'))
from classify import india_clause, us_clause, outcome_of  # noqa: E402


def clean(s):
    s = html.unescape(s).replace("\u2011", "-")
    return re.sub(r"\s+", " ", s).strip()


def redact(s):
    s = re.sub(r"Case No\.?\s?[\d\-/]+ the complainant(?:/s)?\s*", "", s)
    s = re.sub(r"^&?\s*Submissions\s*:\s*", "", s)
    s = re.sub(r"^Case No\.? ?\S+ .{0,170}?(?=(?:The (?:Complainant|claim|Respondent|insured)|Complainant|Claim|INDIVIDUAL|[A-Z][a-z]+ Mediclaim|Both the parties))", "", s)
    s = NAME.sub("the complainant", s)
    s = re.sub(r"(the complainant[ ,]*){2,}", "the complainant ", s)
    return re.sub(r"Case No\.?\s?[\d\-/]+ the complainant(?:/s)?\s*(?:Vs?\.?\s*)?", "", s)


def sentences(t):
    return re.split(r"(?<=[.;])\s+(?=[A-Z])", t)


def parse_books(d):
    out = []
    for key, (fname, default_centre) in BOOKS.items():
        try: txt = open(f"{d}/{key}.txt", encoding="utf8", errors="ignore").read()
        except FileNotFoundError: continue
        marks = [(m.start(), m.group(1)) for m in re.finditer(r"(?:Case|Complaint)\s*No\.?\s*[-:]?\s*([\d\-/]{8,})", txt, re.I)]
        for i, (pos, cno) in enumerate(marks):
            end = marks[i + 1][0] if i + 1 < len(marks) else len(txt)
            seg = txt[pos:end]
            hdr = txt[max(0, pos - 400):pos]
            cm = CENTRE.findall(hdr)
            centre = cm[-1].title().replace("Bhubaneshwar", "Bhubaneswar") if cm else None
            ad = re.search(r"Award\s*dated?[^\n]{0,70}", seg, re.I)
            yr = re.search(r"(20[01]\d)", ad.group(0)) if ad else None
            if not yr: yr = re.search(r"(20[01]\d)", seg[:900])
            if not yr: continue
            body = re.sub(r"^.*?Award\s*dated?[^\n]*\n", "", seg, count=1, flags=re.S | re.I) if ad and ad.start() < 500 else seg
            body = clean(body)
            if len(body) < 250: continue
            if not 2009 <= int(yr.group(1)) <= 2012 or not re.match(r"\d", cno): continue
            out.append(dict(book=key, case_no=cno.strip("-"), centre=centre, year=int(yr.group(1)), body=body, file=fname))
    return out


def build_india(d, n=60):
    cands = []
    for c in parse_books(d):
        b = c["body"]; head = b[:700]
        b = re.sub(r"^Case No\.? ?[\d/A-Za-z\-]+ .*?(?:Facts\s*&\s*Submissions\s*:|Order Dated\s*:?\s*[\d\w .,]{8,25})", "", b, count=1)
        c["body"] = b = b.strip()
        if len(b) < 250: continue
        clause = india_clause(b)
        if not clause: continue
        oc = outcome_of(b)
        if not oc: continue
        amts = [int(a.replace(",", "")) for a in re.findall(r"Rs\.?\s?([\d,]{4,})", b)]
        ref = re.search(r"(?:clause|condition|exclusion|section)s?\s*(?:no\.?)?\s*([0-9]+(?:\.[0-9]+)*(?:\([a-z0-9]+\))?)", b, re.I)
        sents = [s for s in sentences(redact(b)) if re.search(r"repudiat|reject|denied|declined|ground|disallow|deduct", s, re.I)]
        reason = " ".join(sents[:2])[:360] or redact(b)[:300]
        claim_type = ("Repudiation of mediclaim" if re.search(r"repudiat|reject|declin", head, re.I) else "Partial settlement / deduction" if re.search(r"deduct|short|partial", head, re.I) else "Mediclaim dispute")
        cands.append(dict(id=f"PRC-IN-{c['book'].upper()}-{c['case_no']}", jurisdiction="IN", source_kind="Insurance Ombudsman award summary",
                          case_ref=c["case_no"], forum=(f"Insurance Ombudsman, {c['centre']} centre" if c["centre"] else "Insurance Ombudsman (centre not named in this compilation entry)"), year=c["year"], claim_type=claim_type,
                          amount=amts[0] if amts else 0, currency="INR", clause_id=clause, clause_ref=(ref.group(1) if ref else ""),
                          reason=reason, outcome=oc, excerpt=redact(b)[:420].rsplit(" ", 1)[0] + "...", _text=dict(body=redact(b)),
                          source_url=BASE + c["file"], source_note=f"Council for Insurance Ombudsmen award compilation ({c['file']}), as published on cioins.co.in",
                          pre_current_rules=True))
    seen, uniq = set(), []
    for c in cands:
        k = re.sub(r"\W", "", c["excerpt"])[:90].lower()
        if k in seen: continue
        seen.add(k); uniq.append(c)
    cands = uniq
    random.Random(7).shuffle(cands)
    # balance: per clause cap, and outcome mix
    per = {"IN-7.2": 30, "IN-4.1": 30, "IN-3.1": 14, "IN-9.1": 6}
    got, cnt = [], {}
    for c in sorted(cands, key=lambda x: (x["outcome"], x["id"])):
        pass
    for oc in ("complainant succeeded (in whole or part)", "insurer's decision upheld"):
        for c in cands:
            if c["outcome"] != oc: continue
            k = (c["clause_id"], oc)
            if cnt.get(k, 0) >= per[c["clause_id"]] // 2: continue
            cnt[k] = cnt.get(k, 0) + 1; got.append(c)
    return got[:n], len(cands)


def build_us(csvp, n=60):
    rows = list(csv.DictReader(open(csvp, encoding="utf8")))
    pool = [r for r in rows if int(r["ReportYear"]) >= 2024 and r["Findings"] and len(r["Findings"]) > 400]
    pr = random.Random(11)
    out, quota = [], {("US-9.4", "Overturned"): 8, ("US-9.4", "Upheld"): 8, ("US-3.5", "Overturned"): 22, ("US-3.5", "Upheld"): 22}
    pr.shuffle(pool)
    cnt = {}
    for r in pool:
        det = "Overturned" if r["Determination"].startswith("Overturned") else "Upheld"
        cid = us_clause(r["TreatmentCategory"], r["TreatmentSubCategory"], r["Findings"], r["Type"])
        if cid is None: continue
        k = (cid, det)
        if cnt.get(k, 0) >= quota.get(k, 0): continue
        cnt[k] = cnt.get(k, 0) + 1
        f = clean(r["Findings"]); f = re.sub(r"^Findings:\s*", "", f)
        ex = f.split("Final Result:")[0].strip()
        ex = ex[:480].rsplit(" ", 1)[0] + ("..." if len(ex) > 480 else "")
        out.append(dict(id=f"PRC-US-{r['ReferenceID']}", jurisdiction="US", source_kind="California DMHC Independent Medical Review determination",
                        case_ref=r["ReferenceID"], forum="California DMHC Independent Medical Review", year=int(r["ReportYear"]),
                        claim_type=f"{r['Type']} - {r['TreatmentCategory']} ({r['TreatmentSubCategory']})", amount=0, currency="USD",
                        clause_id=cid, clause_ref="", reason=f"Health plan denied: {r['Type'].lower()} ({r['TreatmentCategory']}); diagnosis: {r['DiagnosisCategory']}",
                        outcome=("health plan's denial overturned" if det == "Overturned" else "health plan's denial upheld"),
                        excerpt=ex, source_url="https://data.chhs.ca.gov/dataset/independent-medical-review-imr-determinations-trend",
                        source_note="California DMHC IMR determinations dataset (CHHS Open Data); searchable at https://wpso.dmhc.ca.gov/imr/",
                        _text=dict(treatment_category=r["TreatmentCategory"], treatment_sub=r["TreatmentSubCategory"], typ=r["Type"], findings=clean(r["Findings"])),
                        pre_current_rules=False, days_to_review=int(r["DaysToReview"] or 0), imr_type=r["IMRType"], determination=det))
    return out, len(pool)


if __name__ == "__main__":
    books, imr, outp = sys.argv[1:4]
    ind, pin = build_india(books); us, pus = build_us(imr)
    if len(sys.argv) > 4:  # evals/cases.jsonl: the exact (redacted) text each classifier saw, for evals/run_eval.py
        with open(sys.argv[4], "w", encoding="utf8") as fh:
            for x in ind + us:
                fh.write(json.dumps({"id": x["id"], "jurisdiction": x["jurisdiction"], **x["_text"]}, ensure_ascii=False) + "\n")
    for x in ind + us: x.pop("_text", None)
    json.dump({"india": ind, "us": us, "stats": {"india_candidates_after_filters": pin, "us_pool_2024_2026": pus}}, open(outp, "w"), indent=1, ensure_ascii=False)
    print(len(ind), "India;", len(us), "US;", pin, pus)
