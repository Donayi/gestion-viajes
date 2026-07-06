@echo off
setlocal EnableExtensions

set "ROOT_DIR=%~dp0.."
pushd "%ROOT_DIR%" >nul

docker compose -f infra/compose.dev.yml --env-file infra/.env ps
echo.

powershell -NoProfile -Command "try { $r = Invoke-WebRequest -Uri 'http://localhost:8080/health' -UseBasicParsing -TimeoutSec 5; if ($r.StatusCode -eq 200) { Write-Output 'API OK'; exit 0 } else { Write-Output 'API DOWN'; exit 1 } } catch { Write-Output 'API DOWN'; exit 1 }"
set "EXIT_CODE=%ERRORLEVEL%"

popd >nul
exit /b %EXIT_CODE%
