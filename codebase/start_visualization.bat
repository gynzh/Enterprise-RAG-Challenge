@echo off
REM 关闭命令回显

chcp 65001 >nul
REM 设置终端编码为 UTF-8

echo 🚀 启动 RAG Challenge 复现结果可视化系统
echo ===============================================

REM 检查是否在正确目录
if not exist "visualization\" (
    echo ❌ 错误：请在项目根目录运行此脚本
    echo    应该包含 visualization/ 目录
    pause
    exit /b 1
)

REM 进入可视化目录
cd visualization

REM 检查是否已安装依赖
echo 📦 检查依赖...
python -c "import gradio; print('✅ Gradio 已安装')" 2>nul

if errorlevel 1 (
    echo ⚠️ 正在安装依赖...
    pip install -r requirements_viz.txt

    if errorlevel 1 (
        echo ❌ 依赖安装失败
        pause
        exit /b 1
    )
)

echo.
echo 🎉 环境测试通过！正在启动可视化界面...
echo 📱 界面地址: http://localhost:7860
echo 💡 按 Ctrl+C 停止服务器
echo.

REM 启动应用
python run.py

pause