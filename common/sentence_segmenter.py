# coding=utf-8
"""语段断句
"""

class SentenceSegmenter:
    """语段分句输出
    """
    def __init__(self, threshold_min, threshold_max):

        self.threshold_min = threshold_min 
        self.threshold_max = threshold_max 
        self.sentence = ""  # 保存原始句子
        self.current_sentence = ""  # 保存当前句子片段

    def filter(self, sentence: str):
        """去除特殊符号
        """
        print(sentence)


    def update(self, text):
        """
        追加字符串到当前句子，并返回最新的断句片段，若没有则返回None。
        """
        self.sentence += text
        if len(self.sentence) > self.threshold_min:
            # 找到最近的标点符号位置
            split_indexs = []
            for i in range(0, len(self.sentence), 1):
                if self.sentence[i] in "。？！,.?":
                    # print('find split:{}'.format(i))
                    split_indexs.append(i)
            ## 断句
            if len(split_indexs) > 0: 
                cut_index = split_indexs[-1]
                # print('cut index: ', cut_index)
                self.current_sentence += self.sentence[:cut_index+1]
                # print('current sentence: ', self.current_sentence)
                self.sentence = self.sentence[cut_index+1:]
                # print('self sentence: ', self.sentence)

        sentence = None
        if len(self.current_sentence) > self.threshold_min: 
            sentence = self.current_sentence
            self.current_sentence = ""

        if len(self.sentence) > self.threshold_max:
            sentence = self.sentence
            self.current_sentence = ""
            self.sentence = ""

        # sentence = self.filter(sentence)
        return sentence


    def flush(self, text=''):
        """清空输出,用在句子结束时
        Args:
            text: 清空时附带输入的字串
        """
        sentence = ""
        if self.current_sentence != '':  # 当前断句可能未输出
            sentence += self.current_sentence

        sentence += self.sentence 
        sentence += text
        # 清空本轮数据
        self.current_sentence = ""
        self.sentence = ""
        # sentence = self.filter(sentence)
        return sentence
        

if __name__=='__main__':

    # 使用示例
    text0 = "有一个小男孩叫小明，他非常喜欢探险。一天，他决定去探索森林深处。在那里，他发现了一个神秘的洞穴。小明充满好奇，毫不犹豫地走了进去。洞穴里面有很多宝藏和神奇的生物。小明非常兴奋，但也有些害怕。最后，他成功带着宝藏回到家，成为了小英雄。从那以后，小明变得更加勇敢，也更加喜欢探险了。"
    # text1 = "1加1等于2 。 有其他问题吗 ？"
    text2 = "1加1=2,有其他问题吗 ？"
    text3 = "我是个聪明自信的AI，擅长 快速解答问题，帮你提供简洁明了的答案。"

    text = text3

    segmenter = SentenceSegmenter(10, 100)
    for t in text[0:-1]:
        s = segmenter.update(t)
        if s is not None:
            print(s)  # 输出最新的断句片段
    print(segmenter.flush(text[-1]))  # 输出最新的断句片段

