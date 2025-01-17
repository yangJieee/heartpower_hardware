from pydub import AudioSegment
from io import BytesIO


class AudioCreator():
    """音频创建
    """
    def __init__(self, samplerate = 16000):
        """
        Args:
            samplerate:  采样率
        """
        self.samplerate = samplerate

    def get_slience_audio(self, format: str, time_long: int):
        """生产静音音频片段
        Args:
            format 音频格式 raw or mp3
            time_long 时长
        """
        audio = AudioSegment.silent(duration=time_long, frame_rate=self.samplerate)
        # 将音频数据存储为字节缓冲
        if format == 'raw':
            raw_bytes = audio.raw_data
            return raw_bytes
        elif format == 'mp3':
            # 将音频数据导出为MP3格式并保存在内存中的缓冲区
            output_buffer = BytesIO()
            audio.export(output_buffer, format="mp3")
            # 读取BytesIO对象中的数据
            output_buffer.seek(0)
            mp3_bytes = output_buffer.read()
            return mp3_bytes
