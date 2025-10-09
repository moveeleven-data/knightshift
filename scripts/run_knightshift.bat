:: Windows-only launcher script.
:: Runs the KnightShift pipeline Docker container.

@echo off
setlocal

:: Define paths
set PROJECT_DIR=C:\Users\KV-62\Desktop\knightshift
set ENV_FILE=%PROJECT_DIR%\.env.docker
set LOG_FILE=%PROJECT_DIR%\log.txt

echo ===============================================
echo   Launching KnightShift Pipeline...
echo   Environment: %ENV_FILE%
echo   Logs: %LOG_FILE%
echo ===============================================

:: Run the container
docker run --rm --env-file "%ENV_FILE%" knightshift-pipeline >> "%LOG_FILE%" 2>&1

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] KnightShift Pipeline failed. Check %LOG_FILE% for details.
) else (
    echo.
    echo [SUCCESS] KnightShift Pipeline finished successfully.
)

echo.
pause
endlocal