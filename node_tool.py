# coding=utf-8
# tool节点
# 1. 设备测试和管理
import sys
import base64
import json
from time import sleep

#1.日志系统初始化,配置log等级
from utility import mlogging
mlogging.logger_config('tool', mlogging.INFO, False)
#2.导入logger模块
from utility.mlogging import logger
from utility.keyboard import KBHit

import audio.audio_common as ac
from audio.opus_decoder import OpusDecoder

from mq_base_node import MqBaseNode, mq_close


class ToolNode(MqBaseNode):
    """tool节点
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

        # 键盘控制
        self.keyboard = KBHit()
        self.node_exit = False


        ## 音频数据缓存
        self.save_audio_buff = bytearray()
        ## 音频数据保存片段时长s
        self.save_audio_duration = 15  


    def keyboard_control(self):
        """control task.
        """
        if self.keyboard.kbhit():
            key_value = ord(self.keyboard.getch())
            # print(key_value)
            # if key_value == 27: # ESC
            if key_value == ord('q'): 
                logger.info('keyboard exit.')
                self.close()


    @mq_close
    def close(self):
        """关闭节点
        """
        self.node_exit = True
        logger.info('app exit')


    def create_xxx_msg(self, text: str):
        data_obj = {
            'node': "asr",
            'topic': "asr/response",
            'type': "json",
            'data':{
                'text': text,
            }    
        }
        return data_obj


    def save_audio_opus(self, opus_bytes: bytes, seq_id: int):
        """保存opus音频文件到本地
        """
        file_path = "./temp/opus-seqs/" + str(seq_id).zfill(2) + ".opus"
        with open(file_path, 'wb') as file:
            file.write(opus_bytes)


    def handle_mq_msg(self, msg: dict):
        """mq 消息处理, 根据请求执行相应操作
        Args:
            msg  从订阅节点接收到的消息
        """
        logger.debug("got mq msg, topic: {}".format(msg['topic']))
        if msg['topic'] == 'test/mic':
            logger.debug("got mq msg, topic: {}".format(msg['topic']))
            if 'data' not in msg:
                logger.warning("get data from msg fail. msg: {}", msg)
                return
            seq_id = msg['data']['seq_id']
            audio_info = msg['data']['audio']
            # print(audio_info)
            audio_format = audio_info['format']
            samplerate = audio_info['samplerate']
            channel_id = audio_info['channel_id']

            ## 1.音频数据解码(Base64解码)
            audio_bytes = base64.b64decode(audio_info['buff'])
            logger.debug('receive audio, samplerate: {}, format: {}, len: {}'.format(samplerate, audio_format, len(audio_bytes)))
            logger.info("got audio, seq id: {}".format(seq_id))

            self.save_audio_buff.extend(audio_bytes)
            ## 2.保存音频数据到本地
            if len(self.save_audio_buff) > samplerate * 2 * self.save_audio_duration:
                if channel_id == 0: 
                    file_path = './test_output/mic_right.wav'
                else:
                    file_path = './test_output/mic_left.wav'
                ac.saveWav(file_path, bytes(self.save_audio_buff), samplerate)
                logger.info("save wav audio to: {}".format(file_path))
                self.save_audio_buff.clear()
                        

    def launch(self):
        """循环任务
        """
        ## 启动rabbbitmq传输子线程
        self.transport_start()

        while not self.node_exit:
            # logger.info('asr main loop.')
            # await asyncio.sleep(0.01)
            sleep(0.01)
            self.keyboard_control()
            ## 获取接收队列数据
            mq_msg = self.auto_read()
            if mq_msg is not None:
                self.handle_mq_msg(mq_msg)

   
def main(config: dict):
    """入口函数
    """
    tool_node = ToolNode(config)
    tool_node.launch()


if __name__=='__main__':
    """APP入口
    """
    logger.info('tool node start...')

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
