# coding=utf-8
"""队列应用
"""
from collections import deque

from utility.mlogging import logger



class Udeque():
    """deque应用封装
    """
    @classmethod
    def write_deque(cls, que: deque, data, max_len=3):
        if len(que) >= max_len:
            logger.warn('queue length[{}] out of range[{}], auto pop data.'.format(len(que), max_len))
            que.popleft()
        que.append(data)


    @classmethod
    def read_deque(cls, que: deque, pop=True):
        res = None
        if len(que) != 0:
            if pop:
                res = que.popleft()
            else:
                res = que[0]
        return res
