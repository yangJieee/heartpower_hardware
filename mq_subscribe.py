"""MQ获取打印node(queue)信息
"""
# coding=utf-8
import sys
import json
from time import sleep

# 日志系统初始化,配置log等级
from utility import mlogging
mlogging.logger_config('mqsub', mlogging.INFO, False)
from utility.mlogging import logger

from utility.keyboard import KBHit
from common.mq_transport import MqTransport


class MqSubscribe():
    """rabbitmq 订阅node(queue)消息并输出到终端
    Args:

    """
    def __init__(self, config: dict, sub_node: str):
        """
        Args:
            config      rabbitmq配置信息
        """
        self.config = config
        self.node_name = self.config['node_name']

        self.listening_node = []
        self.listening_node.append(sub_node)

        # 创建mq传输实例
        self.tr = MqTransport(self.config)
        # mq传输使能接收
        self.tr.enable_receive(routing_keys=self.listening_node)

        # 键盘控制
        self.keyboard = KBHit()
        self.node_exit = False


    def launch(self):
        """接收消息并输出
        """
        logger.info('subscribe {} :'.format(self.listening_node))
        while not self.node_exit:
            sleep(0.01)
            self.keyboard_control()
            ##接收消息
            msg = self.tr.receive()
            if msg is not None:
                print(msg)

        self.tr.close()


    def close(self):
        self.node_exit = True


    def keyboard_control(self):
        """control task.
        """
        if self.keyboard.kbhit():
            key_value = ord(self.keyboard.getch())
            if key_value == ord('q') or key_value == 27: # 27: ESC
                logger.info('keyboard exit.')
                self.close()


def main(config: dict, sub_node: str):
    """Args:
        config  APP配置文件
        sub_node:  订阅的节点
    """
    sub = MqSubscribe(config['rabbitmq'], sub_node)
    sub.launch()


if __name__=='__main__':
    """入口函数
    """
    logger.info('mq sub start...')

    #读取配置文件
    if len(sys.argv) < 3:
        logger.error('useage: config_file sub_node')
        exit(0)

    config_file = sys.argv[1]
    sub_node = sys.argv[2]
    logger.info('config: %s', config_file)
    logger.info('sub_node: %s', sub_node)

    with open(config_file, 'r', encoding='utf-8') as load_f:
        config = json.load(load_f)
        logger.info(config)
        main(config, sub_node)

