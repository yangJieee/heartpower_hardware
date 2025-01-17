# coding=utf-8


class WsEnumTypes():

    NONE = 3000  # 空数据
    STATUS_CONNECTED = 3001  # 已连接
    STATUS_CLOSE = 3002  # 连接断开
    STATUS_MSG_OK = 3003  # 正常接收到消息
    ACTION_CONNECT = 3005  # 执行连接
    ACTION_CLOSE = 3006  # 执行关闭连接
    ACTION_SEND_MSG = 3007  # 发送消息

    @classmethod
    def is_type(cls, msg):
        if msg >= 3000 and msg <= 3010:
            return True
        return False
