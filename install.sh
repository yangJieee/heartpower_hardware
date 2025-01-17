#!/bin/bash

# 创建ailinker虚拟环境
conda create -n ailinker python=3.8

# 切换到目标虚拟环境
conda activate ailinker

# 安装环境依赖
python -m pip install -r requirements.txt -i https://mirrors.cloud.tencent.com/pypi/simple

# 创建临时数据输出目录
if [ -d "./temp/asr" ]; then
    echo "Directory './tmep/asr' already exists."
else
    # 创建目录
    mkdir "./temp/asr" -p
    mkdir "./deploy/temp/asr" -p
    echo "Directory "./temp/asr" created successfully."
fi

# 创建api key信息环境变量存储文件
cp docs/example_env_setup.bash env_setup.bash
