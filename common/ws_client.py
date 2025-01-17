# coding=utf-8
"""websocket client
"""
# import json
from typing import Union
from tornado.ioloop import IOLoop, PeriodicCallback
from tornado import gen
from tornado.websocket import websocket_connect
from tornado.httpclient import HTTPRequest

from utility.mlogging import logger

from collections import deque
from common.u_deque import Udeque  
from common.ws_enum_types import WsEnumTypes


class WsClient():
    def __init__(self, url: Union[str, HTTPRequest], que_max_len=10):
        """
        Args:
            url: str or httpclient.HTTPRequest
            que_max_len   队列缓冲区最大值

        Example:
            header = {"Authorization": f"Bearer"}
            request = httpclient.HTTPRequest(url=url, headers=header)
            client = WsClient(request)
            client.run()
        """
        self.url = url
        # self.timeout = timeout

        self.send_que = deque() 
        self.send_que_max_len = que_max_len

        self.receive_que = deque()
        self.receive_que_max_len = que_max_len

        self.ws = None

        self.keep_alive_task = False
        self.send_task = None
        self.ioloop = None


    def set_keep_alive(self, enable: bool):
        self.keep_alive_enable = enable


    def run(self, connect = False, keep_alive_enable = False):
        """启动客户端
        Args:
            connect 是否连接
        """
        self.ioloop = IOLoop.instance()

        ## ws连接
        if connect:
            self.connect()

        ## 创建keep alive任务
        if keep_alive_enable:
            self.keep_alive_task = PeriodicCallback(self._keep_alive_callback, 5000)
            self.keep_alive_task.start()

        ## 创建自动发送定时任务
        self.send_task = PeriodicCallback(self._execute_callback, 50)
        self.receive_task = PeriodicCallback(self._receive_callback, 50)

        self.send_task.start()
        self.receive_task.start()

        self.ioloop.start()


    def close(self):
        """退出客户端
        """
        if self.send_task is not None:
            if self.send_task.is_running():
                self.send_task.stop()
        if self.ioloop is not None:
            self.ioloop.stop()
        logger.info("ws client exit.")


    def connect_close(self):
        """关闭连接
        """
        if self.ws is not None:
            self.ws.close()
            logger.info("ws connect close.")


    @gen.coroutine # 将普通的生成器函数转换为Tornado协程
    def connect(self):
        logger.info("ws trying to connect")
        try:
            self.ws = yield websocket_connect(self.url)
        except Exception as e:
            logger.error("ws connection error: {}".format(e))
        else:
            logger.info("ws connected")
            self._write_receive_que(WsEnumTypes.STATUS_CONNECTED)


    @gen.coroutine
    def _receive_callback(self):
        """ws数据接收
        """
        while True:
            yield gen.sleep(0.001)
            if self.ws == None:
                continue
            msg = yield self.ws.read_message()
            if msg is None:
                logger.info("ws connection closed")
                self.ws = None
                ## 返回连接断开消息
                self._write_receive_que(WsEnumTypes.STATUS_CLOSE)
                break
            # print('ws receive:', msg)
            # 写入消息接收队列
            self._write_receive_que(WsEnumTypes.STATUS_MSG_OK, msg)


    def _keep_alive_callback(self):
        """连接保持函数
        """
        logger.info('keep alive task')
        if self.ws is None:
            self.connect()
        else:
            pass
            # self.ws.write_message("keep alive")


    @gen.coroutine
    def _execute_callback(self, audo_connect = True):
        """读取队列内容(str msg)并发送
            1. 若有消息需要发送且,检测到连接断开,会先自动连接
        Note: 若连接断未及时检测到，会存在发送不成功的情形
        """
        while True:
            yield gen.sleep(0.001)
            data = Udeque.read_deque(self.send_que, pop=True)
            if data is None:
                yield gen.sleep(0.005)  # 延时5ms
                continue
            status = data['status']
            msg = data['msg']

            ## 判断是否需要执行重连操作
            if status == WsEnumTypes.ACTION_CONNECT or (msg is not None and self.ws == None and audo_connect):
                logger.info("ws connect ...")
                yield self.connect()
                # 等待连接完成
                while True:
                    yield gen.sleep(0.01)  # 延时10ms
                    if self.ws is not None:
                        break
            # print('send', msg)
            ## 进行消息发送
            if msg is not None and self.ws is not None:
                if type(msg) is bytes:
                    yield self.ws.write_message(msg, True) #注意开启binary模式
                else:
                    yield self.ws.write_message(msg)


    def _write_receive_que(self, status=WsEnumTypes.NONE, msg=None):
        """消息输出
        Args:
            status  websocket enumtype 数据
            msg 复合类型消息数据
        """
        data = {}
        data['status'] = status
        data['msg'] = msg
        Udeque.write_deque(self.receive_que, data, self.receive_que_max_len)


    def _auto_execute(self, status, msg=None):
        """自动执行连接或发送消息等操作
        Args:
            status  websocket enumtype 数据
            msg 复合类型消息数据
        """
        data = {}
        data['status'] = status
        data['msg'] = msg
        Udeque.write_deque(self.send_que, data, self.send_que_max_len)


    def auto_send(self, msg):
        """自动发送消息
        Args:
            msg 复合类型消息数据
        """
        self._auto_execute(WsEnumTypes.ACTION_SEND_MSG, msg)


    def auto_read(self, pop=True):
        """从接收队列读取消息
        Returns:
            None or 数据消息
        """
        return Udeque.read_deque(self.receive_que, pop)

    
    def auto_connect(self):
        """自动连接,写入连接命令到队列
        Returns:
        """
        self._auto_execute(WsEnumTypes.ACTION_CONNECT)

