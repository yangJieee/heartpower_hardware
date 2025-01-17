
#coding=utf-8
from collections import deque
import tornado.web
from tornado.ioloop import IOLoop
import tornado.websocket
from tornado.ioloop import PeriodicCallback
from tornado.websocket import WebSocketHandler
import asyncio

from utility.mlogging import logger

from common.u_deque import Udeque  



class WsServerBase(WebSocketHandler):
    """tornado websocket server
    Args: 
    """
    def initialize(self, send_que: deque, receive_que: deque, que_max_len, close_event: asyncio.Event):
        """连接初始化(每次连接成功会调用)
        """
        self.que_max_len = que_max_len
        # 保存待发送信息
        self.send_que = send_que
        self.send_que_max_len = self.que_max_len
        # 保存接收信息
        self.receive_que = receive_que
        self.receive_que_max_len = self.que_max_len

        self._close_event = close_event

        self.close_task = None
        self.send_task = None


    async def _async_send(self, msg):
        """ 异步发送消息
        Args:
            msg 复合类型消息数据
        """
        if type(msg) is bytes:
            await self.write_message(msg, True)
        else:
            await self.write_message(msg)

    
    async def open(self):
        """ 连接成功回调
        """
        # self.set_nodelay(True)  #小包发送,降低延迟（可能占用更多带宽）

        # 启动异步定时器，每秒 n ms执行一次回调函数
        self.send_task = PeriodicCallback(self._send_callback, 50)
        self.send_task.start()

        self.close_task = PeriodicCallback(self._close_callback, 50)
        self.close_task.start()

        logger.info('ws connected.')


    async def _send_callback(self):
        """异步消息自动发送
        """
        while True:
            await asyncio.sleep(0.005)
            msg = Udeque.read_deque(self.send_que, pop=False)
            if msg is not None:
                await self._async_send(msg)
                _ = Udeque.read_deque(self.send_que, pop=True)
            else:
                break


    def _close(self):
        """关闭服务器
        """
        self.close()  # 关闭连接
        if self.send_task is not None:
            if self.send_task.is_running():
                self.send_task.stop()
        if self.close_task is not None:
            self.close_task.stop()


    def _close_callback(self):
        """ 主动关闭连接回调
        """
        if self._close_event.is_set():
            self._close()


    def on_message(self, message):
        """
        消息接收回调
        """
        # logger.info("ws receive: {}".format(message))
        #将消息写入接收队列
        Udeque.write_deque(self.receive_que, message, self.receive_que_max_len)


    def on_close(self):
        """连接关闭回调
        """
        logger.info('ws connection close.')
        self._close()


class WsServer():
    def __init__(self, url: str, port: int, que_max_len = 10):
        """
        Args:
            url   addr, 如 '/'
            port  server port 
            que_max_len  缓冲队列最大长度
        """
        self.url = url
        self.port= port

        self.que_max_len = que_max_len
        self.send_que = deque()
        self.receive_que = deque()

        self.close_event = asyncio.Event()


    def run(self):
        """ws server启动
        """
        self.ioloop = IOLoop.instance()
        app = tornado.web.Application([ 
            tornado.web.url(self.url, WsServerBase, dict(send_que=self.send_que, receive_que=self.receive_que,
            que_max_len=self.que_max_len, close_event=self.close_event) )]) 
        app.listen(self.port)
        logger.info('ws server is running on port {}'.format(self.port))
        self.ioloop.start()

    
    def close(self):
        """关闭连接并退出服务器
        """
        self.close_event.set()
        if self.ioloop is not None:
            self.ioloop.stop()
        logger.info("ws server exit.")


    def auto_send(self, msg):
        """数据写入ws发送缓冲区, 自动发送
        Args:
            msg 复合类型消息数据
        """
        Udeque.write_deque(self.send_que, msg, self.que_max_len)


    def auto_read(self, pop=True):
        """从ws接收缓冲区读取数据
        """
        return Udeque.read_deque(self.receive_que, pop)

