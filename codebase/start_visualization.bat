@echo off
chcp 65001 >nul
setlocal

if not exist "visualization\run.py" (
    echo ERROR: Please run this script from the codebase directory.
    echo Expected file: visualization\run.py
    pause
    exit /b 1
)

python -c "import gradio, fastapi, uvicorn" >nul 2>nul
if errorlevel 1 (
    echo Installing visualization dependencies...
    pip install -r visualization\requirements_viz.txt
    if errorlevel 1 (
        echo ERROR: dependency installation failed.
        pause
        exit /b 1
    )
)

echo Starting RAG visualization...
cd /d "%~dp0visualization"
python run.py

endlocal
