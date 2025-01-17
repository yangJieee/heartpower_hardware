# Opus音频解码
import opuslib
import opuslib.api.encoder
import opuslib.api.decoder


class OpusDecoder():
    def __init__(self, samplerate: int, channels: int, seq_time: float) -> None:
        self.samplerate = samplerate
        # 创建解码器
        self.decoder = opuslib.Decoder(fs=self.samplerate, channels=channels)
        self.seq_length = int(seq_time*self.samplerate*2)

    def decode(self, input_bytes: bytes):
        """解码测试
        Args:
            input_bytes:  待解码数据
        Note:
            每次只能解码一个包的数据，否则解码效果不对
        Returns:
            dec_output 解码结果
        """
        # 直接解码opus数据
        dec_output = self.decoder.decode(bytes(input_bytes), self.seq_length)
        # print('decode seq len: {}'.format(len(dec_output))) 
        return dec_output
