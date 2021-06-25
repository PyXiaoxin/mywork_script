#!/usr/bin/python
# -*- coding: utf-8 -*-

from interface.connection import excel, logg
from interface.statusCheck import pingCheck
import time, re, sys
import concurrent.futures
import threading
import vthread


def runStart(filename):
    filename_local = filename
    excel_obj = excel(filename_local)
    list_ex = excel_obj.excel_read()
    print(list_ex)


def monitor_host(host, interval=5):  # 监控IP并写入日志
    # startTime = time.time()
    monitor_log = logg(loggername=host, filename='monitor_%s' % host)
    while True:
        try:
            delay, loss = pingCheck(host)
        except:
            monitor_log.get_log().error('%s PING执行失败' % host)
        timeNow = time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))
        monitor_log.get_log().info('丢包率:%s 平均时延:%sms' % (loss, delay))
        time.sleep(interval)  # 间隔
        # endTime = time.time()
        # allTime = endTime - startTime
        # if allTime >= 10:  # 5分钟结束一次
        #     break


def action(max):  # 测试函数
    my_sum = 0
    for i in range(max):
        print(threading.current_thread().name + '  ' + str(i))
        my_sum += i
    return my_sum


def threading_action():  # 多线程入口
    cc_list = [10, 20]  # 传递的参数
    result = []  # 多线程执行后的结果
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as exector:
        future_list = []
        for cc in cc_list:
            # 使用submit提交执行的函数到线程池中，并返回futer对象（非阻塞）
            future = exector.submit(action, cc)
            future_list.append(future)
            # print(cc, future)
        # as_completed方法传入一个Future迭代器，然后在Future对象运行结束之后yield Future
        for future in concurrent.futures.as_completed(future_list):
            # 通过result()方法获取结果
            res = future.result()
            # print(res, future)
            result.append(res)
    print(result)


if __name__ == '__main__':
    cmd_key = sys.argv
    host = sys.argv[1]
    interval = int(sys.argv[2])
    monitor_host(host, interval)
    # print(time.time())
