
## CHAT节点 通义千问请求报错

### 问题-报错1
2024-07-13 23:27:10,902-chat-INFO:  1 当然可以，我们先从一数起：一，二，三，四，五，六，七，八，九，十。
2024-07-13 23:27:11,405-chat-INFO: -2 很好，你真棒！接着我们可以数更大的数字，比如十五，二十，这样你的数学就会越来越好哦！
2024-07-13 23:27:40,604-chat-INFO: user: 你可以教我九九乘法口诀表吗？
Traceback (most recent call last):
  File "node_chat.py", line 147, in <module>
    main(config)
  File "node_chat.py", line 128, in main
    chat_node.launch()
  File "node_chat.py", line 121, in launch
    self.handle_mq_msg(mq_msg)
  File "node_chat.py", line 97, in handle_mq_msg
    reponse = self.chat.get_response_stream(text)
  File "/home/deakin/esp/ailinker/chat/openai_chat.py", line 164, in get_response_stream
    response = self.client.chat.completions.create(
  File "/home/deakin/miniconda3/envs/aibot/lib/python3.8/site-packages/openai/_utils/_utils.py", line 277, in wrapper
    return func(*args, **kwargs)
  File "/home/deakin/miniconda3/envs/aibot/lib/python3.8/site-packages/openai/resources/chat/completions.py", line 590, in create
    return self._post(
  File "/home/deakin/miniconda3/envs/aibot/lib/python3.8/site-packages/openai/_base_client.py", line 1240, in post
    return cast(ResponseT, self.request(cast_to, opts, stream=stream, stream_cls=stream_cls))
  File "/home/deakin/miniconda3/envs/aibot/lib/python3.8/site-packages/openai/_base_client.py", line 921, in request
    return self._request(
  File "/home/deakin/miniconda3/envs/aibot/lib/python3.8/site-packages/openai/_base_client.py", line 1005, in _request
    return self._retry_request(
  File "/home/deakin/miniconda3/envs/aibot/lib/python3.8/site-packages/openai/_base_client.py", line 1053, in _retry_request
    return self._request(
  File "/home/deakin/miniconda3/envs/aibot/lib/python3.8/site-packages/openai/_base_client.py", line 1005, in _request
    return self._retry_request(
  File "/home/deakin/miniconda3/envs/aibot/lib/python3.8/site-packages/openai/_base_client.py", line 1053, in _retry_request
    return self._request(
  File "/home/deakin/miniconda3/envs/aibot/lib/python3.8/site-packages/openai/_base_client.py", line 1020, in _request
    raise self._make_status_error_from_response(err.response) from None
openai.RateLimitError: Error code: 429 - {'error': {'message': 'Too many requests in route. Please try again later.', 'type': 'invalid_request_error', 'param': None, 'code': 'rate_limit_error'}}

### 问题-报错2
Traceback (most recent call last):
  File "node_chat.py", line 152, in <module>
    main(config)
  File "node_chat.py", line 133, in main
    chat_node.launch()
  File "node_chat.py", line 126, in launch
    self.handle_mq_msg(mq_msg)
  File "node_chat.py", line 103, in handle_mq_msg
    for chunk in reponse:
  File "/home/deakin/miniconda3/envs/aibot/lib/python3.8/site-packages/openai/_streaming.py", line 46, in __iter__
    for item in self._iterator:
  File "/home/deakin/miniconda3/envs/aibot/lib/python3.8/site-packages/openai/_streaming.py", line 72, in __stream__
    raise APIError(
openai.APIError: Output data may contain inappropriate content.

#### 解决(未处理)
  与openai接口兼容性问题

## TTS取消任务问题
  tts合成开始后进入处理循环，无法有效处理取消信号 

#### 解决(未处理)
  需要进行更新为异步处理,收到取消信号后关闭连接
