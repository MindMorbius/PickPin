#!/bin/bash

# 设置语言环境
export LANG=zh_CN.UTF-8
export LANGUAGE=zh_CN:en_US:en
export LC_ALL=zh_CN.UTF-8

# 确保终端支持 UTF-8
if [ -t 1 ]; then
    stty iutf8
fi

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# 配置
BOT_DIR=$(pwd)
VENV_DIR="$BOT_DIR/venv"
PID_FILE="$BOT_DIR/bot.pid"
LOG_FILE="$BOT_DIR/logs/bot.log"

# 确保日志目录存在
mkdir -p "$BOT_DIR/logs"

check_env() {
    echo "检查环境配置..."
    
    # 检查 Python
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}未找到 Python3${NC}"
        return 1
    fi
    
    # 检查虚拟环境
    if [ ! -d "$VENV_DIR" ]; then
        echo "创建虚拟环境..."
        python3 -m venv "$VENV_DIR"
    fi
    
    # 检查 .env 文件
    if [ ! -f "$BOT_DIR/.env" ]; then
        echo -e "${RED}未找到 .env 文件${NC}"
        return 1
    fi
    
    echo -e "${GREEN}环境检查完成${NC}"
}

install_deps() {
    echo "安装依赖..."
    source "$VENV_DIR/bin/activate"
    pip install -r requirements.txt
    echo -e "${GREEN}依赖安装完成${NC}"
}

start_bot() {
    if [ -f "$PID_FILE" ]; then
        echo -e "${RED}Bot 已在运行${NC}"
        return 1
    fi
    
    echo "启动 Bot..."
    source "$VENV_DIR/bin/activate"
    nohup python3 src/bot.py > "$LOG_FILE" 2>&1 & echo $! > "$PID_FILE"
    echo -e "${GREEN}Bot 已启动${NC}"
}

stop_bot() {
    if [ ! -f "$PID_FILE" ]; then
        echo -e "${RED}Bot 未运行${NC}"
        return 1
    fi
    
    echo "停止 Bot..."
    kill $(cat "$PID_FILE")
    rm "$PID_FILE"
    echo -e "${GREEN}Bot 已停止${NC}"
}

check_status() {
    if [ ! -f "$PID_FILE" ]; then
        echo -e "${RED}Bot 未运行${NC}"
        return 1
    fi
    
    if ps -p $(cat "$PID_FILE") > /dev/null; then
        echo -e "${GREEN}Bot 正在运行${NC}"
        echo "最新日志:"
        tail -n 10 "$LOG_FILE"
    else
        echo -e "${RED}Bot 进程已死${NC}"
        rm "$PID_FILE"
    fi
}

show_menu() {
    echo "====== PickPin Bot 管理 ======"
    echo "1. 初始化 (检查环境并安装依赖)"
    echo "2. 启动 Bot"
    echo "3. 停止 Bot"
    echo "4. 查看状态"
    echo "5. 退出"
    echo "=========================="
}

while true; do
    show_menu
    read -p "请选择操作 (1-5): " choice
    
    case $choice in
        1)
            check_env && install_deps
            read -p "按回车继续..."
            ;;
        2)
            start_bot
            read -p "按回车继续..."
            ;;
        3)
            stop_bot
            read -p "按回车继续..."
            ;;
        4)
            check_status
            read -p "按回车继续..."
            ;;
        5)
            echo "再见!"
            exit 0
            ;;
        *)
            echo -e "${RED}无效选择${NC}"
            read -p "按回车继续..."
            ;;
    esac
    clear
done