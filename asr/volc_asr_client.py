#coding=utf-8
import base64
import gzip
import hmac
import json
import uuid
from hashlib import sha256
from typing import List
from urllib.parse import urlparse

import threading
from tornado.httpclient import HTTPRequest

from collections import deque
from utility.mlogging import logger
from common.ws_client import WsClient
from common.ws_enum_types import WsEnumTypes 


# Base
PROTOCOL_VERSION = 0b0001
DEFAULT_HEADER_SIZE = 0b0001

PROTOCOL_VERSION_BITS = 4
HEADER_BITS = 4
MESSAGE_TYPE_BITS = 4
MESSAGE_TYPE_SPECIFIC_FLAGS_BITS = 4
MESSAGE_SERIALIZATION_BITS = 4
MESSAGE_COMPRESSION_BITS = 4
RESERVED_BITS = 8

# Message Type:
CLIENT_FULL_REQUEST = 0b0001
CLIENT_AUDIO_ONLY_REQUEST = 0b0010
SERVER_FULL_RESPONSE = 0b1001
SERVER_ACK = 0b1011
SERVER_ERROR_RESPONSE = 0b1111

# Message Type Specific Flags
NO_SEQUENCE = 0b0000  # no check sequence
POS_SEQUENCE = 0b0001
NEG_SEQUENCE = 0b0010
NEG_SEQUENCE_1 = 0b0011

# Message Serialization
NO_SERIALIZATION = 0b0000
JSON = 0b0001
THRIFT = 0b0011
CUSTOM_TYPE = 0b1111

# Message Compression
NO_COMPRESSION = 0b0000
GZIP = 0b0001
CUSTOM_COMPRESSION = 0b1111



def generate_header( version=PROTOCOL_VERSION,
        message_type=CLIENT_FULL_REQUEST,
        message_type_specific_flags=NO_SEQUENCE,
        serial_method=JSON,
        compression_type=GZIP,
        reserved_data=0x00,
        extension_header=bytes()):

    """
    protocol_version(4 bits), header_size(4 bits),
    message_type(4 bits), message_type_specific_flags(4 bits)
    serialization_method(4 bits) message_compression(4 bits)
    reserved （8bits) 保留字段
    header_extensions 扩展头(大小等于 8 * 4 * (header_size - 1) )
    """
    header = bytearray()
    header_size = int(len(extension_header) / 4) + 1
    header.append((version << 4) | header_size)
    header.append((message_type << 4) | message_type_specific_flags)
    header.append((serial_method << 4) | compression_type)
    header.append(reserved_data)
    header.extend(extension_header)
    return header


def generate_full_default_header():
    return generate_header()


def generate_audio_default_header():
    return generate_header(
        message_type=CLIENT_AUDIO_ONLY_REQUEST
    )


def generate_last_audio_default_header():
    return generate_header(
        message_type=CLIENT_AUDIO_ONLY_REQUEST,
        message_type_specific_flags=NEG_SEQUENCE
    )


def parse_response(res):
    """解码
    protocol_version(4 bits), header_size(4 bits),
    message_type(4 bits), message_type_specific_flags(4 bits)
    serialization_method(4 bits) message_compression(4 bits)
    reserved （8bits) 保留字段
    header_extensions 扩展头(大小等于 8 * 4 * (header_size - 1) )
    payload 类似与http 请求体
    """
    protocol_version = res[0] >> 4
    header_size = res[0] & 0x0f
    message_type = res[1] >> 4
    message_type_specific_flags = res[1] & 0x0f
    serialization_method = res[2] >> 4
    message_compression = res[2] & 0x0f
    reserved = res[3]
    header_extensions = res[4:header_size * 4]
    payload = res[header_size * 4:]
    result = {}
    payload_msg = None
    payload_size = 0
    if message_type == SERVER_FULL_RESPONSE:
        payload_size = int.from_bytes(payload[:4], "big", signed=True)
        payload_msg = payload[4:]
    elif message_type == SERVER_ACK:
        seq = int.from_bytes(payload[:4], "big", signed=True)
        result['seq'] = seq
        if len(payload) >= 8:
            payload_size = int.from_bytes(payload[4:8], "big", signed=False)
            payload_msg = payload[8:]
    elif message_type == SERVER_ERROR_RESPONSE:
        code = int.from_bytes(payload[:4], "big", signed=False)
        result['code'] = code
        payload_size = int.from_bytes(payload[4:8], "big", signed=False)
        payload_msg = payload[8:]
    if payload_msg is None:
        return result
    if message_compression == GZIP:
        payload_msg = gzip.decompress(payload_msg)
    if serialization_method == JSON:
        payload_msg = json.loads(str(payload_msg, "utf-8"))
    elif serialization_method != NO_SERIALIZATION:
        payload_msg = str(payload_msg, "utf-8")
    result['payload_msg'] = payload_msg
    result['payload_size'] = payload_size
    return result


class VolcAsrClient:
    def __init__(self, appid, token, cluster, **kwargs):
        """Asr WS客户端
        Args:
            **kwargs 可选参数
        """
        # self.audio_path = audio_path
        self.cluster = cluster
        self.appid = appid
        self.token = token
        self.success_code = 1000  # success code, default is 1000

        self.seg_duration = int(kwargs.get("seg_duration", 10000))
        self.nbest = int(kwargs.get("nbest", 1))
        self.api_url = kwargs.get("ws_url", "wss://openspeech.bytedance.com/api/v2/asr")
        self.uid = kwargs.get("uid", "streaming_asr_demo")
        self.workflow = kwargs.get("workflow", "audio_in,resample,partition,vad,fe,decode,itn,nlu_punctuate")
        self.show_language = kwargs.get("show_language", False)
        self.show_utterances = kwargs.get("show_utterances", False)   #开启分句返回,更详细(到字)

        self.result_type = kwargs.get("result_type", "single")  # 返回结果类型 "full" or "single"
        self.format = kwargs.get("format", "raw")  # raw(pcm) / wav / mp3 / ogg

        self.channels = kwargs.get("channels", 1)
        self.sampwidth = kwargs.get("sampwidth", 2)
        self.samplerate = kwargs.get("samplerate", 16000)
        self.codec = kwargs.get("codec", "raw") # raw / opus

        self.language = kwargs.get("language", "zh-CN")
        self.bits = kwargs.get("bits", 16)
        # self.audio_type = kwargs.get("audio_type", 1) ## 使用本地音频文件
        self.secret = kwargs.get("secret", "access_secret")
        self.auth_method = kwargs.get("auth_method", "token")

        # self.mp3_seg_size = int(kwargs.get("mp3_seg_size", 10000))
        # self.segment_size = self._get_segment_size()

        # 关于连接建立:
        # SDK说明，多次合成需要建立多次连接，但有时连接通道建立较慢,非常影响整体效果。
        # 实测: 单次连接也可以多次合成，但服务器可能会主动关闭连接
        # TODO: 加入空闲检测机制，空闲自动断开连接, 在收到合成请求(预请求)后及时重连
        # self.ws = create_connection(self.api_url, header=ws_header, timeout=600)
        # header = {"Authorization": f"Bearer; {self.token}"}

        header = {'Authorization': 'Bearer; {}'.format(self.token)}
        request = HTTPRequest(url=self.api_url, headers=header)
        self._ws = WsClient(request)

        # 创建ws子线程
        self._ws_thread = threading.Thread(target=self._ws.run, args=())

    
    def close(self):
        """退出客户端
        """
        self._ws.close()
        self._ws_thread.join()


    def launch(self):
        """启动客户端
        """
        self._ws_thread.start()


    def construct_request(self, reqid):
        req = {
            'app': {
                'appid': self.appid,
                'cluster': self.cluster,
                'token': self.token,
            },
            'user': {
                'uid': self.uid
            },
            'request': {
                'reqid': reqid,
                'nbest': self.nbest,
                'workflow': self.workflow,
                'show_language': self.show_language,
                'show_utterances': self.show_utterances,
                'result_type': self.result_type,
                "sequence": 1
            },
            'audio': {
                'format': self.format,
                'rate': self.samplerate,
                'language': self.language,
                'bits': self.bits,
                'channel': self.channels,
                'codec': self.codec
            }
        }
        return req


    @staticmethod
    def slice_data(data: bytes, chunk_size: int) -> (list, bool):
        """
        slice data
        :param data: wav data
        :param chunk_size: the segment size in one request
        :return: segment data, last flag
        """
        data_len = len(data)
        offset = 0
        while offset + chunk_size < data_len:
            yield data[offset: offset + chunk_size], False
            offset += chunk_size
        else:
            yield data[offset: data_len], True


    def _get_segment_size(self):
        """计算分片大小
        """
        size_per_sec = self.channels * self.sampwidth * self.samplerate
        segment_size = int(size_per_sec * self.seg_duration / 1000)
        return segment_size


    def execute_start_req(self):
        """提交语音识别起始请求
        Args:
            audio_bytes:  音频文件数据，wav格式
        请求成功响应如下:
            {'payload_msg': {'addition': {'duration': '0', 'logid': '202406272215514754B3B2400D5AB0AD60'}, 'code': 1000, 'message': 'Success', 
            'reqid': '691440b6-16ae-4aea-b67f-fdc333b060b5', 'sequence': 1}, 'payload_size': 157}
        """
        reqid = str(uuid.uuid4())
        # 构建 full client request，并序列化压缩
        request_params = self.construct_request(reqid)
        payload_bytes = str.encode(json.dumps(request_params))
        payload_bytes = gzip.compress(payload_bytes)

        full_client_request = bytearray(generate_full_default_header())
        full_client_request.extend((len(payload_bytes)).to_bytes(4, 'big'))  # payload size(4 bytes)
        full_client_request.extend(payload_bytes)  # payload
        # 转为bytes发送
        full_client_request = bytes(full_client_request)

        # print(full_client_request)
        # 发送首次请求信息      
        self._ws.auto_send(full_client_request)
        logger.debug('asr full_request send.')


    def execute_audio_req(self, audio_bytes: bytes, end_seq = False):
        """提交语音识别分片语音请求
        Args:
            audio_bytes:  音频数据
            end_seq:  是否为结束片段

        请求成功响应如下:
        """
        ## 数据压缩
        payload_bytes = gzip.compress(audio_bytes)

        if end_seq:
            audio_only_request = bytearray(generate_last_audio_default_header())
        else:
            audio_only_request = bytearray(generate_audio_default_header())

        audio_only_request.extend((len(payload_bytes)).to_bytes(4, 'big'))  # payload size(4 bytes)
        audio_only_request.extend(payload_bytes)  # payload

        # 转为bytes发送
        audio_only_request = bytes(audio_only_request)

        # 发送 audio-only client request
        self._ws.auto_send(audio_only_request)
        logger.debug('asr audio_only_request send.')


    def get_result(self):
        """获取api响应数据,在提交请求后调用
        Note:
            TODO: 目前识别结果confidence参数只是预留,服务器返回值都是0
        Returns:
            None 
            or 
            开始请求返回结果: data_obj: {'status': '0', 'code': 1000 }   #code 1000成功, 1001失败
            or
            中间片段请求返回结果: data_obj: {'status': '0', 'code': 1000 } 
            or 
            语音识别结果返回
            data_obj: {
                'status':参数列表如下:
                        'DISCONENCT'  服务器已断开  
                        'CONENCTED'  服务器已连接
                        'REQ_OK' 请求成功  
                        'VOICE_PART' 部分语音检测到
                        'VOICE_ALL' 全部语音检测完成
                        'VOICE_NOT' 未检测到语音 
                        'VOICE_NOT_CLEAR' 语音不清晰
                'result': { 'text': '识别结果', 'confidence': '置信度,保留字段,暂时为0'  }
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
            msg = parse_response(res['msg'])
            msg = msg['payload_msg']
            code = msg['code']
            if code == 1000: # 请求成功
                result['status'] = "REQ_OK"
                if 'result' in msg:  # 包含语音
                    result['seq'] = msg['sequence']
                    if result['seq'] < 0:
                        result['status'] = "VOICE_ALL"
                    else:
                        result['status'] = "VOICE_PART"
                    result['result'] = msg['result']
            elif code == 1013: # 未检出到语音
                result['status'] = "VOICE_NOT"
            elif code == 1001: # 请求出错
                logger.warning('request fail!')
            else:
                logger.warning('request error, code: {}'.format(code))
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

