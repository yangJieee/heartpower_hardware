# AiLinker

**请点击上方的README.md文件查看具体文档**

## 简介
### 1.1 系统特点

* 该系统基于python3.8开发，大模型以及后端语音服务对接解耦设计。
* 该系统节点间通信基于rabbitmq通信框架.
* 该系统通过websockets和硬件对接，实现AI聊天机器人、AI硬件控制终端等应用。
* 该系统旨在帮助初学者学习在线大模型服务、各语音服务api调用流程，以及和硬件对接流程。

### 1.2 目录架构
* common     # 通用包目录
* configs    #节点配置文件目录
* scripts    #相关测试脚本目录
* deploy     #应用部署和后台运行文件目录
* docs       #相关说明文档
* README.md  

## 2.软件安装
### 2.1 系统软件安装
&nbsp;&nbsp;软件运行在Linux系统，我们的测试系统环境为ubuntu22.04,建议初学者使用相同版本, <br>
其它Linux发行版也可参考本文档安装相关依赖。

#### 1安装rabbitmq server

```
$ sudo apt install rabbitmq-server
```

#### 2配置rabbitmq服务:
```
$ sudo rabbitmqctl add_user user 123456
$ sudo rabbitmqctl set_permissions -p / user ".*" ".*" ".*"
$ sudo rabbitmqctl set_user_tags user administrator
```

#### 3安装其它依赖软件
```
$ sudo apt install libopus-dev
```

### 2.2 安装AILINKER

#### 1安装python虚拟环境管理工具，建议使用miniconda或者conda
* [miniconda安装参考1(中文)](https://www.cnblogs.com/jijunhao/p/17235904.html)
* [conda安装参考2](https://conda.io/projects/conda/en/latest/user-guide/install/index.html)

#### 2安装Ailinker后端服务

首先确保conda虚拟环境管理工具已经正确安装

```
$ git clone https://gitee.com/yumoutech/ailinker.git
$ cd ailinker
$ ./install.sh
```

## 3.运行

### 3.1运行服务前的准备工作

&nbsp;&nbsp;由于大模型接口,语音识别接口,语音合成接口都是用的在线服务接口，这里需要大家先去各家官网申请API KEY(具体申请方法查看docs目录下的文档)，<br>
并将获取到的相关信息，写入 env_setup.bash 文件方可正常运行。若没有该文件可以从docs目录下复制一份出来,运行以下命令。

```
# 确认当前在 ailinker 目录下
$ cp docs/example_env_setup.bash env_setup.bash
```

​系统默认使用的是 openai-hk 的大模型接口，和火山引擎的语音服务，建议大家先申请这两个进行测试。具体申请办法，查看docs目录下的介绍文档或者点击下方链接：

1. [openai-hk大模型api key申请](https://gitee.com/yumoutech/ailinker/blob/master/docs/%E5%A4%A7%E6%A8%A1%E5%9E%8Bapikey%E7%94%B3%E8%AF%B7%E8%AF%B4%E6%98%8E(openai-hk)%E4%B8%AD%E8%BD%AC%E5%B9%B3%E5%8F%B0.md)
2. [火山引擎语音服务api key申请](https://gitee.com/yumoutech/ailinker/blob/master/docs/%E7%81%AB%E5%B1%B1%E5%BC%95%E6%93%8E%E8%AF%AD%E9%9F%B3%E6%9C%8D%E5%8A%A1apikey%E7%94%B3%E8%AF%B7%E8%AF%B4%E6%98%8E.md)


### 3.2运行rabbitmq服务

理论上安装完rabbitmq服务，系统会自动启动，这里我们看一下状态，确保rabbitmq服务器已经启动

```
$ sudo service rabbitmq-server status
```

输入如下，看到(running)即可

```
[sudo] password for deakin:
● rabbitmq-server.service - RabbitMQ Messaging Server
     Loaded: loaded (/lib/systemd/system/rabbitmq-server.service; enabled; vendor preset: enabled)
     Active: active (running) since Thu 2024-08-29 13:34:59 CST; 7h ago
   Main PID: 835 (beam.smp)
      Tasks: 27 (limit: 7084)
     Memory: 142.1M
        CPU: 35min 44.735s
     CGroup: /system.slice/rabbitmq-server.service
             ├─ 835 /usr/lib/erlang/erts-12.2.1/bin/beam.smp -W w -MBas ageffcbf -MHas ageffcbf -MBlmbcs 512 -MHlmbcs 512 -MMmcs 30 -P 1048576 -t 5000000 -stbt db -zdbbl 12800>
             ├─ 943 erl_child_setup 65536
             ├─1706 inet_gethost 4
             └─1707 inet_gethost 4

8月 29 13:34:56 ubuntu22-VirtualBox systemd[1]: Starting RabbitMQ Messaging Server...
8月 29 13:34:59 ubuntu22-VirtualBox systemd[1]: Started RabbitMQ Messaging Server.
```

若服务未启动，运行以下命令启动即可

```
$ sudo service rabbitmq-server start
```

### 3.3在前台运行ailinker服务

```
$ conda activate ailinker
$ source env_setup.bash
$ python app.py
```

1.后端服务启动后可以先用电脑浏览器进行访问，能正常访问会返回以下页面。

![Alt text](./pics/后端部署成功返回01.png)


2.此时如果已经配置好板子的IP和端口信息，重启板子就会看到板子自动连接到服务，连接成功后，板子LED为紫灯闪烁, 此时可以尝试唤醒设备开始聊天。


### 3.4在后台运行ailinker服务(注意设备可以聊天前，不要在后台启动)
前期测试的时候，可以先在前台启动服务，方便看调试信息输出，测试没问题后，可以进入deploy目录运行启动脚本在后台启动服务。具体操作如下

```
$ cd deploy
$ ./run_app.sh  # 运行后回车结束即可 
```

查看后端运行是否正常
后台运行后可以打开该目录下的log文件，查看输出是否正常。

```
$ cat app.log
```

输出如下即可:
```
2024-08-29 20:43:20,095-app-INFO: main app start...
 * Serving Flask app 'app'
 * Debug mode: off
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:8090
 * Running on http://192.168.3.105:8090
Press CTRL+C to quit
```

## 4.目前支持的服务

### 大模型服务

当前大模型只支持openai SDK兼容的服务，但部分厂商兼容性一般，使用过程中可能不稳定。

| LLM服务                | 是否支持 | 兼容性 | 运行效果                                                   | 模型效果               | 使用成本 |
| ---------------------- | -------- | ------ | ---------------------------------------------------------- | ---------------------- | -------- |
| **openai中转平台**     |          |        |                                                            |                        |          |
| gpt-4o                 | 是       | 好     | 较为稳定，响应速度取决于网络情况和中转服务商提供的服务质量 | 效果较好，建议使用     | 较高     |
| gpt-3.5-turbo          | 是       | 好     | 较为稳定，响应速度取决于网络情况和中转服务商提供的服务质量 | 效果一般               | 较低     |
| 其它gpt模型            | 是       | 好     | /                                                          | /                      | /        |
|                        |          |        |                                                            |                        |          |
| **阿里灵积大模型**     |          |        |                                                            |                        |          |
| 通义千问               | 是       | 一般   | 稳定性一般，响应速度较快                                   | 理解能力和逻辑处理一般 | 较低     |
| 其它兼容open sdk的模型 | 是       | 一般   | /                                                          | /                      | /        |
|                        |          |        |                                                            |                        |          |
| **智谱AI**             | 加入中   |        |                                                            |                        |          |
|                        |          |        |                                                            |                        |          |
| **豆包大模型**         | 加入中   |        |                                                            |                        |          |
|                        |          |        |                                                            |                        |          |

### 语音服务

| 语音服务         | 是否支持 | 运行效果                             | 使用效果                       | 使用成本              |
| ---------------- | -------- | ------------------------------------ | ------------------------------ | --------------------- |
| **火山引擎**     |          |                                      |                                |                       |
| 火山引擎语音识别 | 是       | 相对稳定，偶尔响应较慢，少数情况断连 | 识别效果一般，同音字词处理不好 | 较低，20000次免费额度 |
| 火山引擎语音合成 | 是       | 相对稳定，偶尔响应较慢，少数情况断连 | 合成效果较好                   | 较低，20000次免费额度 |
| **讯飞AI**       |          |                                      |                                |                       |
| 讯飞语音识别     | 测试中   |                                      |                                |                       |
| 讯飞语音合成     | 测试中   |                                      |                                |                       |

## 常见问题解答(FAQ)
[参考FAQ文档](./docs/FAQ.md)   

## 版本更新
### v0.3.01
* 更新了asr单次请求数据大小

### v0.3.02
* 修改了asr节点配置文件，默认不保存音频

### v0.3.10
* 更新README

### v0.3.11(dev)
* 更新队列缓存区大小
* 更新控制数据发送频率
