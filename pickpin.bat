@echo off
chcp 65001 > nul
setlocal EnableDelayedExpansion

set "BOT_DIR=%~dp0"
set "VENV_DIR=%BOT_DIR%venv"
set "PID_FILE=%BOT_DIR%bot.pid"
set "LOG_FILE=%BOT_DIR%logs\bot.log"

if not exist "%BOT_DIR%logs" mkdir "%BOT_DIR%logs"

:check_env
echo 检查环境配置...
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo %RED%Python未安装%NC%
    exit /b 1
)

if not exist "%VENV_DIR%" (
    echo 创建虚拟环境...
    python -m venv "%VENV_DIR%"
)

if not exist "%BOT_DIR%.env" (
    echo .env文件不存在
    exit /b 1
)
goto :eof

:install_deps
echo 安装依赖...
call "%VENV_DIR%\Scripts\activate.bat"
pip install -r requirements.txt
echo 依赖安装完成
goto :eof

:start_bot
if exist "%PID_FILE%" (
    echo Bot已在运行
    exit /b 1
)

echo 启动Bot...
call "%VENV_DIR%\Scripts\activate.bat"
start /B pythonw src\bot.py > "%LOG_FILE%" 2>&1
for /f "tokens=2" %%a in ('tasklist ^| findstr "pythonw.exe"') do (
    echo %%a > "%PID_FILE%"
    goto :bot_started
)
:bot_started
echo %GREEN%Bot已启动%NC%
goto :eof

:stop_bot
if not exist "%PID_FILE%" (
    echo Bot未运行
    exit /b 1
)

echo 停止Bot...
for /f %%a in (%PID_FILE%) do (
    taskkill /PID %%a /F
)
del "%PID_FILE%"
echo Bot已停止
goto :eof

:check_status
if not exist "%PID_FILE%" (
    echo Bot未运行
    exit /b 1
)

for /f %%a in (%PID_FILE%) do (
    tasklist /FI "PID eq %%a" 2>nul | find "%%a" >nul
    if !ERRORLEVEL! equ 0 (
        echo Bot正在运行
        echo 最新日志:
        type "%LOG_FILE%" | tail -n 10
    ) else (
        echo Bot进程已死
        del "%PID_FILE%"
    )
)
goto :eof

:show_menu
echo ====== PickPin Bot 管理 ======
echo 1. 初始化 (检查环境并安装依赖^)
echo 2. 启动 Bot
echo 3. 停止 Bot
echo 4. 查看状态
echo 5. 退出
echo ==========================

:menu_loop
call :show_menu
set /p choice="请选择操作 (1-5): "

if "%choice%"=="1" (
    call :check_env
    call :install_deps
) else if "%choice%"=="2" (
    call :start_bot
) else if "%choice%"=="3" (
    call :stop_bot
) else if "%choice%"=="4" (
    call :check_status
) else if "%choice%"=="5" (
    echo 再见!
    exit /b 0
) else (
    echo 无效选择
)

pause
cls
goto menu_loop