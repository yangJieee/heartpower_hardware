#!/bin/bash

sudo apt install rabbitmq-server  -y

#配置rabbitmq服务:
sudo rabbitmqctl add_user user 123456  
sudo rabbitmqctl set_permissions -p / user ".*" ".*" ".*"
sudo rabbitmqctl set_user_tags user administrator


#安装libopus
sudo apt install  libopus-dev

