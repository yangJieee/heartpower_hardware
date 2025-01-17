# 配置文件说明
## LLM参数修改说明
大模型对应配置文件是: config_chat.json
```
    "chat":{
        "common":{
            "message_windows_size": 8,      // 短期记忆窗口数值，越大记忆的聊天数据越多，消耗的token越多
            "response_segment":{
                "min": 10,                  // 分句最小数值
                "max": 100                  // 分句最大数值
            }
        },
        "service": "openai",
        "openai":{
            "base_url": "https://api.openai-hk.com/v1/",
            "model": "gpt-3.5-turbo",       // 要选择的模型
            "temperature": 0.5,             // 模型热度值，越大回答随机性越高       
            "prompt": "从现在起你是一个调皮有个性的川妹子,请用网络语言和我进行交流,禁止回复表情,回答字数尽量少于100字"
        },
        "dashscope": {
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "model": "qwen-turbo",
            "temperature": 0.7,
            "prompt": "从现在起你是一个充满智慧早教老师,你教育的对象是3-8岁的小朋友;请用小朋友能听懂的语言进行交流,引导帮助小朋友学习,回答字数尽量少于100字"
        } 
    }

```
### 当前支持的service
    * openai
    * dashscope(阿里灵积大模型)

### openai 
```
openai: {
    //可选AI模型如下
    "model": "gpt-4o",
    "model": "gpt-3.5-turbo",
    "model": "gpt-3.5-turbo-1106",
    //模型热度参数设置，范围0-1,较高的温度会导致更富有创造性
    "temperature": 0.5
    "prompt": "请你充语音助手, 性格是聪慧且自信的"
    "prompt": "请你充当模拟语音助手, 性格是聪慧且自信的，回答尽可能简练口语化，禁止出现特殊符号, 如提问: 1+1=多少，应该答: 1加1等于2; 字数适当控制在50字以下,明确要求除外"
}
```

### dashscope(阿里灵积大模型)

```
dashscope:{
    // 可选模型
    "model": "qwen-turbo",
    // 其它模型官网查看，兼容openai sdk即可
    ...
}
```


## TTS参数修改说明

### 火山引擎volc TTS

##### 相关参数说明

* 支持格式: wav / pcm / ogg_opus / mp3，默认为 pcm
* compression_rate	opus格式时编码压缩比	2	int		[1, 20]，默认为 1 
    <!-- "compression_rate": 10 -->
    目前测试compression_rate 参数无效,不传递
    api默认压缩率mp3比opus较高
    {"index": 6, "id": "BV424_streaming" , "name":"广东女仔", "example_text": "今日天气真系好好呀！我地一齐去食翻啲嘢。"},

