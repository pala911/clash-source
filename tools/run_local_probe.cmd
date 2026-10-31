@echo off
REM ============================================================
REM  clash-source local (China-scope) probe -- MANUAL entry point.
REM  The scheduled task \clash-source-local-probe now runs pythonw.exe
REM  directly on src\local_probe.py (windowless, since 2026-10-17);
REM  this .cmd stays for manual/console runs -- same effect.
REM
REM  NOTE: this file is ASCII-only ON PURPOSE. cmd.exe reads .cmd using the
REM  OEM codepage (936/GBK on Chinese Windows). A UTF-8 .cmd with Chinese
REM  comments gets its line structure mangled and dies with
REM  "xxx is not recognized as an internal or external command".
REM  All the real documentation lives in src/local_probe.py (UTF-8, safe).
REM
REM  Manual runs (args are passed through to local_probe.py):
REM    tools\run_local_probe.cmd --scope-only   skip probing, only archive+push
REM    tools\run_local_probe.cmd --no-push      probe only, do not push
REM
REM  This entry point NEVER touches dist/ -- it only pushes state/, archive/,
REM  reports/ and src/sources.yaml. Node freshness is L1's job (every 6h).
REM  (An earlier comment here claimed "weekly"; the scheduled task is daily.)
REM ============================================================
setlocal
set ROOT=D:\work\agent\codebuddy\clash-source
set PY=D:\softdata\anaconda3\python.exe
set LOG=%ROOT%\logs

if not exist "%LOG%" mkdir "%LOG%"
set LOGF=%LOG%\local_probe.log

echo ============================================================>> "%LOGF%"
echo [%DATE% %TIME%] start local probe (scope=local) %*>> "%LOGF%"

cd /d "%ROOT%"
"%PY%" "%ROOT%\src\local_probe.py" %* >> "%LOGF%" 2>&1
set RC=%ERRORLEVEL%

echo [%DATE% %TIME%] done, exit=%RC%>> "%LOGF%"
exit /b %RC%