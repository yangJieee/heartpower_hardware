# coding=utf-8
# MQ基础节点类
from time import sleep
from collections import deque
import threading

from utility.mlogging import logger
# from utility.keyboard import KBHit

from common.u_deque import Udeque
from common.mq_transport import MqTransport


def mq_close(func):
    """关闭rabbitmq连接
    """
    def wrapper(self, *args, **kwargs):
        if not getattr(self, '_mq_close_called', False):
            setattr(self, '_mq_close_called', True)
            MqBaseNode.transport_close(self)
        return func(self, *args, **kwargs)
    return wrapper


class MqBaseNode:
    """MQ节点基类
    """
    def __init__(self, config: dict):
        """
        Args:
            config:  rabbitmq参数配置
        """
        self.mq_config = config
        self.node_exit = False

        self.node_name = self.mq_config['node_name']
        # self.listening_node = ['*']  # 监听节点
        self.listening_node = self.mq_config['listening_node']
        
        # 保存待发送信息
        self._send_que = deque()

        # 保存接收信息
        self._receive_que = deque()

        # 接收缓冲队列最大长度
        self.receive_que_max_len = 10
        # 发送缓冲队列最大长度
        self.send_que_max_len = 10

        # 线程退出控制信号
        self._transport_stop_event = threading.Event()
        # 创建子线程进行与其它节点进行数据交互
        self._transport_thread = threading.Thread(target=self.transport, 
            args=(self._transport_stop_event, self._send_que, self._receive_que))

        # rabbitmq发布订阅实例
        self.mqtr = None


    def set_que_max_len(self, max_len: int):
        """设置队列缓冲区最大值
        """
        self.send_que_max_len = max_len
        self.receive_que_max_len = max_len


    def mqtr_close(self):
        """关闭连接
        """
        if self.mqtr is not None:
            self.mqtr.close()
        logger.info('rabbitmq node exit')


    def transport_close(self):
        """退出数据传输线程,关闭连接
        """
        self._transport_stop_event.set()
        self._transport_thread.join()


    def transport_start(self):
        """启动数据传输线程
        """
        self._transport_thread.start()


    def transport(self, stop_event, send_que, receive_que):
        """节点数据交互(线程函数)
        """
        # 创建mq传输实例
        self.mqtr = MqTransport(self.mq_config)
        self.mqtr.enable_receive(routing_keys=self.listening_node)
        logger.info('transport thread start, node: [{}] listenging: {}'.format(self.node_name, self.listening_node))

        while not stop_event.is_set():
            logger.debug('transport thread...')
            sleep(0.001)
            ##自动发送消息
            while True:
                sleep(0.001)
                msg_obj = Udeque.read_deque(send_que)
                if msg_obj is not None:
                    self.mqtr.send_obj(self.node_name, msg_obj)
                else:
                    break
            ##自动接收消息
            ret = self.mqtr.receive()
            if ret is None:
                continue
            if ret['routing_key'] in self.listening_node:
                logger.debug('write queue, receive from: {}'.format(ret['data']['node']))
                Udeque.write_deque(receive_que, ret['data'], max_len=self.receive_que_max_len)

        # 关闭连接
        self.mqtr_close()


    def auto_send(self, data_obj: dict):
        """写入数据到发送缓冲区，自动发送
        Args:
            data_obj  待发送数据
        """
        Udeque.write_deque(self._send_que, data_obj, max_len=self.send_que_max_len)


    def auto_read(self, pop=True):
        """从接收缓冲区读取数据
        Args:
            pop 是否弹出队列数据 
        Returns:
            None or data_obj        
        """
        return Udeque.read_deque(self._receive_que, pop)
