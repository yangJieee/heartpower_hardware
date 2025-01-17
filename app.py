# coding=utf-8
# AILINKER 主管理程序
## 主要功能如下
# 1. 运行web服务器
# 2. 接收硬件请求，管理后端各节点(启动，重启等)
# 3. 提供设备操作界面
import os
import subprocess
import json
from time import sleep
from flask import Flask, jsonify, render_template

#1.日志系统初始化,配置log等级
from utility import mlogging
mlogging.logger_config('app', mlogging.INFO, False)

#2.导入logger模块
from utility.mlogging import logger


# 获取工作目录和配置文件目录
WORK_PATH=os.environ.get("AILINKER_WORK_PATH", None)
if WORK_PATH is None:
    logger.error("get work path fail!")
    exit(1)
CONFIG_PATH= WORK_PATH + "/configs/config"

# 服务器端口
PORT=8090

STATUS_NONE = -1
STATUS_STOP = 0
STATUS_RUNNING = 1


app = Flask(__name__)


class NodeManager:
    """节点进程管理
    """
    def __init__(self, work_path: str, config_path: str):
        """节点进程管理
        Args:
            work_path      节点程序所在目录
            config_path    节点程序配置文件所在目录
        """
        self.status = STATUS_STOP

        self.work_path = work_path
        self.config_path = config_path

        # 切换置指定虚拟环境，source环境变量
        # init_process = subprocess.Popen(["source", ""])

        self.bridge_node_process = None
        self.asr_node_process = None
        self.tts_node_process = None
        self.chat_node_process = None


    def start(self):
        """启动各节点
        """
        logger.info("start nodes.")

        if self.status == STATUS_RUNNING:
            logger.warn("nodes, already start.")
            return

        bridge_node_app = self.work_path + '/' + 'node_bridge.py' 
        bridge_node_config = self.config_path + '/' + 'config_bridge.json' 
        self.bridge_node_process = subprocess.Popen(['python', bridge_node_app, bridge_node_config])

        asr_node_app = self.work_path + '/' + 'node_asr.py' 
        asr_node_config = self.config_path + '/' + 'config_asr.json' 
        self.asr_node_process = subprocess.Popen(['python', asr_node_app, asr_node_config])

        chat_node_app = self.work_path + '/' + 'node_chat.py' 
        chat_node_config = self.config_path + '/' + 'config_chat.json' 
        self.chat_node_process = subprocess.Popen(['python', chat_node_app, chat_node_config])

        tts_node_app = self.work_path + '/' + 'node_tts.py' 
        tts_node_config = self.config_path + '/' + 'config_tts.json' 
        self.tts_node_process = subprocess.Popen(['python', tts_node_app, tts_node_config])

        self.status = STATUS_RUNNING


    def stop(self):
        """关闭各节点
        """
        logger.info("close nodes.")
        if self.status == STATUS_STOP:
            logger.warn("nodes, already stop.")
            return

        self.bridge_node_process.terminate()
        # self.bridge_node_process.kill()
        # 等待进程结束
        self.bridge_node_process.wait()

        self.asr_node_process.terminate()
        self.asr_node_process.wait()

        self.chat_node_process.terminate()
        self.chat_node_process.wait()

        self.tts_node_process.terminate()
        self.tts_node_process.wait()

        self.status = STATUS_STOP


    def restart(self):
        """重启各节点
        """
        logger.info("restart nodes.")
        if self.status == STATUS_RUNNING:
            self.stop()
        self.start()



manager = NodeManager(work_path=WORK_PATH, config_path=CONFIG_PATH)


@app.route('/nodes_start', methods=['GET'])
def start_node():
    manager.start()
    return jsonify({'status': STATUS_RUNNING}), 200


@app.route('/nodes_stop', methods=['GET'])
def stop_node():
    manager.stop()
    return jsonify({'status': STATUS_STOP}), 200


@app.route('/nodes_restart', methods=['GET'])
def restart_node():
    manager.restart()
    return jsonify({'status': STATUS_RUNNING}), 200

@app.route('/')
def index():
    return render_template('index.html')


def close_nodes():
    """关闭各nodes
    """
    manager.stop()


if __name__ == '__main__':
    logger.info("main app start...")
    app.run(debug=False, host='0.0.0.0', port=PORT)
    # flask app退出后关闭各nodes
    close_nodes()
