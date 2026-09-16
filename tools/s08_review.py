# -*- coding: utf-8 -*-
"""8단계 — 검토진 16명이 원고를 읽고 의견을 낸다(모델 1회). 의견은 **의견으로 남긴다.**

    python tools/s08_review.py B-01-1        → data/02_강의/B-01-1/08_검토.json
                                               (엑셀은 s10_catalog.py 가 전 강을 한 파일로 모은다: data/검토의견.xlsx)
"""
from __future__ import annotations

import io
import json
import re
import sys
from pathlib import Path

from common import DATA, call, extract_json, fill, pack, panel, panel_cards, read, slot, write
from s07_check import Parser

LECT = DATA / "02_강의"


def flatten(lecture_id: str) -> tuple[str, list]:
    P = Parser()
    P.feed(read(LECT / lecture_id / ("%s_원고.html" % lecture_id)))
    L = []
    for i, s in enumerate(P.slides, 1):
        screen = re.sub(r"\s+", " ", s["text"]).strip()
        L.append("### no %d · %s · %s · %s\n화면: %s\n낭독: %s" % (
            i, s["id"], s["corner"], s["title"].strip(), screen[:700], s["say"].strip() or "(없음)"))
    return "\n\n".join(L), P.slides


def review(lecture_id: str, force=False):
    d = LECT / lecture_id
    out = d / "08_검토.json"
    if out.exists() and not force:
        print("  이미 있습니다: %s" % out)
        return json.load(io.open(out, encoding="utf-8"))
    import yaml
    pcfg = yaml.safe_load(io.open(DATA.parent / "pack" / "persona.yaml", encoding="utf-8"))
    sb = json.load(io.open(d / "04_스토리보드.json", encoding="utf-8"))
    script, slides = flatten(lecture_id)
    reviewers = [p for p in panel()["panel"] if p["role"] == "reviewer"]
    prompt = fill(
        "08_검토.md",
        n_reviewers=len(reviewers), reviewers=panel_cards("reviewer"),
        require="\n".join("- " + r for r in pcfg.get("require", [])),
        lecture_id=lecture_id, lecture_title=sb.get("title", ""), script=script,
    )
    print("  %s — 검토진 %d명, 모델 1회 (원고 %s자)" % (lecture_id, len(reviewers), "{:,}".format(len(script))))
    text = call(prompt, d / "_prompts", "08_검토")
    got = extract_json(text)
    items = got.get("items", [])
    for it in items:
        it["no"] = int(it.get("no") or 0)
        n = it["no"]
        it["id"] = slides[n - 1]["id"] if 0 < n <= len(slides) else ""
        it["corner"] = slides[n - 1]["corner"] if 0 < n <= len(slides) else ""
        it["slide_title"] = slides[n - 1]["title"].strip() if 0 < n <= len(slides) else "(강 전체)"
        it.setdefault("kind", "이상무")
        it["선택"] = "1안 적용" if it["kind"] != "이상무" and it.get("severity") in ("상", "중") and it.get("confidence") == "확신" else ("보류" if it["kind"] != "이상무" else "")
        it["반영"] = ""
    covered = {it["no"] for it in items}
    for i, s in enumerate(slides, 1):
        if i not in covered:
            items.append({"no": i, "id": s["id"], "corner": s["corner"], "slide_title": s["title"].strip(),
                          "reviewer": "(도구)", "stratum": "", "kind": "이상무", "severity": "", "confidence": "",
                          "as_is": "", "to_be": "", "reason": "검토진이 이 장을 언급하지 않음 — 이상무로 간주", "선택": "", "반영": ""})
    items.sort(key=lambda x: (x["no"], x.get("kind") == "이상무"))
    got["items"] = items
    got["lecture_id"] = lecture_id
    got["title"] = sb.get("title", "")
    got["panel"] = [{"번호": p.get("번호"), "구분": "저자진" if p["role"] == "author" else "검토진",
                     "자리": p.get("view") or p["seat"], "가명": p.get("가명"), "약력": p.get("약력")} for p in panel()["panel"]]
    write(out, json.dumps(got, ensure_ascii=False, indent=1))
    n_issue = sum(1 for it in items if it["kind"] != "이상무")
    n_apply = sum(1 for it in items if it["선택"] == "1안 적용")
    print("  → %s  (지적 %d · 1안 적용 후보 %d · 층별 점수 %s)" % (out.name, n_issue, n_apply, got.get("scores")))
    return got


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__); sys.exit(2)
    for lid in args:
        review(lid, force="--force" in sys.argv)
