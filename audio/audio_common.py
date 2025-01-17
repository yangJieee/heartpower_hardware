# coding=utf-8
"""音频处理通用功能
"""
from typing import Union
import wave
import array
import struct
from utility.mlogging import logger


def readWav(file_path: str):
    """
    打开 WAV 文件,并读取相应的数据
    Args:
        file_path: wav文件路径
    Returns:
        frames bytes, samplerate, channels, sampwidth
    """
    ret = {}
    frames = None
    samplerate = 0
    channels = 0
    sampwidth = 0
    with wave.open(file_path, 'rb') as wav_file:
        channels =  wav_file.getnchannels()
        # 确保是单声道
        # if wav_file.getnchannels() != channels:
            # raise ValueError('only channels:[%d] audio is supported' % channels)
        samplerate =  wav_file.getframerate()
        sampwidth =  wav_file.getsampwidth()

        # 确保是 16 位采样
        if sampwidth != 2:
            raise ValueError('Only 16-bit audio is supported')
        # 读取所有的采样数据,bytes object
        frames = wav_file.readframes(wav_file.getnframes())
        # print(type(frames))
    ret['frames'] = frames
    ret['samplerate'] = samplerate
    ret['sampwidth'] = sampwidth
    ret['channels'] = channels
    return ret


def pcmBytesToList(pcm_bytes: bytes) -> list:
    """将二进制字节数据转换为 PCM 格式的列表
    Args:
        pcm_bytes PCM二进制数据
    Returns:
        pcm_data list
    """
    pcm_data = array.array('h', pcm_bytes)
    return list(pcm_data)


def listToPcmBytes(pcm_data: list) -> bytes:
    """将 PCM 格式的列表转换为二进制字节数据
    Args:
        pcm_data PCM格式的列表
    Returns:
        pcm_bytes bytes
    """
    pcm_array = array.array('h', pcm_data)
    return pcm_array.tobytes()


def saveWav(file_path, audio_data: Union[list, bytes], samplerate: int, channels=1, sampwidth=2):
    """写入PCM音频数据到.wav文件
    Args:
        file_path  文件路径
        audio_data    音频采样数据，16位有符号整数列表或者bytes
        samplerate    采样率
        channels      音频通道数, 默认:1
        sampwidth     音频数据位宽 默认:2--16bit
    """
    samples = []
    if isinstance(audio_data, list):
        samples = audio_data
    elif isinstance(audio_data, bytes):
        samples = pcmBytesToList(audio_data)
    else:
        logger.error('invalid audio data.')
        return  
    samples_number = len(samples)
    save_samples = []
    ## 确保数据转成16位有符号整型
    for sample in samples:
        save_samples.append(struct.pack('<h', sample))

    with wave.open(file_path, 'w') as wave_file:
        logger.debug('save wav audio to: {}'.format(file_path))
        wave_file.setparams((channels, sampwidth, int(samplerate), samples_number, 'NONE', 'not compressed'))
        wave_file.writeframes(b''.join(save_samples))
        wave_file.close()

