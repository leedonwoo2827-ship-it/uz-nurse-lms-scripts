# -*- coding: utf-8 -*-
"""2단계 — 과목 하나를 LMS credit 수만큼 강으로 나눈다(저자진, 모델 1회).

    python tools/s02_design.py B-01            → data/01_설계/B-01_설계.json + .md
    python tools/s02_design.py --all           전 과목(이미 있는 것은 건너뜀)
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

from common import DATA, call, extract_json, fill, load_input, panel_cards, write

OUT = DATA / "01_설계"


def design(code: str, force=False):
    subjects, slots = load_input()
    if code not in subjects:
        sys.exit("교과목 시트에 없는 코드: %s" % code)
    s = subjects[code]
    my = [x for x in slots if x["코드"] == code]
    if not my:
        print("  %s — 강의 없음(최종평가). 건너뜀." % code)
        return None
    out = OUT / ("%s_설계.json" % code)
    if out.exists() and not force:
        print("  이미 있습니다: %s" % out)
        return json.load(io.open(out, encoding="utf-8"))

    sib = [v for v in subjects.values() if v["모듈코드"] == s["모듈코드"] and v["코드"] != code]
    preset = [x for x in my if x.get("제목") or x.get("학습목표")]
    prompt = fill(
        "02_설계.md",
        authors=panel_cards("author"),
        course=s["과정"], module_code=s["모듈코드"], module_name=s["모듈명"],
        code=code, subject=s["교과목명"], comp_main=s["주역량"], comp_sub=s["부역량"],
        credit=s["credit"], lms=s["LMS"], onsite=s["집합"], n_lectures=len(my),
        mode=s["운영"], method=s["교육방법"], assess=s["평가방법"], content_type=s["콘텐츠 형태"],
        objectives="\n".join("  " + l for l in str(s["학습목표"]).splitlines() if l.strip()),
        contents=s["주요 교육내용"], local_note=s["현지 적용 유의"] or "(없음)",
        benchmark=s["벤치마킹 근거"],
        siblings="\n".join("- %s %s — %s" % (v["코드"], v["교과목명"], v["주요 교육내용"]) for v in sib) or "(없음)",
        preset="\n".join("- %s: %s / %s" % (x["차시ID"], x.get("제목") or "(제목 없음)", x.get("학습목표") or "") for x in preset) or "(없음)",
        lecture_ids=", ".join(x["차시ID"] for x in my),
    )
    print("  %s %s — %d강 설계, 모델 1회" % (code, s["교과목명"], len(my)))
    text = call(prompt, OUT / "_prompts", "02_%s_설계" % code)
    d = extract_json(text)
    ids = [l["id"] for l in d.get("lectures", [])]
    want = [x["차시ID"] for x in my]
    if ids != want:
        print("  [경고] 차시ID 가 다릅니다: 받음 %s / 기대 %s — 기대 순서로 바로잡음" % (ids, want))
        for l, w in zip(d["lectures"], want):
            l["id"] = w
    d["subject"] = {k: s[k] for k in ("과정", "모듈코드", "모듈명", "코드", "교과목명", "주역량", "부역량", "학습목표", "주요 교육내용", "현지 적용 유의", "콘텐츠 형태")}
    write(out, json.dumps(d, ensure_ascii=False, indent=1))
    write(out.with_suffix(".md"), to_md(d))
    print("  →", out)
    return d


def to_md(d):
    s = d["subject"]
    L = ["# %s %s — 차시 설계 (%d강)" % (s["코드"], s["교과목명"], len(d["lectures"])), ""]
    for l in d["lectures"]:
        L += ["## %s %s" % (l["id"], l["title"]), "",
              "**학습목표**", *["%d. %s" % (i + 1, o) for i, o in enumerate(l.get("objectives", []))], "",
              "**생각해보기**", *["- " + q for q in l.get("think", [])], ""]
        for b in l.get("blocks", []):
            L += ["### 블록 %s. %s" % (b.get("no"), b.get("title")),
                  "- 소주제: " + " · ".join(b.get("topics", [])),
                  "- 표·그림: " + " / ".join(b.get("figures", []))]
            if b.get("skill"):
                L += ["- 술기: " + json.dumps(b["skill"], ensure_ascii=False)]
            L += [""]
        L += ["**퀴즈 주제**: " + " · ".join(l.get("quiz_topics", [])),
              "**현지화**: " + " ".join(l.get("localize", [])) if l.get("localize") else "**현지화**: (없음)",
              "**선행**: " + (", ".join(l.get("prereq", [])) or "없음"), ""]
    L += ["## 학습목표 배분", ""]
    for c in d.get("coverage", []):
        L += ["- %s → %s" % (c.get("objective"), ", ".join(c.get("where", [])))]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    force = "--force" in sys.argv
    if "--all" in sys.argv:
        subjects, _ = load_input()
        for code in subjects:
            design(code, force)
    elif args:
        for code in args:
            design(code, force)
    else:
        print(__doc__)
