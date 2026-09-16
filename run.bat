@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
:menu
echo.
echo  45분 LMS 강의 대본 파이프라인
echo  ---------------------------------------------------------
echo  [0] xlsx 분리      _context\차시설계_입력_v1.xlsx (있으면 건너뜀)
echo  [1] 패널 20명      data\00_패널\패널명부.xlsx (+ --bio 약력)
echo  [2] 설계           전 과목 차시 분할 (없는 것만)
echo  [3] 초고 1차 배치   30+30 (스토리보드→집필→조립→검수)
echo  [4] 초고 2차 배치   나머지 62강
echo  [5] 검토·탈고 1차   30+30
echo  [6] 검토·탈고 2차   나머지
echo  [7] 현황           data\index.html · 검토의견.xlsx · 목차.xlsx
echo  [8] 한 강만        차시ID 를 물어 초고까지
echo  [q] 끝
echo.
set /p c=번호:
if "%c%"=="0" python tools\s00_extract.py & goto menu
if "%c%"=="1" python tools\s01_panel.py & python tools\s01_panel.py --bio & goto menu
if "%c%"=="2" python tools\run.py design & goto menu
if "%c%"=="3" python tools\run.py draft --batch 1 --workers 2 & goto menu
if "%c%"=="4" python tools\run.py draft --batch 2 --workers 2 & goto menu
if "%c%"=="5" python tools\run.py review --batch 1 --workers 2 & goto menu
if "%c%"=="6" python tools\run.py review --batch 2 --workers 2 & goto menu
if "%c%"=="7" python tools\run.py catalog & goto menu
if "%c%"=="8" set /p L=차시ID(예 B-01-1): & python tools\run.py draft --only %L% --workers 1 & goto menu
if "%c%"=="q" exit /b
goto menu
