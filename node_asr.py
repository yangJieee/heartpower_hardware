# coding=utf-8
# 在线ASR节点
import sys
import base64
import json
from time import sleep
import time

#1.日志系统初始化,配置log等级
from utility import mlogging
mlogging.logger_config('asr', mlogging.INFO, False)
#2.导入logger模块
from utility.mlogging import logger
# from utility.keyboard import KBHit

import audio.audio_common as ac
from audio.opus_decoder import OpusDecoder

from mq_base_node import MqBaseNode, mq_close
from asr.volc_asr import VolcASR

FILE_PATH = "./conversation.json"

class ASRNode(MqBaseNode):
    """asr节点
    """
    def __init__(self, config: dict):
        """初始化
        Args:
            config  app参数配置信息
        """
        # rabbitmq初始化
        super().__init__(config['rabbitmq']) 
        # rabbitmq接收缓冲队列最大长度
        self.set_que_max_len(5000)

        self.asr_config = config['asr']

        # 键盘控制
        # self.keyboard = KBHit()
        self.node_exit = False

        self.asr = VolcASR(config=self.asr_config)

        self.audio_samplerate = self.asr_config['common']['audio']['samplerate']
        self.decoder = OpusDecoder(samplerate=self.audio_samplerate, channels=1, seq_time=0.02)

        # 进行片段缓冲
        self.audio_buff = bytearray()  

        # 最小片段长度
        # self.audio_seg_min = 640*10
        # 测试发现小片段发送整体识别率低(可能服务器处理逻辑的问题)
        # 一次发送就好(响应速度差不多)
        self.audio_seg_min = 640*200

        self.audio_req_ready = False
        # 识别有效文本最小长度,小于该值丢弃
        self.valid_text_min = self.asr_config['valid_text_min']
        ## 是否保存音频到本地
        self.save_audio_opus_enable = self.asr_config['save_audio_opus']
        self.save_audio_wav_enable = self.asr_config['save_audio_wav']
        # 本次请求所有音频数据缓冲
        self.audio_buff_all = bytearray()  

        ## TODO:默认静音片段去除

        ## 本轮聊天id
        self.chat_id = 0

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
        self.asr.close()
        self.node_exit = True
        logger.info('app exit')


    def create_asr_msg(self, text: str, chat_id: int):
        """创建asr识别结果消息(发送至chat节点)
        Args:
            text     聊天响应消息
            chat_id  本轮聊天ID
        """
        data_obj = {
            'node': "asr",
            'topic': "asr/response",
            'type': "json",
            'data':{
                'chat_id': chat_id,
                'text': text,
            }    
        }
        return data_obj


    def create_answer_msg_one(self, text: str, chat_id: int):
        """创建单条聊天响应消息,用于用户提示(直接发送至tts节点)
        Args:
            text     聊天响应消息
            chat_id  本轮聊天ID
        """
        data_obj = {
            'node': "asr",
            'topic': "chat/answer",
            'type': "json",
            'data':{
                'chat_id': chat_id,
                'seq': -1,
                'text': text
            }    
        }
        return data_obj


    def save_audio_aac(self, aac_bytes: bytes, seq_id: int):
        """保存音频文件到本地
        """
        file_path = "./temp/aac-seqs/" + str(seq_id).zfill(2) + ".aac"
        with open(file_path, 'wb') as file:
            file.write(aac_bytes)


    def save_audio_opus(self, opus_bytes: bytes, seq_id: int):
        """保存opus音频文件到本地
        """
        file_path = "./temp/opus-seqs/" + str(seq_id).zfill(2) + ".opus"
        with open(file_path, 'wb') as file:
            file.write(opus_bytes)


    def handle_execute_error(self):
        """处理执行错误情况
        """
        self.asr.connect_close()
        self.audio_req_ready = False

    def initialize_conversation_file():
        try:
            with open(FILE_PATH, "x", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=4)
        except FileExistsError:
            pass # 如果文件已存在，则无需初始化

    # 添加一条对话记录
    def add_conversation(self, user_text: str, chat_id: int):
        # 获取当前时间戳
        time_stamp = time.time()
        # 读取现有记录
        with open(FILE_PATH, "r", encoding="utf-8") as f:
            conversations = json.load(f)
        data_obj = {
                'time_stamp': time_stamp,
                'user_text': user_text
        }
        # 添加新记录
        conversations.append(data_obj)
        # 将更新后的记录写回文件
        with open(FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(conversations, f, ensure_ascii=False, indent=4)
        
    def create_asr_msg(self, text: str, chat_id: int):
        """创建asr识别结果消息(发送至chat节点)
        Args:
            text     聊天响应消息
            chat_id  本轮聊天ID
        """
        data_obj = {
            'node': "asr",
            'topic': "asr/response",
            'type': "json",
            'data':{
                'chat_id': chat_id,
                'text': text,
            }    
        }
        return data_obj

    def execute(self, seq_id: int, audio_bytes: bytes):
        """执行ASR,并发布结果
        TODO: 增加超时机制，处理部分异常情况,如: 
              1.接收到开始音频信号，却没收到结束音频信号
        Args:
            seq_id:       音频片段id
            audio_bytes:  音频片段数据
        """
        wait_start_response = False 
        wait_end_response = False 
        wait_midle_response = False 

        ## 发送开始请求
        if seq_id == 0:
            logger.info("voice start...")
            self.asr.execute_start_req()
            self.audio_req_ready = False
            wait_start_response = True

        ## 等待开始信号
        if wait_start_response:
            ## 等待成功请求响应, TODO: 若响应失败会陷入循环
            re_request = False
            while True:
                # print('0000')
                sleep(0.001)
                res = self.asr.get_result()
                if res == None:
                    continue
                if 'status' not in res:
                    logger.warning('asr response invaild.')
                    self.handle_execute_error()
                    return
                if res['status'] == "DISCONNECT":
                    logger.info('ws already disconnect.')
                    # 进行自动重连
                    self.asr.auto_connect()
                    re_request = True
                elif res['status'] == "CONNECTED":
                    if re_request == True: # 再次发送请求
                        re_request = False
                        self.asr.execute_start_req()
                elif res['status'] == "REQ_OK":
                    logger.info("asr server ready, can start send audio segment.")
                    # 记录时间
                    self.audio_req_ready = True
                    break

        ## 判断是否可以进行音频请求
        if not self.audio_req_ready:
            logger.warning("asr server no ready, please ensure start request success.")
            return

        ## 发送音频请求
        if seq_id >= 0:
            logger.debug("voice active...")
            self.asr.execute_audio_req(audio_bytes, end_seq=False)
            wait_midle_response = True
        else :
            logger.info("voice end.")
            self.asr.execute_audio_req(audio_bytes, end_seq=True)
            wait_end_response = True

        ## 中间片段状态响应消息,不处理
        # TODO: 增加超时退出机制
        if wait_midle_response:
            while True:
                sleep(0.001)
                res = self.asr.get_result()
                if res == None:
                    break
                if 'status' not in res:
                    logger.warning('asr response invaild.')
                    self.handle_execute_error()
                    return
                if res['status'] == "DISCONNECT":
                    logger.warning('ws disconnect.')
                    self.audio_req_ready = False
                    break

        ## 等待结束信号
        if wait_end_response:
            while True:
                sleep(0.001)
                # print(222)
                ## 等待成功请求响应
                res = self.asr.get_result()
                if res is None:
                    continue
                if 'status' not in res:
                    logger.warning('asr response invaild.')
                    self.handle_execute_error()
                    return
                # print(res)
                if res['status'] == "DISCONNECT":
                    logger.warning('ws disconnect.')
                    self.audio_req_ready = False
                    break
                if res['status'] == "VOICE_PART":
                    logger.debug(res)
                elif res['status'] == "VOICE_ALL":
                    self.audio_req_ready = False
                    text = res['result'][0]['text']
                    logger.info('识别结果: {}'.format(text))
                    if len(text) >= self.valid_text_min:
                        ## 发布语音识别结果
                        self.auto_send(self.create_asr_msg(text, self.chat_id))
                        self.add_conversation(text, self.chat_id) #将语音识别结果保存为json文件 格式为{user,chat_id}yj
                    else:
                        logger.warning('recognition text too less.')
                        self.auto_send(self.create_answer_msg_one('我没听清,可以再说一遍吗', self.chat_id))
                    break
                elif res['status'] == "VOICE_NOT":
                    logger.warning("no found voice.")
                    # TODO: 判断是否为语音
                    # self.auto_send(self.create_answer_msg_one('我没听清,可以再说一遍吗', self.chat_id))
                    self.auto_send(self.create_answer_msg_one('', self.chat_id))
                    self.audio_req_ready = False
                    break


    def handle_mq_msg(self, msg: dict):
        """mq 消息处理, 根据请求执行相应操作
        Args:
            msg  从订阅节点接收到的消息
        """
        logger.debug("got mq msg, topic: {}".format(msg['topic']))
        if msg['topic'] == 'request/asr':
            logger.debug("got mq msg, topic: {}".format(msg['topic']))
            if 'data' not in msg:
                logger.warning("get data from msg fail. msg: {}", msg)
                return

            self.chat_id = msg['data']['chat_id']
            seq_id = msg['data']['seq_id']
            audio_info = msg['data']['audio']
            # print(audio_info)
            audio_format = audio_info['format']
            samplerate = audio_info['samplerate']
            '''
            在消息队列中，使用 JSON 格式封装消息是常见的做法。
            JSON 不支持直接嵌入二进制数据，因此需要将音频数据编码为 Base64 字符串后再传输。
            传输前：
            将音频数据（如二进制 Opus 数据）进行 Base64 编码，转为字符串形式，嵌入 JSON 消息。
            接收后：
            收到的 Base64 编码字符串通过 base64.b64decode() 解码，恢复为原始的二进制音频数据。
            根据音频格式（如 Opus），使用专用解码器进一步处理。
            因此，使用 Base64 解码的目的是处理一种传输中间格式，确保音频数据可以在消息队列或网络环境中安全传输，与输入音频的具体格式间接相关。
            '''
            ## 1.音频数据解码(Base64解码)
            audio_bytes = base64.b64decode(audio_info['buff'])
            logger.debug('receive audio, samplerate: {}, format: {}, len: {}'.format(samplerate, audio_format, len(audio_bytes)))
            logger.debug("got audio, seq id: {}".format(seq_id))

            ## 2.音频解码
            decode_bytes = self.decoder.decode(audio_bytes)
            # logger.debug("decode bytes len: {}".format(len(decode_bytes)))
            if len(decode_bytes) != 640:
                logger.warning("decode bytes fail, len: {}".format(len(decode_bytes)))

            ## 3.发送音频请求
            if seq_id == 0:
                # 首次直接执行ASR请求
                self.execute(seq_id, decode_bytes)
            else:
                ## 后续请求进行片段缓冲, 减少发送片段，可提高响应速度
                self.audio_buff.extend(decode_bytes)
                if len(self.audio_buff) >= self.audio_seg_min or seq_id < 0:
                    self.execute(seq_id, self.audio_buff)
                    self.audio_buff.clear()

                        
            ## 音频数据保存
            if self.save_audio_opus_enable:
                ## 保存文件到本地
                if audio_format == 'opus':
                    self.save_audio_opus(audio_bytes, seq_id)
                else:
                    logger.error("invalid format: {}, not support.".format(audio_format))
                # print(audio_bytes)

            if self.save_audio_wav_enable:
                self.audio_buff_all.extend(decode_bytes)
                if seq_id < 0:
                    ac.saveWav('./temp/asr/asr.wav', bytes(self.audio_buff_all), samplerate)
                    self.audio_buff_all.clear()


    def launch(self):
        """循环任务
        """
        ## 启动rabbbitmq传输子线程
        self.transport_start()

        ## 启动asr client
        self.asr.launch()
        self.initialize_conversation_file()
        while not self.node_exit:
            # logger.info('asr main loop.')
            # await asyncio.sleep(0.01)
            sleep(0.01)
            # self.keyboard_control()
            ## 获取接收队列数据
            mq_msg = self.auto_read()
            if mq_msg is not None:
                self.handle_mq_msg(mq_msg)

   
def main(config: dict):
    """入口函数
    """
    asr_node = ASRNode(config)
    asr_node.launch()


if __name__=='__main__':
    """APP入口
    """
    logger.info('asr node start...')

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
