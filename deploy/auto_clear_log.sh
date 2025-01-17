#!bin/bash

# 设置日志文件路径

LOG_FILE="app.log"

MAXSIZE=100000000  # 100M，单位为字节
#MAXSIZE=10000  # 10k

while true; do
    size=$(stat -c %s "$LOG_FILE")  # 获取文件大小，单位为字节
    if [ $size -gt $MAXSIZE ]; then
        echo "Clear $LOG_FILE, as it exceeded 100M."
	cat /dev/null > $LOG_FILE
    fi
    sleep 600  # 每隔600秒检查一次文件大小
done

