#!/usr/bin/python
# -*- coding: utf-8 -*-
# from ping3 import ping, verbose_ping
from pythonping import ping
import re


def pingCheck(host):  # ping 返回平均延迟,丢包
    res = ping(host, count=10, size=64)
    res = str(res)
    timeout = re.findall(r'timed out', res)
    timeoutNum = len(timeout)
    loss = timeoutNum / 10
    delayAvg = re.findall(r'max is\s(\S+)', res)
    delayAvg = delayAvg[0].split('/')[1]
    loss = '%.2f%%' % (loss * 100)
    return delayAvg, loss


def resCheck(data):  # 结果检查，检查通过返回True
    data_local = data
    keyword_local = ['error']
    for key in keyword_local:
        match = re.search(r'%s' % key, data_local, re.I)
        if match:
            return False
    return True


if __name__ == '__main__':
    # ip = '192.168.1.254'
    # pingRes = pingCheck(ip)
    datastr = 'zhiehu1k2312,12313 Error'
    print(resCheck(datastr))
