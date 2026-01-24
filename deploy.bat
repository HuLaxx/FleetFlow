@echo off
REM ===========================================
REM FleetFlow - Production Deployment Script (Windows)
REM ===========================================

echo.
echo 🚀 FleetFlow Production Deployment
echo ====================================
echo.

REM Check Docker
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker not found. Please install Docker Desktop.
    pause
    exit /b 1
)
echo ✅ Docker found

REM Check environment files
if not exist "backend\.env" (
    echo ⚠️  backend\.env not found
    echo    Copying from .env.example...
    copy backend\.env.example backend\.env
    echo    ⚠️  IMPORTANT: Edit backend\.env with production values!
)

if not exist "frontend\.env.local" (
    echo ⚠️  frontend\.env.local not found
    echo    Copying from .env.example...
    copy frontend\.env.example frontend\.env.local
    echo    ⚠️  IMPORTANT: Edit frontend\.env.local with production values!
)

echo ✅ Environment files ready
echo.

REM Build and start
echo 🔨 Building and starting services...
docker-compose up -d --build

echo.
echo ✅ Waiting for services to start...
timeout /t 10 /nobreak >nul

echo.
echo ====================================
echo 🎉 FleetFlow Deployment Complete!
echo ====================================
echo.
echo Access Points:
echo   📱 Frontend:    http://localhost:3000
echo   🔌 API:         http://localhost:8000
echo   📊 API Docs:    http://localhost:8000/docs
echo   📈 Metrics:     http://localhost:8000/metrics
echo   🔍 GraphQL:     http://localhost:8000/graphql
echo   🌐 WebSocket:   ws://localhost:8002
echo.
echo Monitoring:
echo   📊 Prometheus:  http://localhost:9090
echo   📈 Grafana:     http://localhost:3001 (admin/admin)
echo.
echo Commands:
echo   View logs:      docker-compose logs -f
echo   Stop:           docker-compose down
echo   Restart:        docker-compose restart
echo.

pause
