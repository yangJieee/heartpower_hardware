#!/bin/bash

### 启动Python环境
CONDA_PATH=$HOME/miniconda3  ## 这里请填写实际安装路径
source $CONDA_PATH/bin/activate ailinker

# 设置环境变量
source ../env_setup.bash

# 设置日志文件路径
LOG_FILE="app.log"

if [ ! -f "$LOG_FILE" ];then
	touch $LOG_FILE
fi

# 启动 Flask 应用程序，并将输出重定向到日志文件

## 程序含键盘输入后台启动会报错
nohup python ../app.py > $LOG_FILE &

# 检查日志文件大小是否超过100M，如果超过清空日志
nohup bash auto_clear_log.sh > /dev/null &

echo "服务后台启动"
