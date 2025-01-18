## openAI接口应用，教程地址
# https://cookbook.openai.com/examples/how_to_format_inputs_to_chatgpt_models

import os
from openai import OpenAI

from utility.mlogging import logger
from common.sentence_segmenter import SentenceSegmenter


class OpenAIChat():
    """openAI chatGPT 对话
    """
    def __init__(self, config: dict) -> None:
        """
        Args:
            config chat配置信息
        """
        self.config = config
        # 选择模型服务商(需要兼容openai的sdk才行)
        service = self.config['service']
        gpt_config = self.config[service]
        common_config = self.config['common']

        base_url = gpt_config['base_url']
        logger.info(base_url)

        api_key = None

        if service == 'openai':
            api_key=os.environ.get("OPENAI_API_KEY", None)
        elif service == 'dashscope':
            api_key=os.environ.get("DASHSCOPE_API_KEY", None)
        else:
            logger.error('service: {} , no support.'.format(service))
            exit(1)

        if api_key is None:
            logger.error('get api_key from env fial!')
            exit(1)
        logger.debug(api_key)


        # 创建gpt客户端
        self.client = OpenAI(api_key=api_key, base_url=base_url)

        # 模型选择
        self.model = gpt_config['model']
        logger.info('gpt model: {}'.format(self.model))

        # 模型热度参数设置，范围0-1, 低热度回答稳定，高热度富有创造性
        self.temperature = gpt_config['temperature']

        self.prompt_content = gpt_config['prompt']
        self.prompt = self.prompt_defalut(self.prompt_content)

        self.chat_messages = []
        # 消息条数最大值(不含prompt)
        self.chat_messages_windows_size_max = common_config['message_windows_size'] 

        self.full_answer = ""
        self.answer_seq = 0
        self.segmenter = SentenceSegmenter(common_config['response_segment']['min'], common_config['response_segment']['max'])


    def prompt_assistant(self):
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Knock knock."},
            {"role": "assistant", "content": "Who's there?"},
            {"role": "user", "content": "Orange."},
        ]
        return messages


    def prompt_defalut(self, prompt_content):
        messages = [
            {"role": "user", "content": prompt_content},
        ]
        return messages


    def get_messages(self):
        """获取完整消息,用于请求
        """
        messages = [] 
        messages.extend(self.prompt)
        messages.extend(self.chat_messages)
        # print(f"chat message: {self.chat_messages}")
        return messages


    def update_chat_messages(self, role: str, content: str):
        """跟新对话消息
        """
        msg = {"role": role, "content": content}
        self.chat_messages.append(msg)
        if len(self.chat_messages) > self.chat_messages_windows_size_max:
            self.chat_messages = self.chat_messages[-self.chat_messages_windows_size_max : ]


    def chat(self, text: str):
        """执行一次对话
        """
        self.update_chat_messages('user', text)
        # a ChatCompletion request
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.get_messages(),
            temperature=self.temperature,
            stream=True,
            stream_options={"include_usage": True}, # retrieving token usage for stream response
        )

        full_answer = ""
        for chunk in response:
            print(chunk)
            choices = chunk.choices
            if len(choices) != 0:
                chunk_message = chunk.choices[0].delta.content  # extract the message
                if chunk_message is not None:
                    full_answer += chunk_message
                    print(chunk_message)
        # print('assistant:', full_answer)
        ## 保存回答
        self.update_chat_messages('assistant', full_answer)
        return full_answer


    def get_response(self, text: str):
        """执行一次对话请求,非流式返回
        Args:
            text  当前用户输入信息
        Returns:
            reponse  返回响应数据
            {'seq': 'text': } 回答句子序列和文本 seq取值-1
        """
        ## 更新当前聊天数据
        self.update_chat_messages('user', text)
        # a ChatCompletion request
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.get_messages(),
            temperature=self.temperature,
            stream=False,
        )
        result = {}
        result['seq'] = -1
        completionMessage = response.choices[0].message
        # print(completionMessage.content)
        result['text'] = completionMessage.content
        return result


    def get_response_stream(self, text: str):
        """执行一次对话请求,流式返回
        Args:
            text  当前用户输入信息
        Returns:
            reponse  返回流式响应数据，由多个chunk组成
        """
        ## 更新当前聊天数据
        self.update_chat_messages('user', text)
        # a ChatCompletion request
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.get_messages(),
            temperature=self.temperature,
            stream=True,
            stream_options={"include_usage": True}, # retrieving token usage for stream response
        )
        return response


    def decode_chunk(self, chunk):
        """解码对话流式响应数据,分句返回回答结果
        Args:
            chunk   流式响应response的元素
        Note:
            openai 和 dashscope 数据返回有所区别, openai最后一条消息为None
        Returns:
            None(未就绪) or {'seq': 'text': } 回答句子序列和文本 seq取值[0,1,2,3...-n] 0 代表开始, seq=-n 代表尾句
        """
        result = {}
        answer = None
        # finish_reason='stop'
        choices = chunk.choices
        if len(choices) != 0:
            msg = chunk.choices[0].delta.content  # extract the message
            finish_reason = chunk.choices[0].finish_reason

            if msg == '':  # 开始  
                self.answer_seq = 0

            # get answer
            if finish_reason == 'stop':
                if msg is not None:
                    answer = self.segmenter.flush(text=msg)
                else: 
                    answer = self.segmenter.flush()
                self.full_answer = ""
            else:
                if msg is not None and msg != '': # 中间数据
                    self.full_answer += msg
                    answer = self.segmenter.update(msg)

            if answer != None:
                self.answer_seq = self.answer_seq + 1
                if finish_reason:
                    self.answer_seq = -1 * self.answer_seq
                ## 保存回答到chat messages
                self.update_chat_messages('assistant', self.full_answer)
        logger.debug('answer:{}'.format(answer))

        if answer == None:
            return None
        result['seq'] = self.answer_seq
        result['text'] = answer
        return result
