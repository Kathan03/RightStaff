@echo off
REM ==========================================
REM RightStaff Database Management Tools
REM ==========================================

if "%1"=="" goto help
if "%1"=="load-dummy" goto load_dummy
if "%1"=="reset" goto reset
if "%1"=="connect" goto connect
if "%1"=="verify" goto verify
goto help

:help
echo.
echo ========================================
echo RightStaff Database Tools
echo ========================================
echo.
echo Usage: database-tools.bat [command]
echo.
echo Available Commands:
echo   load-dummy    - Add 10 dummy candidates to existing database
echo   reset         - Reset database and reload all data
echo   connect       - Connect to PostgreSQL database
echo   verify        - Verify data was loaded successfully
echo.
goto end

:load_dummy
echo.
echo ========================================
echo Loading Dummy Data...
echo ========================================
echo.
docker exec -i rightstaff-postgres psql -U right_staff -d rightstaff < database\scripts\05_dummy_data.sql
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ Success! Dummy data loaded.
    echo    - 10 Candidates
    echo    - 5 Jobs
    echo    - 7 Applications
    echo.
    echo Run: database-tools.bat verify
) else (
    echo.
    echo ❌ Error loading data. Is the database running?
    echo Try: cd docker ^&^& docker-compose up -d postgres
    echo.
)
goto end

:reset
echo.
echo ========================================
echo WARNING: Reset Database
echo ========================================
echo.
echo This will DELETE all existing data!
echo.
set /p confirm="Are you sure? (yes/no): "
if /i not "%confirm%"=="yes" (
    echo.
    echo Cancelled.
    goto end
)
echo.
echo Stopping database...
cd docker
docker-compose down -v
echo.
echo Starting fresh database...
docker-compose up -d postgres
echo.
echo Waiting for initialization (20 seconds)...
timeout /t 20 /nobreak >nul
echo.
echo ✅ Database reset complete!
echo    All SQL scripts were automatically loaded.
echo.
cd ..
goto end

:connect
echo.
echo ========================================
echo Connecting to Database...
echo ========================================
echo.
echo 💡 Once connected, run:
echo    SET search_path = rightstaff, public;
echo    SELECT COUNT(*) FROM candidate;
echo.
echo Type \q to exit
echo.
pause
docker exec -it rightstaff-postgres psql -U right_staff -d rightstaff
goto end

:verify
echo.
echo ========================================
echo Verifying Database Contents...
echo ========================================
echo.
docker exec -it rightstaff-postgres psql -U right_staff -d rightstaff -c "SET search_path = rightstaff, public; SELECT (SELECT COUNT(*) FROM candidate) as candidates, (SELECT COUNT(*) FROM job) as jobs, (SELECT COUNT(*) FROM application) as applications, (SELECT COUNT(*) FROM skill) as skills;"
goto end

:end
echo.

