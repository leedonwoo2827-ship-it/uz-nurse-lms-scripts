# -*- coding: utf-8 -*-
"""6단계 — 집필 JSON 들을 원고 HTML 하나로 조립한다(도구, 모델 없음).

    python tools/s06_assemble.py B-01-1               → data/02_강의/B-01-1/B-01-1_원고.html
    python tools/s06_assemble.py B-01-1 --final       탈고 판(09 수정본이 있으면 그것을 씀) → B-01-1_탈고.html

원고 HTML 계약(summary-showcase 가 읽는다): h3 = 슬라이드, data-say / data-read / data-img / data-id,
h2 = 코너·블록, h1 = 표지·마무리 낭독. HTML 에는 강의 내용만 — 패널 명부는 검토의견.xlsx 에.
"""
from __future__ import annotations

import html
import io
import json
import re
import sys
from pathlib import Path

from common import DATA, PACK_DIR, pack, read, slot, write

LECT = DATA / "02_강의"
ROMAN = ["Ⅰ", "Ⅱ", "Ⅲ", "Ⅳ", "Ⅴ", "Ⅵ", "Ⅶ"]
CORNER_NAMES = {"think": "생각해보기", "tutor": "강사 소개", "goals": "학습목표", "outline": "학습내용",
                "body": "본문", "wrap": "정리하기", "quiz": "퀴즈", "refs": "참고문헌"}


def attr(s: str) -> str:
    return html.escape((s or "").strip(), quote=True).replace("\n", " ")


def has_jong(word: str) -> bool:
    """마지막 한글 글자에 받침이 있는가. 조사를 고르는 데 쓴다."""
    for c in reversed((word or "").strip()):
        if "가" <= c <= "힣":
            return (ord(c) - 0xAC00) % 28 != 0
        if c.isalnum():
            return c in "013678lmnr"      # 영문·숫자로 끝나면 흔한 읽기로 어림
    return False


def cover_lines(title: str):
    """표지·마무리 낭독. **도구가 만든다** — 강마다 같은 형태여야 한다.

    ★ 제목 말고 다른 것을 읽히지 않는다. 과정·코드·차시 같은 관리용 정보를 화면에 두면
      영상 도구가 그것까지 읽어 "비 공 일 일 사십오 분 엘엠에스" 가 되어 버린다(실측).
    """
    t = title.strip()
    spoken = t.replace(" — ", ", ").replace("—", ",")     # 줄표는 소리로 읽을 수 없다. 쉼표로 쉰다
    say = "안녕하세요. %s%s 시작하겠습니다." % (t, "을" if has_jong(t) else "를")
    read = "안녕하세요. %s%s 시작하겠습니다." % (spoken, "을" if has_jong(spoken) else "를")
    outro = "지금까지 %s%s습니다. 들어주셔서 감사합니다." % (t, "이었" if has_jong(t) else "였")
    outro_read = "지금까지 %s%s습니다. 들어주셔서 감사합니다." % (spoken, "이었" if has_jong(spoken) else "였")
    return say, read, outro, outro_read


def sid(lecture_id: str, block: int, no_in_corner: int, corner: str) -> str:
    # b01-1-03-07 = B-01 1차시 3블록 7장. 본문이 아닌 코너는 블록 자리에 코너 약자.
    code, k = lecture_id.rsplit("-", 1)
    base = code.lower().replace("-", "")
    blk = ("%02d" % block) if corner == "body" else corner[:2]
    return "%s-%s-%s-%02d" % (base, k, blk, no_in_corner)


def load_written(d: Path, final=False):
    """청크 파일들을 no 순으로 합친다. --final 이면 09_수정_cNN.json 이 있는 청크는 그것을 쓴다."""
    slides, h1 = {}, {}
    for p in sorted(d.glob("05_집필_c*.json")):
        q = d / p.name.replace("05_집필_", "09_수정_")
        src = q if (final and q.is_file()) else p
        got = json.load(io.open(src, encoding="utf-8"))
        if got.get("h1"):
            h1 = got["h1"]
        for s in got.get("slides", []):
            slides[int(s["no"])] = s
    return h1, [slides[k] for k in sorted(slides)]


def clean_body(b: str) -> str:
    b = (b or "").strip()
    b = re.sub(r"<(script|style|link|iframe)[^>]*>.*?</\1>", "", b, flags=re.S | re.I)
    b = re.sub(r'\s(style|class)="[^"]*"', lambda m: m.group(0) if m.group(1) == "class" and 'class="src"' in m.group(0) else "", b)
    return b


def assemble(lecture_id: str, final=False):
    subj, sl, _ = slot(lecture_id)
    d = LECT / lecture_id
    sb = json.load(io.open(d / "04_스토리보드.json", encoding="utf-8"))
    plan = {s["no"]: s for s in sb["slides"]}
    h1, slides = load_written(d, final)
    if not slides:
        sys.exit("집필 파일이 없습니다: %s/05_집필_c*.json" % d)
    cfg = pack()

    parts, cur_h2, count_in_corner, prev_key = [], None, 0, None
    total_say = 0
    for s in slides:
        p = plan.get(int(s["no"]), {})
        corner, block = p.get("corner", "body"), int(p.get("block") or 0)
        if corner == "tutor":
            continue          # 강사 소개는 넣지 않는다(사용자 결정)
        key = (corner, block)
        if key != prev_key:
            if corner == "body":
                h2 = "%s. %s" % (ROMAN[block - 1] if 0 < block <= len(ROMAN) else block, block_title(lecture_id, block))
            else:
                h2 = CORNER_NAMES.get(corner, corner)
            parts.append('<h2 data-corner="%s"%s>%s</h2>' % (corner, (' data-block="%d"' % block) if corner == "body" else "", html.escape(h2)))
            count_in_corner, prev_key = 0, key
        count_in_corner += 1
        say, read_, img = (s.get("say") or "").strip(), (s.get("read") or "").strip(), (s.get("img") or "").strip()
        if corner in ("quiz", "refs"):
            say = read_ = ""
        if say and not read_:
            read_ = say
        total_say += len(say)
        parts.append('<h3 data-id="%s" data-say="%s" data-read="%s" data-img="%s">%s</h3>' % (
            sid(lecture_id, block, count_in_corner, corner), attr(say), attr(read_), attr(img),
            html.escape(s.get("title") or p.get("title") or "")))
        parts.append('<div class="doc">%s</div>' % clean_body(s.get("body")))

    minutes = total_say / cfg["chars_per_sec"] / 60
    # ★ h1 에 보이는 글은 **강 제목 하나뿐**이다. 차시ID·과정·코드는 넣지 않는다 — 읽혀 버린다.
    title = sb.get("title", "").strip()
    say, read_h1, outro_say, outro_read = cover_lines(title)
    total_say += len(say) + len(outro_say)
    tpl = read(PACK_DIR / "template_원고.html")
    out = (tpl.replace("{{title}}", html.escape(title))
           .replace("{{meta}}", attr("%s · %d장 · data-say %d자" % (lecture_id, len(slides), total_say)))
           .replace("{{say_total}}", "{:,}".format(total_say))
           .replace("{{minutes}}", "%d분 %02d초" % (int(minutes), int(round((minutes % 1) * 60))))
           .replace("{{h1_say}}", attr(say)).replace("{{h1_read}}", attr(read_h1))
           .replace("{{h1_outro_say}}", attr(outro_say)).replace("{{h1_outro_read}}", attr(outro_read))
           .replace("{{subtitle}}", html.escape("%s · %s %s · %s/%s강 · 45분 LMS 강의 · 한국어 마스터 원고%s" % (
               subj["과정"], subj["코드"], subj["교과목명"], sl["차수"], sl["총차수"], " (탈고)" if final else " (초고)")))
           .replace("{{body}}", "\n".join(parts)))
    dest = d / ("%s_%s.html" % (lecture_id, "탈고" if final else "원고"))
    write(dest, out)
    print("  → %s  (%d장 · %s자 · 약 %d분)" % (dest, len(slides), "{:,}".format(total_say), round(minutes)))
    return dest


def block_title(lecture_id: str, block: int) -> str:
    from s04_storyboard import lecture_design
    _, l = lecture_design(lecture_id)
    for b in l.get("blocks", []):
        if int(b.get("no") or 0) == block:
            return b.get("title", "")
    return "블록 %d" % block


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__); sys.exit(2)
    for lid in args:
        assemble(lid, final="--final" in sys.argv)
