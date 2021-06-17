#!/usr/bin/python
# -*- coding: utf-8 -*-

from interface.connection import excel, logg
from interface.statusCheck import pingCheck
import time,re

def runStart(filename):
    filename_local = filename
    excel_obj = excel(filename_local)
    list_ex = excel_obj.excel_read()
    print(list_ex)


def monitor_host(host, interval=5):  # 监控IP并写入日志
    monitor_log = logg(loggername='monitor', filename='monitor')
    while True:
        try:
            delay, loss = pingCheck(host)
        except:
            monitor_log.get_log().error('%s PING执行失败' % host)
        timeNow = time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))
        monitor_log.get_log().info('丢包率:%s 平均时延:%s' % (loss, delay))
        time.sleep(interval)


if __name__ == '__main__':
    # filename = 'xiaoixn.xlsx'
    # runStart(filename)
    host = '192.168.1.254'
    interval = 10
    monitor_host(host, interval)
