@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "ROOT_DIR=%~dp0.."
pushd "%ROOT_DIR%" >nul

where docker >nul 2>&1
if errorlevel 1 (
  echo Docker no esta disponible en PATH.
  popd >nul
  exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
  echo Docker Desktop no esta disponible o no ha iniciado.
  popd >nul
  exit /b 1
)

if not exist "infra\.env" (
  if not exist "infra\.env.example" (
    echo No existe infra\.env ni infra\.env.example
    popd >nul
    exit /b 1
  )
  copy /Y "infra\.env.example" "infra\.env" >nul
  echo Se creo infra\.env a partir de infra\.env.example
)

if not exist "frontend\.env.local" (
  (
    echo NEXT_PUBLIC_API_URL=http://localhost:8080
    echo NEXT_PUBLIC_WEB_PUSH_PUBLIC_KEY=
  )> "frontend\.env.local"
  echo Se creo frontend\.env.local con valores locales por defecto
)

docker compose -f infra/compose.dev.yml --env-file infra/.env up --build -d
if errorlevel 1 (
  echo No fue posible iniciar Docker Compose.
  popd >nul
  exit /b 1
)

set /a elapsed=0
:wait_health
powershell -NoProfile -Command "try { $r = Invoke-WebRequest -Uri 'http://localhost:8080/health' -UseBasicParsing -TimeoutSec 5; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 goto ready

if !elapsed! GEQ 60 (
  echo Timeout esperando http://localhost:8080/health
  popd >nul
  exit /b 1
)

timeout /t 2 /nobreak >nul
set /a elapsed+=2
goto wait_health

:ready
echo ==================================
echo DAFREQ Desarrollo iniciado
echo ==================================
echo.
echo Backend:
echo http://localhost:8080
echo.
echo Swagger:
echo http://localhost:8080/docs
echo.
echo Frontend:
echo cd frontend
echo npm run dev

popd >nul
exit /b 0
