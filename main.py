#!/usr/bin/python
# -*- coding: utf-8 -*-

from interface.connection import excel, logg, deviceControl, deviceControl_auto
from interface.statusCheck import pingCheck
from interface.tipsFunctions import netSplit, listReset
import time, re, sys
import concurrent.futures
import threading
import vthread


def runStart(args_ments):
    username = args_ments[1]
    password = args_ments[2]
    ip = args_ments[0]
    try:
        cmds = args_ments[3].split(',')
    except:
        cmds = [args_ments[3]]
    print(cmds)
    res = [ip]  # 结果集
    logIN = deviceControl_auto(ip, username, password)
    try:
        result = logIN.auto_login(cmds)
        res.extend(result)
    except Exception as e:
        res.extend(['%s' % e])
    Rlock.acquire()
    print('%s 执行完成' % (ip))
    Rlock.release()
    return res


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
    global Rlock  # 定义线程锁
    Rlock = threading.RLock()
    hostname = 'IP.xlsx'
    excel_obj = excel(hostname)
    read_excel = excel_obj.excel_read(sheetnum=1)
    cc_list = read_excel
    result = []  # 多线程执行后的结果
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as exector:
        future_list = []
        for cc in cc_list:
            # 使用submit提交执行的函数到线程池中，并返回futer对象（非阻塞）
            future = exector.submit(runStart, cc)
            future_list.append(future)
            # print(cc, future)
        # as_completed方法传入一个Future迭代器，然后在Future对象运行结束之后yield Future
        for future in concurrent.futures.as_completed(future_list):
            # 通过result()方法获取结果
            res = future.result()
            # print(res, future)
            result.append(res)
    excel_w = excel('result')
    excel_w.excel_write(title=['IP', '执行结果'], data=result)
    excel_w.save_file()


def VlanifConfig(file):  # 构造vlanif配置
    excel_obj = excel(file)
    read_excel = excel_obj.excel_read(sheetnum=2)
    result = ''
    for row in read_excel:
        match_row = str(row[1])
        matchStr = re.search('vlan', match_row, re.I)
        if matchStr:
            vlanID = re.findall('\d+', match_row)[0]
            VlanifInfo = '\ninterface Vlanif%s\n' % (vlanID)
            for index, cellInfo in enumerate(row[2:]):  # 从第三列开始循环
                if bool(cellInfo) == False:
                    continue
                cellSplit = str(cellInfo).split('/')
                network = cellSplit[0].split('.')
                network[-1] = str(int(network[-1]) + 1)
                networStr = '.'.join(network)
                if index == 0:
                    VlanifInfo += 'ip address %s %s\n' % (networStr, cellSplit[1])
                else:
                    VlanifInfo += 'ip address %s %s sub\n' % (networStr, cellSplit[1])
            result += VlanifInfo
    timeNow = time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))
    with open('config%s.txt' % timeNow, 'w') as file_w:
        file_w.write(result)


def VlanifConfigTemp(file):  # 构造vlanif配置 临时代码
    excel_obj = excel(file)
    read_excel = excel_obj.excel_read(sheetnum=2)
    result = ''
    for row in read_excel:
        match_row = str(row[1])
        matchStr = re.search('vlan', match_row, re.I)
        if matchStr:
            vlanID = re.findall('\d+', match_row)[0]
            VlanifInfo = '\ninterface Vlanif%s\n dhcp select relay \n dhcp relay server-ip 154.92.99.252\n' % (vlanID)
            result += VlanifInfo
    timeNow = time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))
    with open('config%s.txt' % timeNow, 'w') as file_w:
        file_w.write(result)


def splitNetworkWriteToExcel():  # 网段划分
    net = '192.168.192.0'
    mask = 18
    sub_mask1 = 24  # 子网的子网掩码
    sub_mask2 = 27  # 子网小段子网掩码
    count_sub = 8  # 分组
    subnetList = netSplit(net, mask, sub_mask1)
    subnetList = listReset(subnetList)
    excel_list = []  # 划分之后的子网段集
    for cell in subnetList:
        excel_list.append([cell])
    # print(excel_list)
    excel_obj = excel('IP地址大段')
    excel_obj.excel_write(title=['%s/%d' % (net, mask)], data=excel_list)
    savename = excel_obj.save_file()

    '''小网段24to27段排列'''
    result_subList = []
    excel_obj = excel(savename)
    read_excel = excel_obj.excel_read(sheetnum=1)
    for cell_sub in read_excel:
        withoutMaskSplit = cell_sub[0].split('/')
        result_subList.append(netSplit(withoutMaskSplit[0], int(withoutMaskSplit[1]), sub_mask2))

    '''重新排序'''
    num = 0
    result_all = read_excel
    for index, list_cell in enumerate(result_subList):
        temp_cell = list_cell[:num]
        del list_cell[:num]
        list_cell.extend(temp_cell)
        num += 1
        if num == count_sub - 1:
            num = 0
        result_all[index].extend(list_cell)
    # print(result_all)
    '''写入excel'''
    excel_w = excel('IP地址细化')
    excel_w.excel_write(title=['%s/%d' % (net, mask)], data=result_all)
    excel_w.save_file()


def getVersion():
    filename = 'IP_list.xlsx'
    excel_obj = excel(filename)
    read_excel = excel_obj.excel_read()
    Bl_ip = '103.233.9.231'
    username = 'xx'
    password = 'xx'
    conn = deviceControl(Bl_ip, username, password, port=2222)
    res = conn.connectLinux()
    print(res)


if __name__ == '__main__':
    threading_action()
