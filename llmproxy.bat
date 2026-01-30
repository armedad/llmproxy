@echo off
setlocal enabledelayedexpansion

REM LLM Proxy - Windows launcher

cd /d "%~dp0"

if "%1"=="--help" goto :help
if "%1"=="-h" goto :help
if "%1"=="--install" goto :install

REM Check for port argument
set "PORT="
:parse_args
if "%1"=="--port" (
    set "PORT=%2"
    shift
    shift
    goto :parse_args
)

REM Check Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Error: python is required but not found
    echo Install Python 3.9+ from https://python.org and try again
    exit /b 1
)

REM Check dependencies
python -c "import aiohttp" 2>nul
if %errorlevel% neq 0 (
    echo Dependencies not installed. Run: llmproxy.bat --install
    exit /b 1
)

REM Set port via environment if specified
if defined PORT (
    set "LLM_PROXY_PORT=%PORT%"
)

REM Run the proxy
python run.py
goto :eof

:help
echo.
echo LLM Proxy - Local OpenAI API debugging proxy
echo.
echo USAGE:
echo     llmproxy.bat [OPTIONS]
echo.
echo OPTIONS:
echo     --help, -h      Show this help message
echo     --port PORT     Override the default port (default: 8000)
echo     --install       Install Python dependencies
echo.
echo DESCRIPTION:
echo     LLM Proxy sits between your apps and OpenAI's API, letting you observe
echo     and debug actual API calls. It logs requests/responses and provides a
echo     web UI for inspection.
echo.
echo QUICK START:
echo     1. Start the proxy:
echo        llmproxy.bat
echo.
echo     2. Open the web UI:
echo        http://localhost:8000
echo.
echo     3. Configure your app to use the proxy as the OpenAI base URL:
echo        http://localhost:8000
echo.
echo CONFIGURING APPS:
echo     Cursor:
echo         Settings -^> Models -^> OpenAI Base URL -^> http://localhost:8000
echo.
echo     OpenAI Python SDK:
echo         client = OpenAI(base_url="http://localhost:8000/v1", api_key="...")
echo.
echo     curl:
echo         curl http://localhost:8000/v1/chat/completions ^
echo           -H "Authorization: Bearer sk-..." ^
echo           -H "Content-Type: application/json" ^
echo           -d "{\"model\": \"gpt-4o\", \"messages\": [...]}"
echo.
echo CONFIGURATION:
echo     Edit config.json to change settings:
echo     - port: Local port (default 8000)
echo     - api_key_override: Use a specific API key instead of client's
echo     - log_dir: Where to store request logs
echo.
echo LOGS:
echo     Request logs are saved to: logs\requests-YYYY-MM-DD.jsonl
echo.
echo MORE INFO:
echo     See README.md for full documentation.
echo.
goto :eof

:install
echo Installing dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo Failed to install dependencies. Try:
    echo     pip install aiohttp
)
echo Done!
goto :eof
