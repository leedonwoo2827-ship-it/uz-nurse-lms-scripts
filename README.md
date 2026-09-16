# 우즈베키스탄 간호사 LMS 강의 — 122강 대본 파이프라인

우즈베키스탄 보건부 산하 TXKMRM(의료인 직무역량개발센터) 규격의 1~3년차 일반간호사 보수교육
「기본 간호 실무」(67강) · 「응급상황에서의 간호」(55강) — **1 credit = 45분 동영상 1강 = 122강**의
한국어 마스터 원고를 만든다. 실제 영상은 우즈벡어 음성 · 러시아어 자막이며, 한국어판은 분량·구조 확인용이다.

MatrAIx Persona-1M 에서 뽑은 **저자진 4명 + 검토진 16명(20명)** 이 쓰고 읽는다. 검토는 의견으로 남기고
(`data/검토의견.xlsx`, 강별 시트), 결론은 강마다 `탈고.html` 로 완결한다.

## 산출물 (강마다)

```
data/02_강의/B-01-1/
  B-01-1_원고.html      ← summary-showcase 가 그대로 읽는 원고. h3 = 슬라이드
  B-01-1_검수표.md       규격 검수(장수·글자수·분·표/그림·발음·이미지 대본)
  B-01-1_탈고.html      검토 1안 반영본 (지적이 없으면 원고와 같음)
  B-01-1_검수표_탈고.md
  04_스토리보드.json · 05_집필_cNN.json · 08_검토.json · 09_수정_cNN.json · _prompts/(보낸 프롬프트·응답 전부)
```

원고 HTML 의 `h3` 속성 세 가지가 **숨겨진 대본**이다:

| 속성 | 무엇 |
|---|---|
| `data-say` | 자막 대본 (맞춤법대로, srt 원본) |
| `data-read` | 음성 대본 (TTS/성우용, 소리 나는 대로 — "에스바", "밀리미터 수은주") |
| `data-img` | 이미지 대본 (장면 지시, 16:9 · 플랫 벡터 · 라벨 4~6개). 몇 장을 그림으로 바꿀지는 나중에 고른다 |

`h1` 에는 표지·마무리 낭독(`data-say`/`data-outro-say` + `-read`). HTML 에는 강의 내용만 들어간다 — 패널 20명은 `검토의견.xlsx` 각 시트 끝에.

## 규격 (`pack/pack.yaml`)

- 낭독 합계 15,500~17,000자 (5.5자/초 → 본문만 45분 + 도입·정리) · 슬라이드 65~80장 · 본문 장당 150~300자
- 코너: 생각해보기 → 학습목표 → 학습내용 → 본문 Ⅰ~Ⅴ(블록 = 학습목표 1개, 2,500~4,000자) → 정리하기 → 퀴즈 3~5문항(낭독 없음) → 참고문헌
- 장마다 표 또는 인라인 SVG 하나 이상. 한 문장 60자 이내. 괄호 없음. 한국 기관·법령은 낭독에 넣지 않고 `[LOCALIZE: 종류 — 내용]` 으로 화면에만.

## 돌리는 법

```
run.bat                      메뉴
python tools/s00_extract.py  원본 xlsx → _context/차시설계_입력_v1.xlsx (사용자가 손보는 입력)
python tools/s01_panel.py    패널 20명 (엔진 sample_panel) → 명부 xlsx · --bio 약력
python tools/run.py design   전 과목 차시 설계 (64회 호출)
python tools/run.py draft  --batch 1 --workers 2     초고 (강당 ~10회 호출, 약 40~60분)
python tools/run.py review --batch 1 --workers 2     검토 → 수정 → 탈고
python tools/run.py catalog                          data/index.html · 검토의견.xlsx · 목차.xlsx
```

모델 호출은 `D:\00work\260810-MatrAIx-검토분석엔진\tools\provider.py` (Claude Code 구독, `claude -p`) 를 그대로 쓴다.
API 키를 쓰지 않는다. 이미 있는 산출은 덮지 않는다 — 다시 만들려면 파일을 옮기거나 지운다.

## 다음 단계 (영상)

원고 HTML → `summary-showcase`(https://github.com/leedonwoo2827-ship-it/summary-showcase) → 덱·자막·TTS·큐시트 → 영상.
영상은 1차 30+30 → 나머지 순으로 야간 CPU 작업. `_45min-assets/` 가 45분 영상 본보기다(깃허브에는 올리지 않음).
