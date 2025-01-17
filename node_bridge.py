# coding=utf-8
# ws<-->rabbitmq 通信桥接节点
# 主要功能如下
# 1. ws连接linker-dev
# 2. ws接收linker-dev数据转发至rabbitmq
# 3. 接收rabbitmq数据通过ws发送至linker-dev
import time
import sys
import json
from time import sleep
from collections import deque
import threading

#1.日志系统初始化,配置log等级
from utility import mlogging
mlogging.logger_config('bridge', mlogging.INFO, False)
#2.导入logger模块
from utility.mlogging import logger

from utility.keyboard import KBHit

from common.u_deque import Udeque
from common.ws_server import WsServer 

from mq_base_node import MqBaseNode, mq_close



class Bridge(MqBaseNode):
    """ws-rabitmq桥接,数据转发
    TODO: 当前收发消息缓存区共用, 只支持单设备连接, 后续改进根据设备ID区分, 加入多设备支持。
    """

    def __init__(self, config: dict):
        """ws-rabitmq桥接,数据转发
        Args:
            config: app参数
        """
        #---------------rabbitmq------------------
        super().__init__(config['rabbitmq']) 

        ## 设置rabbitmq node接收发送缓冲队列最大长度
        self.que_max_len = 5000
        self.set_que_max_len(self.que_max_len)

        self.ws_config = config['ws']

        self.node_exit = False
        # self.keyboard = KBHit()

        #---------------websocket------------------
        # 队列缓冲区最大长度
        self.ws_que_max_len = self.que_max_len

        # 创建websocket server线程
        self._ws = WsServer(self.ws_config['url'], self.ws_config['port'], self.que_max_len)
        # self.stop_event = threading.Event()
        self._ws_thread = threading.Thread(target=self._ws.run, args=())
        # 发送握手消息
        # await self._async_send_obj({'node': 'bridge', 'topic': 'status/connected', 'data': {} })
        # 硬件单次接收的最大消息长度
        self.dev_receive_length_max = config["dev"]["receive_length_max"]


    def _msg_to_obj(self, msg):
        """转换json消息为dict_obj
        Args:
            msg:  json字符串
        Returns:
            None or data_obj 
        """
        if msg is None:
            return None
        # logger.info("Receive:", msg)
        try:
            data_obj = json.loads(msg)
            # 检查解析后的数据类型，如果是数字则拒绝
            if isinstance(data_obj, (int, float)):
                raise ValueError("Input data should not be a single number.")
            # 将data_obj写入队列
            logger.debug("write to ws receive queue: {}".format(data_obj))
            return data_obj

        except json.JSONDecodeError as e:
            logger.error("Error decoding JSON: {}".format(e))
            return None

        except Exception as e:
            logger.error("An error occurred: {}".format(e))
            return None


    def launch(self):
        """bridge main run
        """
        ## 启动ws线程
        self._ws_thread.start()

        ## 启动rabitmq transport线程
        self.transport_start()

        while not self.node_exit:
            sleep(0.005) # 控制发送频率
            # self.keyboard_control()
            ## 读取ws数据(设备)发送至rabitmq
            ws_msg = self._ws.auto_read()
            ws_msg = self._msg_to_obj(ws_msg)
            if ws_msg is not None:
                logger.debug("got ws msg from: {} topic: {}".format(ws_msg['node'], ws_msg['topic']))
                self.auto_send(ws_msg)

            ## 读取rabitmq数据发送至ws(设备)
            mq_msg = self.auto_read()
            if mq_msg is not None:
                sleep(0.015) # 控制发送频率
                logger.debug("got mq msg from: {} topic: {}".format(mq_msg['node'], mq_msg['topic']))
                ## 检查消息长度是否超出限制范围
                mq_msg_str = json.dumps(mq_msg)
                mq_msg_str_length = len(mq_msg_str)
                # print(mq_msg_str)
                logger.debug("send to dev, msg length: {}".format(mq_msg_str_length))
                if mq_msg_str_length > self.dev_receive_length_max:
                    # logger.info("exception msg : {}.".format(mq_msg_str))
                    logger.error("msg length must be less than: {}.".format(self.dev_receive_length_max))
                else:
                    self._ws.auto_send(mq_msg_str)

    ''''
    def keyboard_control(self):
       """control task.
       """
       if self.keyboard.kbhit():
           key_value = ord(self.keyboard.getch())
           if key_value == ord('q'): 
               logger.info('keyboard exit.')
               self.close()
    '''

    @mq_close
    def close(self):
        """关闭节点
        """
        self._ws.close()
        self._ws_thread.join()
        self.node_exit = True
        logger.info('app exit')


#---------------------main--------------------------
def main(config: dict):
    """入口函数
    """
    bridge = Bridge(config)
    bridge.launch()


if __name__=='__main__':
    """APP入口
    """
    logger.info('node bridge start...')

    #读取配置文件
    if len(sys.argv) < 2:
        logger.error('useage: config_file')
        exit(0)

    config_file = sys.argv[1]
    logger.info('config: %s', config_file)

    with open(config_file, 'r', encoding='utf-8') as load_f:
        config = json.load(load_f)
        logger.info(config)
        main(config)

