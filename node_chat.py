# coding=utf-8
# 在线Chat节点
import sys
# import base64
import json
from time import sleep
from collections import deque
import threading
import time

#1.日志系统初始化,配置log等级
from utility import mlogging
mlogging.logger_config('chat', mlogging.INFO, False)
#2.导入logger模块
from utility.mlogging import logger
# from utility.keyboard import KBHit


from mq_base_node import MqBaseNode, mq_close
from chat.openai_chat import OpenAIChat
FILE_PATH = "./conversation.json"

class ChatNode(MqBaseNode):
    """chat节点
    """
    def __init__(self, config: dict):
        """初始化
        Args:
            config  app参数配置信息
        """
        self.chat_config = config['chat']

        #---------------rabbitmq------------------
        super().__init__(config['rabbitmq']) 

        self.que_max_len = 5000
        self.set_que_max_len(self.que_max_len)

        #-----------------------------------------
        # 键盘控制
        # self.keyboard = KBHit()
        self.node_exit = False
        try:
            with open(FILE_PATH, "x", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=4)
        except FileExistsError:
            pass # 如果文件已存在，则无需初始化
        self.chat = OpenAIChat(self.chat_config)

        ## 本轮聊天ID
        self.chat_id = 0
        ## 取消的聊天ID
        self.cancel_chat_id = -1

    '''
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
        self.node_exit = True
        logger.info('app exit')

    
    def create_answer_msg(self, msg: dict, chat_id: int):
        """创建聊天响应消息
        Args:
            msg, 聊天响应消息
        """
        data_obj = {
            'node': "chat",
            'topic': "chat/answer",
            'type': "json",
            'data':{
                'chat_id': chat_id,
                'seq': msg['seq'],
                'text': msg['text'],
            }    
        }
        return data_obj

    # 添加一条对话记录     
    def add_conversation(self, bot_text: str, chat_id: int):
        # 获取当前时间戳
        time_stamp = time.time()
        # 读取现有记录
        with open(FILE_PATH, "r", encoding="utf-8") as f:
            conversations = json.load(f)
        data_obj = {
                'time_stamp': time_stamp,
                'bot_text': bot_text
        }
        # 添加新记录
        conversations.append(data_obj)
        # 将更新后的记录写回文件
        with open(FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(conversations, f, ensure_ascii=False, indent=4)

    def handle_mq_msg(self, msg: dict, stream=True):
        """mq 消息处理, 根据请求执行相应操作
        Args: 
            msg  从订阅节点接收到的消息
            stream 是否启动流失响应
        TODO: 增加聊天打断检测
        """
        
        logger.debug("got mq msg, topic: {}".format(msg['topic']))
        topic = msg['topic']

        if topic == 'request/cancel':
            self.cancel_chat_id = msg['data']['chat_id']
            logger.info('receive cancel signal,current chat_id: {}, cancel chat_id: {}'.format(self.chat_id, self.cancel_chat_id))

        elif topic == 'asr/response':
            logger.debug(msg)
            text = msg['data']['text']
            self.chat_id = msg['data']['chat_id']
            logger.info('user: {}'.format(text))

            ## 判断是否为取消的ID,如果是则不进行chat请求
            if self.chat_id <= self.cancel_chat_id:
                logger.info('this chat already cancel, chat_id: {}, cancel chat_id: {}'.format(self.chat_id, self.cancel_chat_id))
                return

            if stream:
                ## 流式对话
                bot_list = []
                reponse = self.chat.get_response_stream(text)
                for chunk in reponse:
                    answer_msg = self.chat.decode_chunk(chunk)
                    if answer_msg is not None:
                        logger.info("{:2} {}".format(answer_msg['seq'], answer_msg['text']))
                        self.auto_send(self.create_answer_msg(answer_msg, self.chat_id))
                        bot_list.append(answer_msg)  # 将 chunk 添加到列表
                # bot_text = ''.join(bot_list) # 将列表字符串拼接为一个整体
                self.add_conversation(bot_list[0]['text'], self.chat_id) # 将bot回复保存到另一个json文件中
                        
            else:
                answer_msg = self.chat.get_response(text)
                logger.info("{:2} {}".format(answer_msg['seq'], answer_msg['text']))
                self.auto_send(self.create_answer_msg(answer_msg, self.chat_id))
                self.add_conversation(answer_msg, self.chat_id) # 将bot回复保存到另一个json文件中
            
            


    def launch(self):
        """循环任务
        """
        ## 启动rabitmq transport线程
        self.transport_start()
        # self.initialize_conversation_file()
        while not self.node_exit:
            sleep(0.001)
            # self.keyboard_control()
            ## 读取rabitmq数据
            mq_msg = self.auto_read()
            if mq_msg is not None:
                self.handle_mq_msg(mq_msg)


def main(config: dict):
    """入口函数
    """
    chat_node = ChatNode(config)
    chat_node.launch()


if __name__=='__main__':
    """APP入口
    """
    logger.info('chat node start...')

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
