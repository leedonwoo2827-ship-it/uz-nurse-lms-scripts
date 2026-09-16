# -*- coding: utf-8 -*-
"""7단계 — 원고 HTML 규격 검수(도구, 모델 없음). 대본을 고칠 때마다 다시 돌린다.

    python tools/s07_check.py B-01-1            → B-01-1_검수표.md + 07_검수.json (bad_slides 를 s05 --fix 가 읽는다)
    python tools/s07_check.py B-01-1 --final    탈고 HTML 검수 → B-01-1_검수표_탈고.md
"""
from __future__ import annotations

import io
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

from common import DATA, pack, read, write

LECT = DATA / "02_강의"


class Parser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.slides, self.h1, self.cur, self.depth_doc = [], {}, None, 0
        self.in_h3 = False
        self.in_corner_span = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "span" and a.get("class") == "corner":
            self.in_corner_span = True
        if tag == "h1":
            self.h1 = a
        elif tag == "h2":
            self.cur_corner = a.get("data-corner", "")
        elif tag == "h3":
            self.cur = {"id": a.get("data-id", ""), "say": a.get("data-say", ""), "read": a.get("data-read", ""),
                        "img": a.get("data-img", ""), "corner": getattr(self, "cur_corner", ""),
                        "title": "", "table": 0, "svg": 0, "src": 0, "text": "", "localize": 0}
            self.in_h3 = True
            self.slides.append(self.cur)
        elif self.cur is not None:
            if tag == "table": self.cur["table"] += 1
            if tag == "svg": self.cur["svg"] += 1
            if tag == "p" and a.get("class") == "src": self.cur["src"] += 1

    def handle_endtag(self, tag):
        if tag == "h3":
            self.in_h3 = False
        if tag == "span":
            self.in_corner_span = False

    def handle_data(self, data):
        if self.cur is None:
            return
        if self.in_h3:
            if not self.in_corner_span:
                self.cur["title"] += data
        else:
            self.cur["text"] += data
            self.cur["localize"] += data.count("[LOCALIZE")


def check(lecture_id: str, final=False):
    d = LECT / lecture_id
    src = d / ("%s_%s.html" % (lecture_id, "탈고" if final else "원고"))
    if not src.is_file():
        sys.exit("원고가 없습니다: %s" % src)
    cfg = pack()
    P = Parser()
    P.feed(read(src))
    S = P.slides
    forbid = cfg["voice"]["forbid"]
    smax = cfg["sentence_max"]
    per_lo, per_hi = cfg["say_per_slide"]
    bad, notes = set(), []
    total = 0
    rows = ["| # | id | 코너 | 제목 | 낭독자 | 표/그림 | 판정 |", "|---|---|---|---|---|---|---|"]
    for i, s in enumerate(S, 1):
        n = len(s["say"].strip())
        total += n
        why = []
        spoken = s["corner"] not in ("quiz", "refs")
        if spoken:
            lo_, hi_ = (per_lo, per_hi) if s["corner"] == "body" else (80, 500)   # 도입·정리 코너는 느슨하게
            if n < lo_ or n > hi_: why.append("낭독 %d자(%d~%d)" % (n, lo_, hi_))
            if not s["read"].strip(): why.append("read 없음")
            long_s = [x for x in re.split(r"(?<=[.!?。])\s+", s["say"]) if len(x.strip()) > smax]
            if long_s: why.append("%d자 넘는 문장 %d개" % (smax, len(long_s)))
            hit = [w for w in forbid if w in s["say"]]
            if hit: why.append("금칙어 " + "/".join(hit))
            if "(" in s["say"] or ")" in s["say"]: why.append("낭독에 괄호")
            if "[LOCALIZE" in s["say"]: why.append("낭독에 LOCALIZE")
        else:
            if n: why.append("낭독 있음(없어야 함)")
        if not s["img"].strip(): why.append("img 없음")
        if s["table"] + s["svg"] == 0: why.append("표/그림 없음")
        if "(집필 누락)" in s["text"]: why.append("집필 누락")
        if why:
            bad.add(i)
        rows.append("| %d | %s | %s | %s | %d | %d/%d | %s |" % (
            i, s["id"], s["corner"], s["title"].strip()[:24], n, s["table"], s["svg"], "; ".join(why) or "OK"))

    corners = [s["corner"] for s in S]
    order = [c for i, c in enumerate(corners) if i == 0 or corners[i - 1] != c]
    want = [c["id"] for c in cfg["corners"]]
    order_ok = [c for c in order if c != "body"] == [c for c in want if c != "body"] and "body" in order
    quiz_n = sum(1 for s in S if s["corner"] == "quiz")
    nslides = sum(1 for s in S)
    minutes = total / cfg["chars_per_sec"] / 60
    lo, hi = cfg["say_total"]
    slo, shi = cfg["slides"]
    verdict = []
    if not (lo <= total <= hi): verdict.append("낭독 합계 %s자 — 규격 %s~%s" % ("{:,}".format(total), "{:,}".format(lo), "{:,}".format(hi)))
    if not (slo <= nslides <= shi): verdict.append("슬라이드 %d장 — 규격 %d~%d" % (nslides, slo, shi))
    if not order_ok: verdict.append("코너 순서 %s" % " → ".join(order))
    if not (cfg["quiz"][0] <= quiz_n <= cfg["quiz"][1]): verdict.append("퀴즈 %d문항" % quiz_n)
    for k in ("data-say", "data-read", "data-outro-say", "data-outro-read"):
        if not (P.h1.get(k) or "").strip(): verdict.append("h1 %s 없음" % k)
    # 본문 블록별 합계
    blocks = {}
    for s in S:
        m = re.match(r"^[a-z0-9]+-\d+-(\d\d)-", s["id"])
        if s["corner"] == "body" and m:
            blocks[int(m.group(1))] = blocks.get(int(m.group(1)), 0) + len(s["say"].strip())
    blo, bhi = cfg["body_block_chars"]
    for b, n in sorted(blocks.items()):
        if not (blo <= n <= bhi):
            verdict.append("본문 블록 %d 낭독 %s자 — 규격 %s~%s" % (b, "{:,}".format(n), "{:,}".format(blo), "{:,}".format(bhi)))
    status = "통과" if not verdict and not bad else ("보류 — 장 %d개 규격 밖" % len(bad) if not verdict else "보류")

    md = ["# %s 검수표%s" % (lecture_id, " (탈고)" if final else ""), "",
          "- 판정: **%s**" % status,
          "- 슬라이드 %d장 · 낭독 합계 **%s자** · 약 **%d분 %02d초** (5.5자/초)" % (
              nslides, "{:,}".format(total), int(minutes), int(round((minutes % 1) * 60))),
          "- 코너 순서: %s" % " → ".join(order),
          "- 퀴즈 %d문항 · 표/그림 없는 장 %d · read 없는 장 %d · img 없는 장 %d · LOCALIZE 표시 %d곳" % (
              quiz_n, sum(1 for s in S if s["table"] + s["svg"] == 0),
              sum(1 for s in S if s["corner"] not in ("quiz", "refs") and not s["read"].strip()),
              sum(1 for s in S if not s["img"].strip()), sum(s["localize"] for s in S)),
          "- 본문 블록별 낭독: " + " · ".join("블록%d %s자" % (b, "{:,}".format(n)) for b, n in sorted(blocks.items())),
          ""]
    if verdict:
        md += ["## 강 전체 규격 밖", *["- " + v for v in verdict], ""]
    md += ["## 장별", *rows, ""]
    dest = d / ("%s_검수표%s.md" % (lecture_id, "_탈고" if final else ""))
    write(dest, "\n".join(md))
    if not final:
        write(d / "07_검수.json", json.dumps({"status": status, "total_say": total, "slides": nslides,
                                               "minutes": round(minutes, 1), "bad_slides": sorted(bad),
                                               "verdict": verdict}, ensure_ascii=False, indent=1))
    print("  %s: %s · %d장 · %s자 · %d분 → %s" % (lecture_id, status, nslides, "{:,}".format(total), round(minutes), dest.name))
    return status


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__); sys.exit(2)
    for lid in args:
        check(lid, final="--final" in sys.argv)
