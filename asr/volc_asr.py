#coding=utf-8
import os

from asr.volc_asr_client import VolcAsrClient

from utility.mlogging import logger

class VolcASR(VolcAsrClient):
    def __init__(self, config: dict):
        """
        Args:
            config: asr配置参数
        """
        self.config = config
        volc_config = config['volc']
        common_config = config['common']

        appid=os.environ.get("VOLC_ASR_APP_ID", None)
        if appid is None:
            logger.error('get app id from env fail.')
            exit(1)

        token=os.environ.get("VOLC_ASR_ASSEST_TOKEN", None)
        if token is None:
            logger.error('get assest token from env fail.')
            exit(1)

        cluster=os.environ.get("VOLC_ASR_API_CLUSTER", None)
        if cluster is None:
            logger.error('get cluster from env fail.')
            exit(1)

        super().__init__(
            appid=appid,
            token=token,
            cluster=cluster,
            ws_url=volc_config['ws_url'],
            samplerate = common_config['audio']['samplerate'],
            channels = common_config['audio']['channels'],
            sampwidth = common_config['audio']['sampwidth'],
            codec = common_config['audio']['codec']
        )

        logger.info('asr client initialize.')
