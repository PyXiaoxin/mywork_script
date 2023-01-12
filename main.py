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
    password = 'xx11111'
    conn = deviceControl(Bl_ip, username, password, port=2222)
    res = conn.connectLinux()
    print(res)

def funcAction(user, passwd, fileName, logName, func, worker=30):  # 主模块
    global Rlock_local, logger
    with alive_bar(title='Progress', bar='filling', spinner='waves2', unknown='wait', manual=True) as bar:  # 进度条
        init()  # 初始化全局变量
        set_value('logger', logg(logName, 'log/%s' % logName))
        file = fileName  # 读取文件名
        file_dir = 'read/%s' % file
        read = excel(file_dir)
        logger = get_value('logger')
        logger.get_log().info('当前运行环境:%s %s %s' % (platform.system(), platform.version(), platform.machine()))
        bar(0.05)
        try:
            read_info = read.excel_read()
            logger.get_log().info('读取 \'%s\' 成功' % file)
        except Exception as e:
            logger.get_log().error('读取 \'%s\' 失败:%s' % (file, e))
            bar(1)
            return
        bar(0.1)
        arg = [user, passwd]  # 用户密码
        my_poll = autoThreadingPool(worker)
        result = my_poll(func, arg, read_info)
        logger.get_log().info('数据获取全部完成,准备写入本地')
        bar(1)
        return result
    
def writeToExcel(filename, title, data):  # 写入数据到excel
    filename_local = 'data/%s' % filename
    title_local = title
    data_local = data
    write_info = excel(filename_local)
    try:
        write_info.excel_write(title_local, data_local)
        savename = write_info.save_file()
    except Exception as e:
        logger.get_log().error('文件写入失败,%s' % (e, Exception))
        return
    logger.get_log().info('文件 %s 写入完成,保存至data目录下' % (savename))


def writeToTXT(data):  # 写入数据到TXT
    data_local = data
    timeNow = time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))
    try:
        for data_unit in data_local:
            with open('data/%s_%s_%s.log' % (data_unit[0], data_unit[1], timeNow), 'w') as f:
                f.write(data_unit[2])
    except Exception as e:
        logger.get_log().error('文件写入失败,%s %s' % (e, Exception))
        return
    logger.get_log().info('文件写入完成,保存至data目录下')


def platform_select():  # 判断当前运行环境
    username = ''
    password = ''
    if ('Windows' in platform.system()):
        from interface import passwdinput
        username = input('用户:')
        password = passwdinput('密码:')
        while True:
            worker = input('线程数:')
            if int(worker) <= 200 and int(worker) >= 1:
                break
            else:
                print('线程数范围1-200')
    elif ('Linux' in platform.system()):
        import sys
        username, password, worker = sys.argv[1], sys.argv[2], sys.argv[3]
    else:
        print(platform.system(), platform.version(), platform.machine())
        print('当前运行环境不支持')
    return username, password, int(worker)


def start_action():  #入口
    fileName = 'devices_ip.xlsx'
    title = ['IP', 'Description', 'PingStatus(ms)', 'loginWay']  # 保存的sheet标题
    from checkConfig import deviceCheck
    username, password, worker = platform_select()
    data = funcAction(username, password, fileName, savename, deviceCheck, worker)
    writeToExcel(savename, title, data)

if __name__ == '__main__':
    start_action():
