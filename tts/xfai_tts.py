#coding=utf-8
import os
from tts.xfai_tts_client import XFAiTTSClient
from utility.mlogging import logger


class XFaiTTS(XFAiTTSClient):
    """科大讯飞TTS
    """
    def __init__(self, config: dict):
        """
        Args:
            config: tts配置参数
        """
        self.config = config

        api_key=os.environ.get("XFAI_TTS_API_KEY", None)
        if api_key is None:
            logger.error('get api key from env fail.')
            exit(1)
        appid = api_key.split('--')[0]
        api_secret = api_key.split('--')[1]
        api_key = api_key.split('--')[2]

        super().__init__(appid=appid, api_secret=api_secret, api_key=api_key, config=self.config)
        logger.info('tts client initialize.')
