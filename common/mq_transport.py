# coding=utf-8
"""RabbitMQ通信
"""
import json
import pika

class MqTransport():
    """RabbitMQ消息发布订阅
    """
    def __init__(self, config: dict):
        """
        Args:
            config: rabbitmq配置参数
        """
        #连接到消息代理
        self.config = config
        credentials = pika.PlainCredentials(config['server']['username'], config['server']['password'])
        params = pika.ConnectionParameters(host=config['server']['host'],
            port=config['server']['port'], heartbeat=config['server']['heartbeat'], blocked_connection_timeout=300, credentials=credentials)
        self.connection = pika.BlockingConnection(params)
        self.channel = self.connection.channel()
        self.exchange_id = config['exchange_id']
        # 声明交换机
        self.channel.exchange_declare(exchange=self.exchange_id, exchange_type='topic')

        # 设置消息预取数量,客户端处理消息过慢时启用,达到设定数值是不再接收消息
        self.channel.basic_qos(prefetch_count=2)

        # 创建一个随机独占队列, 队列名设置为空，会返回唯一ID
        self.queue_result = self.channel.queue_declare(queue='', exclusive=True)
        self.queue_id = self.queue_result.method.queue
        self.receive_active = False


    def close(self):
        """关闭连接
        """
        self.channel.close()
        self.connection.close()


    def _send(self, routing_key: str, msg: dict):
        """序列化后发送
        """
        json_str = json.dumps(msg)
        self.channel.basic_publish(exchange=self.exchange_id, routing_key=routing_key, body=json_str)


    def send_str(self, routing_key: str, msg: str):
        """发布字符串消息
        #  routing_key 路由
        """
        data = {'type': 'string', 'data': msg}
        self._send(routing_key, data)


    def send_obj(self, routing_key: str, msg: dict):
        """发布序列化对象
        """
        data = {'type': 'object', 'data': msg}
        self._send(routing_key, data)


    def enable_receive(self, routing_keys = None):
        """绑定监听队列
        Args:
            routing_keys,  要监听的路由,默认监听交换机下的所有路由
        """
        if routing_keys is None:
            routing_keys = ['*']
        # 绑定队列到Exchange, 支持多个binding_key(路由)
        for routing_key in routing_keys:
            self.channel.queue_bind(exchange=self.exchange_id, queue=self.queue_id, routing_key=routing_key)
        self.receive_active = True


    def receive(self):
        """单次接收消息,主动查询非阻塞
        """
        if not self.receive_active:
            print('mq transport enable_receive not set.')
            return None
        method, properties, body = self.channel.basic_get(queue=self.queue_id, auto_ack=True)
        if method is None:
            return None
        result = {'routing_key': method.routing_key}
        data = json.loads(body)
        result.update(data)
        return result
