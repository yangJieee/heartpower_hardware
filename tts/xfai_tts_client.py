#coding=utf-8
# import os
from time import sleep
import json
import json

from urllib.parse import urlencode
import hashlib
import base64
import hmac
from datetime import datetime
from wsgiref.handlers import format_date_time
from time import mktime

import threading

## logger模块
from utility.mlogging import logger

from common.ws_client import WsClient
from common.ws_enum_types import WsEnumTypes

#from audio.audio_creator import AudioCreator

# STATUS_FIRST_FRAME = 0  # 第一帧的标识(实测无)
STATUS_CONTINUE_FRAME = 1  # 第一帧数,中间帧标识
STATUS_LAST_FRAME = 2  # 最后一帧的标识

## 音频处理
#audio_creator = AudioCreator(samplerate=16000)
#SLIENCE_MP3 = audio_creator.get_slience_audio("mp3", 900)


def parse_response(res):
    """解码tts响应数据
    Args:
        res: 原始响应数据
    Returns:
        None or 解码到的数据
        { 'status': 状态标志位: 0表示开始 1中间数据 2合成结束, -1合成失败
        #   'seq_num':,
          'seq_size':, 
          'data':
        }
    """
    # {"code":0,"message":"success","sid":"tts000dda37@gz19082e5ea5446c9902","data":{"audio":""} }
    result = {}
    try:
        message =json.loads(res)
        code = message["code"]
        sid = message["sid"]
        audio_base64 = message["data"]["audio"]
        audio_bytes = base64.b64decode(audio_base64)
        status = message["data"]["status"]
        # print(status)

        if status == STATUS_LAST_FRAME:
            result['status'] = 2
            audio_bytes = bytearray(audio_bytes)
            audio_bytes = bytes(audio_bytes)

        elif status == STATUS_CONTINUE_FRAME:
            result['status'] = 1

        if code != 0:
            errMsg = message["message"]
            logger.warning("sid: %s call error: %s code is: %s" % (sid, errMsg, code))
            result['status'] = -1
        else:
            result['seq_size'] = len(audio_bytes)
            result['data'] = audio_bytes
        return result

    except Exception as e:
        logger.error("receive msg,but parse exception:", e)
        result['status'] = -1
        return result


# 合成小语种需要传输小语种文本、使用小语种发音人vcn、tte=unicode以及修改文本编码方式
# 错误码链接：https://www.xfyun.cn/document/error-code （code返回错误码时必看）
class XFAiTTSClient():
    """科大讯飞语音合成, websocket接口
    """
    def __init__(self, appid, api_secret, api_key, config: dict):
        """
        Args:
            appid:      app id
            api_secret: api secret
            api_key:    api key
            config:  tts配置参数
        """
        self.config = config
        self.audio_config = config['common']['audio']
        self.xfai_tts_config = config['xfai']

        self.api_url = self.xfai_tts_config['ws_url']
        self.silence_duration = self.xfai_tts_config['silence_duration']
        self.voice_type = self.xfai_tts_config['voice_type']

        self.appid = appid
        self.api_secret = api_secret
        self.api_key = api_key
        # self.operation_type = 'query'

        # 公共参数(common)
        self.common_args = {"app_id": self.appid}

        # 业务参数(business)，更多个性化参数可在官网查看

        # 请求合成文本
        #self.request_data = {"status": 2, "text": str(base64.b64encode(self.Text.encode('utf-8')), "UTF8")}
        #使用小语种须使用以下方式，此处的unicode指的是 utf16小端的编码方式，即"UTF-16LE"”
        #self.Data = {"status": 2, "text": str(base64.b64encode(self.Text.encode('utf-16')), "UTF8")}

        # self.default_header = bytearray(b'\x11\x10\x11\x00')
        # self.ws = create_connection(self.api_url, header=ws_header, timeout=600)
        # header = {"Authorization": f"Bearer; {self.token}"}
        # request = HTTPRequest(url=self.api_url, headers=header)

        request_url = self._create_request_url()
        self._ws = WsClient(request_url)

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


    def _create_business_args(self): 
        """创建合成参数
        """
        auf = "audio/L16;rate=16000"
        if self.audio_config['samplerate'] != 16000:
            logger.error('invalid samplerate: {}, use default'.format(16000))
        
        aue = "raw"
        if self.audio_config['codec'] == "mp3":
            aue = "lame"

        business_args = {
            "aue": aue, 
            "auf": auf,
            "sfl": 1,   # 开启流式返回
            "vcn": "xiaoyan123", 
            # "vcn": "aisjiuxu", 
            # "vcn": "Rania", 
            # "tte": "utf8",
            "tte": "UNICODE",
        }
        return business_args


    def _create_request_url(self):
        """生成请求url
        """
        url = self.api_url

        # 生成RFC1123格式的时间戳
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))

        # 拼接字符串
        signature_origin = "host: " + "ws-api.xfyun.cn" + "\n"
        signature_origin += "date: " + date + "\n"
        signature_origin += "GET " + "/v2/tts " + "HTTP/1.1"
        # 进行hmac-sha256进行加密
        signature_sha = hmac.new(self.api_secret.encode('utf-8'), signature_origin.encode('utf-8'),
                                 digestmod=hashlib.sha256).digest()
        signature_sha = base64.b64encode(signature_sha).decode(encoding='utf-8')

        authorization_origin = "api_key=\"%s\", algorithm=\"%s\", headers=\"%s\", signature=\"%s\"" % (
            self.api_key, "hmac-sha256", "host date request-line", signature_sha)
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')
        # 将请求的鉴权参数组合为字典
        obj = {
            "authorization": authorization,
            "date": date,
            "host": "ws-api.xfyun.cn"
        }
        # 拼接鉴权参数，生成url
        url = url + '?' + urlencode(obj)
        # 此处打印出建立连接时候的url,参考本demo的时候可取消上方打印的注释，比对相同参数时生成的url与自己代码生成的url是否一致
        # print('websocket url :', url)
        return url

    
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
        ## 请求合成的文本
        # request_data = {"status": 2, "text": str(base64.b64encode(text.encode('utf-8')), "UTF8")}
        # 兼容小语种
        request_data = {"status": 2, "text": str(base64.b64encode(text.encode('utf-16')), "UTF8")}
        print(request_data)

        obj = {
            "common": self.common_args,
            "business": self._create_business_args(),
            "data": request_data,
        }
        obj_str = json.dumps(obj)
        self._ws.auto_send(obj_str)
        logger.debug('auto send full request: {}'.format(obj_str))


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
            # print(msg)
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
