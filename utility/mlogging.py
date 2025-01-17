# coding=utf-8
import logging

class CustomFormatter(logging.Formatter):
  def __init__(self, loc_enable: bool):
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    green = "\x1b[32;20m"
    reset = "\x1b[0m"
    if loc_enable:
      format = "%(asctime)s-%(name)s-%(levelname)s: %(message)s (%(filename)s:%(lineno)d)"
    else:
      format = "%(asctime)s-%(name)s-%(levelname)s: %(message)s"

    self.FORMATS = {
      logging.DEBUG: green + format + reset,
      logging.INFO: grey + format + reset,
      logging.WARNING: yellow + format + reset,
      logging.ERROR: bold_red + format + reset,
      logging.CRITICAL: red + format + reset
    }

  def format(self, record):
    log_fmt = self.FORMATS.get(record.levelno)
    formatter = logging.Formatter(log_fmt)
    return formatter.format(record)


class MLogger(logging.Logger):
  """logger对象
  Args:
    1. app_name  当前应用名
    2. logging_level  log消息等级,如: logging.DEBUG
    3. loc_enable  是否开启位置指引
  Returns:
  Raises:
  """
  def __init__(self, app_name: str, level: int, loc_enable: bool):
    super().__init__(app_name)
    self.setLevel(level)
    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(CustomFormatter(loc_enable))
    self.addHandler(ch)


DEBUG=logging.DEBUG
INFO=logging.INFO
WARNING=logging.WARNING
ERROR=logging.ERROR
CRITICAL=logging.CRITICAL


# 默认全局logger可直接导入使用
logger = MLogger("root", logging.INFO, False)

# 默认全局logger配置函数，需要在导入logger之前调用
def logger_config(app_name: str, level: int, loc_enable: bool):
  global logger
  logger = MLogger(app_name, level, loc_enable)
