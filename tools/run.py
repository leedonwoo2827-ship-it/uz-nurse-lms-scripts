# -*- coding: utf-8 -*-
"""큐 실행기 — 며칠 동안 돌려 둔다. 이미 있는 산출은 건너뛰고, 실패는 기록하고 다음 강으로.

    python tools/run.py design                       설계: 전 과목(없는 것만)
    python tools/run.py draft   [--batch 1] [--workers 3] [--only B-01-1,B-01-2]
                                                     초고: 스토리보드 → 집필 → 조립 → 검수 (→ 규격 밖 청크 1회 재집필)
    python tools/run.py review  [--batch 1] [--workers 2]
                                                     검토 → 수정 → 탈고 (검수표_탈고 까지)
    python tools/run.py all     [--batch 1]          draft 뒤 review
    python tools/run.py catalog                      index.html · 검토의견.xlsx · 목차.xlsx 갱신

큐 순서 = _context/차시설계_입력_v1.xlsx 의 차시슬롯 순서. --batch 로 1차(30+30)/2차 를 고른다.
워커 = 동시에 부르는 claude -p 수. 같은 구독을 다른 창이 함께 쓰면 2~3 이 안전하다.
"""
from __future__ import annotations

import io
import json
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from common import DATA, LOG, load_input

LECT = DATA / "02_강의"


def opt(name, default=None):
    if name in sys.argv:
        i = sys.argv.index(name)
        return sys.argv[i + 1] if i + 1 < len(sys.argv) else default
    return default


def queue(batch, only):
    subjects, slots = load_input()
    q = [s["차시ID"] for s in slots]
    if batch:
        q = [s["차시ID"] for s in slots if str(s["배치"]) == str(batch)]
    if only:
        want = [x.strip() for x in only.split(",") if x.strip()]
        q = [x for x in q if x in want] or want
    return q


def note(lid, stage, ok, msg=""):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    io.open(LOG, "a", encoding="utf-8").write(json.dumps(
        {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "run": stage, "lecture": lid, "ok": ok, "msg": msg[:300]}, ensure_ascii=False) + "\n")


def do_design():
    from s02_design import design
    subjects, _ = load_input()
    for code in subjects:
        try:
            design(code)
        except SystemExit as e:
            print("  [중단] %s" % e); raise
        except Exception as e:
            print("  [실패] %s — %s" % (code, e)); note(code, "design", False, str(e))


def draft_one(lid):
    from s04_storyboard import storyboard
    from s05_write import write_lecture
    from s06_assemble import assemble
    from s07_check import check
    d = LECT / lid
    if (d / ("%s_원고.html" % lid)).is_file() and (d / "07_검수.json").is_file():
        return "있음"
    code = lid.rsplit("-", 1)[0]
    if not (DATA / "01_설계" / ("%s_설계.json" % code)).is_file():
        from s02_design import design
        design(code)
    storyboard(lid)
    write_lecture(lid)
    assemble(lid)
    st = check(lid)
    if st != "통과":
        c = json.load(io.open(d / "07_검수.json", encoding="utf-8"))
        if c.get("bad_slides"):
            print("  %s — 규격 밖 장 %d개, 그 청크만 1회 재집필" % (lid, len(c["bad_slides"])))
            write_lecture(lid, fix=True)
            assemble(lid)
            st = check(lid)
    return st


def review_one(lid):
    from s08_review import review
    from s09_revise import revise
    d = LECT / lid
    if not (d / ("%s_원고.html" % lid)).is_file():
        return "초고 없음"
    if (d / ("%s_탈고.html" % lid)).is_file():
        return "있음"
    review(lid)
    revise(lid)
    return "탈고"


def run_pool(fn, q, workers, stage):
    results = {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(fn, lid): lid for lid in q}
        for f in as_completed(futs):
            lid = futs[f]
            try:
                r = f.result()
                results[lid] = r
                note(lid, stage, True, str(r))
                print("[%s] %s → %s" % (stage, lid, r))
            except SystemExit as e:
                results[lid] = "중단: %s" % e
                note(lid, stage, False, str(e))
                print("[%s] %s 중단: %s" % (stage, lid, e))
            except Exception as e:
                results[lid] = "실패: %s" % e
                note(lid, stage, False, traceback.format_exc()[-300:])
                print("[%s] %s 실패: %s" % (stage, lid, e))
    return results


def main():
    if len(sys.argv) < 2:
        print(__doc__); return 2
    cmd = sys.argv[1]
    batch, only = opt("--batch"), opt("--only")
    workers = int(opt("--workers", "2"))
    if cmd == "design":
        do_design()
    elif cmd in ("draft", "review", "all"):
        q = queue(batch, only)
        print("큐 %d강 (배치 %s) · 워커 %d" % (len(q), batch or "전체", workers))
        if cmd in ("draft", "all"):
            run_pool(draft_one, q, workers, "draft")
        if cmd in ("review", "all"):
            run_pool(review_one, q, workers, "review")
        from s10_catalog import main as catalog
        catalog()
    elif cmd == "catalog":
        from s10_catalog import main as catalog
        catalog()
    else:
        print(__doc__); return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
