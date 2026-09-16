# -*- coding: utf-8 -*-
"""5단계 — 스토리보드를 청크로 나눠 화면·낭독·발음·이미지 대본을 쓴다(저자진, 청크마다 모델 1회).

    python tools/s05_write.py B-01-1                → data/02_강의/B-01-1/05_집필_c01.json …
    python tools/s05_write.py B-01-1 --only 3,5     그 청크만 다시(파일을 지우고)
    python tools/s05_write.py B-01-1 --fix          검수표가 잡은 장이 든 청크만 다시

청크 = 도입 코너(생각해보기~학습내용, h1 포함) / 본문 블록(12장 넘으면 반으로) / 마무리(정리·퀴즈·참고문헌).
"""
from __future__ import annotations

import io
import json
import re
import sys
from pathlib import Path

from common import DATA, call, extract_json, fill, pack, panel_cards, slot, write

LECT = DATA / "02_강의"
CHUNK_MAX = 12
CORNER_NAMES = {"think": "생각해보기", "tutor": "강사 소개", "goals": "학습목표", "outline": "학습내용",
                "body": "본문", "wrap": "정리하기", "quiz": "퀴즈", "refs": "참고문헌"}


def chunks(slides):
    """[(label, [slides])]"""
    intro = [s for s in slides if s["corner"] in ("think", "goals", "outline")]   # 강사 소개(tutor)는 쓰지 않는다
    outro = [s for s in slides if s["corner"] in ("wrap", "quiz", "refs")]
    out = [("도입 코너 (생각해보기 → 학습목표 → 학습내용)", intro)]
    blocks = {}
    for s in slides:
        if s["corner"] == "body":
            blocks.setdefault(int(s.get("block") or 0), []).append(s)
    for b in sorted(blocks):
        ss = blocks[b]
        if len(ss) <= CHUNK_MAX:
            out.append(("본문 블록 %d" % b, ss))
        else:
            half = (len(ss) + 1) // 2
            out.append(("본문 블록 %d (앞부분)" % b, ss[:half]))
            out.append(("본문 블록 %d (뒷부분)" % b, ss[half:]))
    out.append(("마무리 코너 (정리하기 → 퀴즈 → 참고문헌)", outro))
    return [(l, ss) for l, ss in out if ss]


def slide_lines(ss):
    L = []
    for s in ss:
        sc = s.get("screen") or {}
        L.append("- no %d · [%s%s] %s\n    화면: %s — %s\n    낭독 목표(%s자): %s" % (
            s["no"], CORNER_NAMES.get(s["corner"], s["corner"]),
            (" 블록%s" % s["block"]) if s["corner"] == "body" else "",
            s.get("title", ""), sc.get("kind", ""), sc.get("sketch", ""),
            s.get("target", 0), s.get("say_goal", "")))
    return "\n".join(L)


def write_lecture(lecture_id: str, only=None, fix=False):
    subj, sl, _ = slot(lecture_id)
    d = LECT / lecture_id
    sb = json.load(io.open(d / "04_스토리보드.json", encoding="utf-8"))
    from s04_storyboard import lecture_design
    _, design = lecture_design(lecture_id)
    cs = chunks(sb["slides"])
    outline = " → ".join("%d.%s" % (s["no"], s.get("title", "")) for s in sb["slides"])

    redo = set(only or [])
    if fix:
        chk = d / "07_검수.json"
        if chk.is_file():
            bad = set(json.load(io.open(chk, encoding="utf-8")).get("bad_slides", []))
            for i, (_, ss) in enumerate(cs, 1):
                if any(s["no"] in bad for s in ss):
                    redo.add(i)
            print("  다시 쓸 청크: %s" % (sorted(redo) or "없음"))

    prev_say = "(첫 장입니다)"
    for i, (label, ss) in enumerate(cs, 1):
        out = d / ("05_집필_c%02d.json" % i)
        if out.exists() and i not in redo:
            got = json.load(io.open(out, encoding="utf-8"))
            prev_say = (got["slides"][-1].get("say") or prev_say) if got.get("slides") else prev_say
            continue
        h1_hint = ('{"h1": {"say": "표지에서 읽을 한두 문장(강 제목·오늘 할 일)", "read": "그 발음판", '
                   '"outro_say": "마무리 화면에서 읽을 한두 문장", "outro_read": "그 발음판"},\n ') if i == 1 else "{"
        prompt = fill(
            "05_집필.md",
            authors=panel_cards("author"),
            lecture_id=lecture_id, lecture_title=sb.get("title", ""),
            code=subj["코드"], subject=subj["교과목명"], k=sl["차수"], n=sl["총차수"],
            objectives="\n".join("  %d. %s" % (j + 1, o) for j, o in enumerate(design.get("objectives", []))),
            outline=outline, chunk_label=label, chunk_n=len(ss), chunk_slides=slide_lines(ss),
            prev_say=prev_say, h1_hint=h1_hint,
        )
        print("  %s — 청크 %d/%d %s (%d장), 모델 1회" % (lecture_id, i, len(cs), label, len(ss)))
        text = call(prompt, d / "_prompts", "05_집필_c%02d" % i)
        try:
            got = extract_json(text)
        except Exception as e:
            print("  [JSON 실패] 청크 %d — %s. 한 번 더 부릅니다." % (i, str(e)[:80]))
            text = call(prompt, d / "_prompts", "05_집필_c%02d_r" % i)
            got = extract_json(text)
        if isinstance(got, list):
            got = {"slides": got}
        # no 정렬·누락 확인
        want = [s["no"] for s in ss]
        have = {int(x.get("no")): x for x in got.get("slides", []) if x.get("no") is not None}
        missing = [n for n in want if n not in have]
        if missing:
            print("  [경고] 빠진 장: %s — 스토리보드 제목으로 빈 장을 채워 둡니다(검수표가 잡습니다)" % missing)
            for n in missing:
                st = next(s for s in ss if s["no"] == n)
                have[n] = {"no": n, "title": st.get("title", ""), "body": "<p>(집필 누락)</p>", "say": "", "read": "", "img": ""}
        got["slides"] = [have[n] for n in want]
        got["chunk"] = {"index": i, "label": label, "nos": want}
        write(out, json.dumps(got, ensure_ascii=False, indent=1))
        prev_say = got["slides"][-1].get("say") or prev_say
        print("  → %s (%d자)" % (out.name, sum(len(x.get("say") or "") for x in got["slides"])))
    return len(cs)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    only = None
    if "--only" in sys.argv:
        only = [int(x) for x in sys.argv[sys.argv.index("--only") + 1].split(",")]
        args = [a for a in args if a != sys.argv[sys.argv.index("--only") + 1]]
    if not args:
        print(__doc__); sys.exit(2)
    for lid in args:
        write_lecture(lid, only=only, fix="--fix" in sys.argv)
