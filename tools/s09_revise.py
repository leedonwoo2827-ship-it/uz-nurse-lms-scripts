# -*- coding: utf-8 -*-
"""9단계 — 검토 의견(1안 적용 대상)이 있는 청크만 저자진이 고쳐 **탈고 HTML 을 반드시 완결**한다.

    python tools/s09_revise.py B-01-1     → 09_수정_cNN.json (고친 청크만) → B-01-1_탈고.html + 검수표_탈고.md

★ 지적이 없거나 모델이 실패해도 탈고 파일은 만든다(원고 그대로). 결론이 파일로 남는 것이 규약이다.
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

from common import DATA, call, extract_json, fill, panel_cards, slot, write
from s05_write import chunks
from s06_assemble import assemble
from s07_check import check

LECT = DATA / "02_강의"


def revise(lecture_id: str, force=False):
    d = LECT / lecture_id
    rv_path = d / "08_검토.json"
    if not rv_path.is_file():
        sys.exit("검토가 없습니다: %s" % rv_path)
    rv = json.load(io.open(rv_path, encoding="utf-8"))
    sb = json.load(io.open(d / "04_스토리보드.json", encoding="utf-8"))
    from s04_storyboard import lecture_design
    _, design = lecture_design(lecture_id)
    cs = chunks(sb["slides"])
    todo = [it for it in rv["items"] if it.get("선택") == "1안 적용" and it.get("no")]
    by_no = {}
    for it in todo:
        by_no.setdefault(it["no"], []).append(it)

    changed = 0
    for i, (label, ss) in enumerate(cs, 1):
        nos = [s["no"] for s in ss]
        items = [it for n in nos for it in by_no.get(n, [])]
        out = d / ("09_수정_c%02d.json" % i)
        if not items:
            continue
        if out.exists() and not force:
            print("  청크 %d 이미 고침" % i)
            continue
        src = json.load(io.open(d / ("05_집필_c%02d.json" % i), encoding="utf-8"))
        prompt = fill(
            "09_수정.md",
            authors=panel_cards("author"),
            lecture_id=lecture_id, lecture_title=sb.get("title", ""),
            objectives="\n".join("  %d. %s" % (j + 1, o) for j, o in enumerate(design.get("objectives", []))),
            chunk_label=label, chunk_n=len(ss),
            chunk_json=json.dumps({"slides": src["slides"]}, ensure_ascii=False, indent=1),
            items="\n".join("- no %d [%s·%s·%s] %s\n    AS IS: %s\n    TO BE: %s\n    근거: %s" % (
                it["no"], it.get("kind"), it.get("severity"), it.get("reviewer"), it.get("slide_title", ""),
                it.get("as_is", ""), it.get("to_be", ""), it.get("reason", "")) for it in items),
        )
        print("  %s — 청크 %d %s 수정 (%d건), 모델 1회" % (lecture_id, i, label, len(items)))
        try:
            got = extract_json(call(prompt, d / "_prompts", "09_수정_c%02d" % i))
        except Exception as e:
            print("  [실패] 청크 %d 수정을 못 받았습니다(%s) — 원고 그대로 탈고합니다" % (i, str(e)[:80]))
            for it in items:
                it["반영"] = "실패 — 원고 유지"
            continue
        have = {int(x["no"]): x for x in got.get("slides", []) if x.get("no") is not None}
        merged = {"slides": [have.get(s["no"], s) for s in src["slides"]], "decisions": got.get("decisions", []),
                  "chunk": src.get("chunk")}
        if src.get("h1"):
            merged["h1"] = src["h1"]
        write(out, json.dumps(merged, ensure_ascii=False, indent=1))
        dec = {(int(x.get("no") or 0), x.get("reviewer", "")): x for x in got.get("decisions", [])}
        for it in items:
            x = dec.get((it["no"], it.get("reviewer", "")))
            if x is None:
                it["반영"] = "탈고에 반영(1안)" if it["no"] in have else "미반영"
            else:
                it["반영"] = ("탈고에 반영(1안)" if x.get("applied") else "저자진 미반영") + ((" — " + x["note"]) if x.get("note") else "")
        changed += 1

    write(rv_path, json.dumps(rv, ensure_ascii=False, indent=1))
    dest = assemble(lecture_id, final=True)
    check(lecture_id, final=True)
    print("  탈고 완결: %s (고친 청크 %d개)" % (dest.name, changed))
    return dest


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__); sys.exit(2)
    for lid in args:
        revise(lid, force="--force" in sys.argv)
