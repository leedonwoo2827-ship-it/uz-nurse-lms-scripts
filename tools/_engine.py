# -*- coding: utf-8 -*-
"""엔진(260810-MatrAIx-검토분석엔진)을 빌려 쓰는 자리. 엔진 코드는 건드리지 않는다.

- provider.ask(prompt)   : Claude Code 구독(OAuth) 으로 `claude -p` 한 번. 엔진 tools/provider.py 그대로.
- VENV_PY                : 엔진 venv 파이썬(pyarrow·numpy 가 여기 있다 — 패널 추출에만 쓴다)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ENGINE = Path(os.environ.get("MATRAIX_ENGINE") or r"D:\00work\260810-MatrAIx-검토분석엔진")
VENV_PY = ENGINE / "venv" / "Scripts" / "python.exe"

if not (ENGINE / "tools" / "provider.py").is_file():
    raise SystemExit("엔진을 찾지 못했습니다: %s\n  set MATRAIX_ENGINE=<엔진 폴더> 로 알려 주십시오." % ENGINE)

sys.path.insert(0, str(ENGINE / "tools"))
import provider  # noqa: E402  (엔진의 것)

ask = provider.ask
strip_fence = provider.strip_fence
ProviderError = provider.ProviderError
QuotaExceeded = provider.QuotaExceeded
NotAuthenticated = provider.NotAuthenticated
