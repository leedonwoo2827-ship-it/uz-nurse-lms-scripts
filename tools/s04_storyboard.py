# -*- coding: utf-8 -*-
"""4단계 — 강 하나의 슬라이드 계획(스토리보드) JSON. 저자진, 모델 1회.

    python tools/s04_storyboard.py B-01-1     → data/02_강의/B-01-1/04_스토리보드.json
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

from common import DATA, call, extract_json, fill, pack, panel_cards, slot, write

LECT = DATA / "02_강의"


def lecture_design(lecture_id: str):
    code = lecture_id.rsplit("-", 1)[0]
    p = DATA / "01_설계" / ("%s_설계.json" % code)
    if not p.is_file():
        sys.exit("설계가 없습니다: %s  → python tools/s02_design.py %s" % (p, code))
    d = json.load(io.open(p, encoding="utf-8"))
    for l in d["lectures"]:
        if l["id"] == lecture_id:
            return d, l
    sys.exit("설계에 이 차시가 없습니다: %s" % lecture_id)


def budget(cfg: dict, n_blocks: int):
    """코너별 장 수·낭독 예산. 본문은 블록 수로 나눈다."""
    rows, total_slides, total_say = [], 0, 0
    for c in cfg["corners"]:
        if c["id"] == "body":
            body_slides = int(round((c["slides"][0] + c["slides"][1]) / 2))
            body_say = int(round((c["say"][0] + c["say"][1]) / 2))
            per = [body_slides // n_blocks] * n_blocks
            for i in range(body_slides - sum(per)):
                per[i] += 1
            for b in range(n_blocks):
                s = int(round(body_say * per[b] / body_slides))
                rows.append(("body", b + 1, per[b], s))
                total_slides += per[b]; total_say += s
        else:
            n = c["slides"][1] if c["id"] in ("quiz",) else c["slides"][0] if c["id"] in ("tutor", "goals", "outline", "refs") else int(round((c["slides"][0] + c["slides"][1]) / 2))
            s = int(round((c["say"][0] + c["say"][1]) / 2))
            rows.append((c["id"], 0, n, s))
            total_slides += n; total_say += s
    names = {c["id"]: c["name"] for c in cfg["corners"]}
    lines = ["| 코너 | 블록 | 장 수 | 낭독 합계(자) |", "|---|---|---|---|"]
    for cid, b, n, s in rows:
        lines.append("| %s | %s | %d | %d |" % (names[cid], b or "-", n, s))
    return rows, "\n".join(lines), total_slides, total_say


def storyboard(lecture_id: str, force=False):
    subj, sl, siblings = slot(lecture_id)
    d, l = lecture_design(lecture_id)
    out = LECT / lecture_id / "04_스토리보드.json"
    if out.exists() and not force:
        print("  이미 있습니다: %s" % out)
        return json.load(io.open(out, encoding="utf-8"))
    cfg = pack()
    blocks = l.get("blocks", [])
    rows, table, ts, tsay = budget(cfg, max(1, len(blocks)))
    blocks_txt = "\n".join(
        "  블록 %s. %s\n    소주제: %s\n    표·그림 후보: %s%s" % (
            b.get("no"), b.get("title"), " · ".join(b.get("topics", [])), " / ".join(b.get("figures", [])),
            ("\n    술기: " + json.dumps(b["skill"], ensure_ascii=False)) if b.get("skill") else "")
        for b in blocks)
    prompt = fill(
        "04_스토리보드.md",
        authors=panel_cards("author"),
        lecture_id=lecture_id, lecture_title=l["title"],
        code=subj["코드"], subject=subj["교과목명"], course=subj["과정"],
        module_code=subj["모듈코드"], module_name=subj["모듈명"],
        k=sl["차수"], n=sl["총차수"],
        objectives="\n".join("  %d. %s" % (i + 1, o) for i, o in enumerate(l.get("objectives", []))),
        think=" / ".join(l.get("think", [])), blocks=blocks_txt,
        quiz_topics=" · ".join(l.get("quiz_topics", [])),
        localize=" ".join(l.get("localize", [])) or "(없음)",
        budget=table, total_slides=ts, total_say=tsay, total_min=round(tsay / cfg["chars_per_sec"] / 60),
    )
    print("  %s %s — 스토리보드, 모델 1회 (예산 %d장 · %d자)" % (lecture_id, l["title"], ts, tsay))
    text = call(prompt, LECT / lecture_id / "_prompts", "04_스토리보드")
    sb = extract_json(text)
    sb["id"] = lecture_id
    sb["title"] = sb.get("title") or l["title"]
    sb["budget"] = [{"corner": c, "block": b, "slides": n, "say": s} for c, b, n, s in rows]
    for i, s in enumerate(sb["slides"], 1):
        s["no"] = i
    write(out, json.dumps(sb, ensure_ascii=False, indent=1))
    got = len(sb["slides"]); gsay = sum(int(s.get("target") or 0) for s in sb["slides"])
    print("  → %s  (%d장 · 목표 %d자)" % (out, got, gsay))
    return sb


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__); sys.exit(2)
    for lid in args:
        storyboard(lid, force="--force" in sys.argv)
