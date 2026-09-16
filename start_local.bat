@echo off
echo ============================================================
echo   The Lenny Growth Assistant - Local Startup
echo ============================================================
echo.

cd /d "%~dp0"

REM ── Step 1: Install backend dependencies ─────────────────────
echo [1/5] Installing backend dependencies...
cd backend
python -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo ERROR: pip install failed. Check Python version and internet connection.
    pause & exit /b 1
)
cd ..
echo     Done.

REM ── Step 2: Create sample transcripts ────────────────────────
echo [2/5] Creating sample transcripts...
cd backend
python -m ingestion.fetch_transcripts --samples-only
if errorlevel 1 echo     Warning: transcript creation failed, continuing...
cd ..
echo     Done.

REM ── Step 3: Ingest transcripts into ChromaDB ─────────────────
echo [3/5] Ingesting transcripts into ChromaDB...
cd backend
python -m ingestion.ingest
if errorlevel 1 echo     Warning: ingestion had errors, continuing...
cd ..
echo     Done.

REM ── Step 4: Start backend in background ──────────────────────
echo [4/5] Starting FastAPI backend on http://localhost:8000 ...
start "Lenny Backend" cmd /k "cd /d %~dp0backend && python -m uvicorn app.main:app --reload --port 8000"
timeout /t 3 /nobreak >nul

REM ── Step 5: Install and start frontend ───────────────────────
echo [5/5] Installing frontend and starting on http://localhost:3000 ...
cd frontend
call npm install --silent
start "Lenny Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"
cd ..

echo.
echo ============================================================
echo   App running!
echo   Frontend : http://localhost:3000
echo   API docs : http://localhost:8000/docs
echo   Health   : http://localhost:8000/health
echo ============================================================
echo.
echo   Close the two terminal windows to stop the app.
echo.
pause
