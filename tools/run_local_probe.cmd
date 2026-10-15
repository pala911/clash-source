@echo off
REM ============================================================
REM  clash-source local (China-scope) probe -- weekly entry point
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
REM  Why weekly and not daily: the China-scope probe only serves
REM  "recall a recovered source" + "quality ranking". Source quality drifts on a
REM  week/month scale. The actual daily need (node freshness) is handled by the
REM  CI fetch pipeline and has nothing to do with probing.
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