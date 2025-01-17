# coding=utf-8

# import sys
# import math
import time
from datetime import datetime,timedelta

"""brief
Args:
Returns:
Raises:
"""

def get_ms_ts_str():
  """获取北京时间ms级格式化时间字符串
  Args:
  Returns:  格式化时间字符串
  Raises:
  """
  time_beijing = datetime.utcnow() + timedelta(hours=8)
  ms_ts_str = time_beijing.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
  return ms_ts_str


def in_time_period(start_time: str, end_time: str) -> bool:
  """判断某一时刻是否在某一时间段内,精确到S
  Args:
    1. start_time  开始时间字符串,如"11:10:09"
    1. end_time  结束时间字符串,如"11:10:09"
  Returns: True or False
  Raises:
  """
  # 当前时间
  now_localtime = time.strftime("%H:%M:%S", time.localtime())
  print(now_localtime)
  if start_time <= now_localtime <= end_time:
    return True
  else:
    return False

