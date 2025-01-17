#coding=utf-8
# import os
from time import sleep
import json
import uuid
import json
import gzip
import copy
from collections import deque

import threading
from tornado.httpclient import HTTPRequest

from utility.mlogging import logger

from common.ws_client import WsClient
from common.ws_enum_types import WsEnumTypes


MESSAGE_TYPES = {11: "audio-only server response", 12: "frontend server response", 15: "error message from server"}
MESSAGE_TYPE_SPECIFIC_FLAGS = {0: "no sequence number", 1: "sequence number > 0",
                               2: "last message from server (seq < 0)", 3: "sequence number < 0"}
MESSAGE_SERIALIZATION_METHODS = {0: "no serialization", 1: "JSON", 15: "custom type"}
MESSAGE_COMPRESSIONS = {0: "no compression", 1: "gzip", 15: "custom compression method"}



def hand_response(seq_num = 0, seq_size = 0, seq_data = None, status = None):
    """处理合成响应数据
      1.增加状态标志, 0表示开始 1中间数据 2合成结束, -1合成失败
    Args: data  合成响应数据
    """
    data = {}
    if status == -1:
        data['status'] = status
        data['seq_size'] = 0
        data['seq_num'] = 0
        data['data'] = None
        return data

    data['seq_size'] = seq_size
    data['seq_num'] = seq_num
    data['data'] = seq_data 

    if data['seq_num'] == 0:
        data['status'] = 0
    elif data['seq_num'] > 0:
        data['status'] = 1
    else:
        data['status'] = 2
    return data


def parse_response(res):
    """解码tts响应数据
    Args:
        res: 原始响应数据
    Returns:
        None or 解码到的数据 {'seq_num':, 'seq_size':, 'data': }
    """
    result = {'seq_num': 0, 'seq_size': 0, 'data': [] }
    logger.info("--------------------------- response ---------------------------")
    # print(f"response raw bytes: {res}")
    protocol_version = res[0] >> 4
    header_size = res[0] & 0x0f
    message_type = res[1] >> 4
    message_type_specific_flags = res[1] & 0x0f
    serialization_method = res[2] >> 4
    message_compression = res[2] & 0x0f
    reserved = res[3]
    header_extensions = res[4:header_size*4]
    payload = res[header_size*4:]
    logger.debug(f"            Protocol version: {protocol_version:#x} - version {protocol_version}")
    logger.debug(f"                 Header size: {header_size:#x} - {header_size * 4} bytes ")
    logger.debug(f"                Message type: {message_type:#x} - {MESSAGE_TYPES[message_type]}")
    logger.debug(f" Message type specific flags: {message_type_specific_flags:#x} - {MESSAGE_TYPE_SPECIFIC_FLAGS[message_type_specific_flags]}")
    logger.debug(f"Message serialization method: {serialization_method:#x} - {MESSAGE_SERIALIZATION_METHODS[serialization_method]}")
    logger.debug(f"         Message compression: {message_compression:#x} - {MESSAGE_COMPRESSIONS[message_compression]}")
    logger.debug(f"                    Reserved: {reserved:#04x}")
    if header_size != 1:
        logger.info(f"Header extensions: {header_extensions}")
    if message_type == 0xb:  # audio-only server response
        if message_type_specific_flags == 0:  # no sequence number as ACK  (可作为开始信号)
            logger.info("Payload size: 0")
            sequence_number = 0
            payload_size = 0
            payload = []
        else:
            sequence_number = int.from_bytes(payload[:4], "big", signed=True)
            payload_size = int.from_bytes(payload[4:8], "big", signed=False)
            payload = payload[8:]
            logger.info(f"Sequence number: {sequence_number}")
            logger.info(f"Payload size: {payload_size} bytes")
        ## 保存payload
        # file.write(payload)
        result = hand_response(sequence_number, payload_size, seq_data=payload)
        return result

    elif message_type == 0xf:
        code = int.from_bytes(payload[:4], "big", signed=False)
        msg_size = int.from_bytes(payload[4:8], "big", signed=False)
        error_msg = payload[8:]
        if message_compression == 1:
            error_msg = gzip.decompress(error_msg)
        error_msg = str(error_msg, "utf-8")
        logger.warn(f"Error message code: {code}")
        logger.warn(f"Error message size: {msg_size} bytes")
        logger.warn(f"Error message: {error_msg}")
        result = hand_response(status=-1)
        return result
    elif message_type == 0xc:
        msg_size = int.from_bytes(payload[:4], "big", signed=False)
        payload = payload[4:]
        if message_compression == 1:
            payload = gzip.decompress(payload)
        logger.warn(f"Frontend message: {payload}")
    else:
        logger.warn("undefined message type!")
        result = hand_response(status=-1)
        return result


class VolcTTSClient():
    """Volc语音合成, websocket接口
    """
    def __init__(self, appid, token, cluster, config: dict):
        """
        Args:
            config:  tts配置参数
        """
        self.config = config
        self.audio_config = config['common']['audio']
        self.api_url = self.config['volc']['ws_url']
        self.silence_duration = self.config['volc']['silence_duration']
        self.voice_type = self.config['volc']['voice_type']

        self.appid = appid
        self.token = token
        self.cluster = cluster 
        self.operation_type = 'query'

        # version: b0001 (4 bits)
        # header size: b0001 (4 bits)
        # message type: b0001 (Full client request) (4bits)
        # message type specific flags: b0000 (none) (4bits)
        # message serialization method: b0001 (JSON) (4 bits)
        # message compression: b0001 (gzip) (4bits)
        # reserved data: 0x00 (1 byte)
        self.default_header = bytearray(b'\x11\x10\x11\x00')

        # 保存当前合成结果
        # self._result_que = deque()

        # 关于连接建立:
        # SDK说明，多次合成需要建立多次连接，但有时连接通道建立较慢,非常影响整体效果。
        # 实测: 单次连接也可以多次合成，但服务器可能会主动关闭连接
        # TODO: 加入空闲检测机制，空闲自动断开连接, 在收到合成请求(预请求)后及时重连

        # self.ws = create_connection(self.api_url, header=ws_header, timeout=600)
        header = {"Authorization": f"Bearer; {self.token}"}
        request = HTTPRequest(url=self.api_url, headers=header)
        # request = HTTPRequest(url="ws://192.168.3.104:9001/linker-dev")
        self._ws = WsClient(request)
        # 线程退出控制信号
        # self.ws_stop_event = threading.Event()
        # 创建ws子线程, 默认不连接
        self.init_connect = False

        if self.init_connect:
            logger.info('start connection...')
        self._ws_thread = threading.Thread(target=self._ws.run, args=(self.init_connect,))


    def wait_ws_connected(self):
        """等待ws客户端连接完成
        """
        while True:
            sleep(0.01) 
            res = self._ws.auto_read()
            if res is None:
                continue
            if res['status'] == WsEnumTypes.STATUS_CONNECTED:
                break


    def launch(self):
        """启动客户端
        """
        self._ws_thread.start()
        if self.init_connect:
            self.wait_ws_connected()


    def close(self):
        """退出客户端
        """
        self._ws.close()
        self._ws_thread.join()


    def _create_request_json(self, text: str, voice_type: str):
        """生成请求数据参数
        """
        request_json = {
            "app": {
                "appid": self.appid,
                "token": self.token,
                "cluster": self.cluster
            },
            "user": {
                "uid": "388808087185088"
            },
            "audio": {
                "voice_type": voice_type,
                "encoding": self.audio_config['codec'],
                # "compression_rate": self.audio_config['compression_rate'],  #测试无效，不传递
                "compression_rate": 10,
                "rate": self.audio_config['samplerate'],
                "speed_ratio": 1.0,
                "volume_ratio": 1.0,
                "pitch_ratio": 1.0,
                # "emotion": "happy",
            },
            "request": {
                "reqid": "xxx",
                "text": text,
                "text_type": "plain",
                "operation": "xxx"
            }
        }
        return request_json

    
    def _hand_result(self, data: dict):
        """处理合成响应数据
          1.增加状态标志, 0表示开始 1中间数据 2合成结束
        Args: data  合成响应数据
        """
        if data['seq_num'] == 0:
            data['status'] = 0
        elif data['seq_num'] > 0:
            data['status'] = 1
        else:
            data['status'] = 2
        return data


    def set_voice_type(self, voice_type: str):
        """设置音色
        """
        self.voice_type = voice_type
    

    def set_operation_type(self, operation_type):
        """设置合成结果返回方式
        Args:
            operation_type  'query' or 'submit' 单次返回或者流式返回 
        """
        self.operation_type = operation_type


    def execute(self, text: str):
        """提交语音合成请求
        Args:
            text: 待合成文本
        """
        if self.operation_type not in ['query', 'submit']:
            logger.error('tts operation_type error.')
            return

        submit_request_json = copy.deepcopy(self._create_request_json(text, self.voice_type))

        submit_request_json["request"]["reqid"] = str(uuid.uuid4())

        submit_request_json["request"]["operation"] = self.operation_type
        submit_request_json["request"]["silence_duration"] = self.silence_duration

        payload_bytes = str.encode(json.dumps(submit_request_json))
        payload_bytes = gzip.compress(payload_bytes)  # if no compression, comment this line
        full_client_request = bytearray(self.default_header)
        full_client_request.extend((len(payload_bytes)).to_bytes(4, 'big'))  # payload size(4 bytes)
        full_client_request.extend(payload_bytes)  # payload

        full_client_request = bytes(full_client_request)
        self._ws.auto_send(full_client_request)
        logger.debug('auto send full client request: {}'.format(full_client_request))
      

    def get_result(self):
        """获取api响应数据,在提交请求后调用
        Returns:
            None or data_obj: {
            'status': 状态表如下:
                'DISCONENCT'  服务器已断开  
                'CONENCTED'  服务器已连接
                'REQ_OK' 请求成功  

            'result': { 'seq_num': , 
                        'seq_size':, 
                        'data': ,  # 音频bytes数据
                        'status': 
                             0表示开始
                             1中间数据 
                             2合成结束, 
                            -1合成失败
                    }
            }
        """
        res = self._ws.auto_read()
        if res is None:
            return None
        result = {}
        result['result'] = None
        # print(1, res)
        # 先读取状态信息
        if res['status'] == WsEnumTypes.STATUS_CLOSE:
            result['status'] = "DISCONNECT"
            return result
        if res['status'] == WsEnumTypes.STATUS_CONNECTED:
            result['status'] = "CONNECTED"
            return result
        elif res['status'] == WsEnumTypes.STATUS_MSG_OK:
            result['status'] = "REQ_OK"
            msg = res['msg']
            msg = parse_response(msg)
            # print('tts reuslt:', msg)
            result['result'] = msg
            return result

        logger.warning('unknow status: {}'.format(res['status']))
        return None


    def auto_connect(self):
        """客户端自动连接
        Returns:
        """
        self._ws.auto_connect()


    def connect_close(self):
        """ws关闭连接
        """
        self._ws.connect_close()

