#coding=utf-8
import os
from tts.volc_tts_client import VolcTTSClient
from utility.mlogging import logger


class VolcTTS(VolcTTSClient):
    """火山引擎TTS
    """
    def __init__(self, config: dict):
        """
        Args:
            config: tts配置参数
        """
        self.config = config

        appid=os.environ.get("VOLC_TTS_APP_ID", None)
        if appid is None:
            logger.error('get app id from env fail.')
            exit(1)

        token=os.environ.get("VOLC_TTS_ASSEST_TOKEN", None)
        if token is None:
            logger.error('get assest token from env fail.')
            exit(1)

        cluster=os.environ.get("VOLC_TTS_API_CLUSTER", None)
        if cluster is None:
            logger.error('get cluster from env fail.')
            exit(1)

        super().__init__(appid=appid, token=token, cluster=cluster, config=self.config)
        logger.info('tts client initialize.')

