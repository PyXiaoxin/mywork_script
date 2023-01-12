#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import re
import socket
from pythonping import ping
import base64


# 函数介绍：
# 1、ping函数 返回延迟以及丢包率
# 2、mscgGateway函数,从给的IP地址和子网掩码得到网关地址。（PS：默认网关为网络号+1，例如：192.168.1.10 255.255.255.0 的网关为
#     192.168.1.1）。
# 3、decSwitchBinary函数，十进制转换为二进制。
# 4、binarySwitchDec函数，二进制转换为十进制。
# 5、scanPort函数，测试端口是否通
# by xiaoxin 2017.06.15


#   ping测试
#   ip = IP地址
#   count = ping包的数量
#   size = ping包的大小
def ping_check(ip, count=4, size=64):  # 返回延迟ms以及丢包率 linux需要root权限
    ip_local = ip
    count_local = count
    size_local = size
    delay_avg = 'None'  # 平均延时
    loss_num = 'None'  # 丢包数量
    ping_result = ping(ip_local, count=count_local, size=size_local)
    ping_result = str(ping_result)
    loss_info = re.findall('timed out', ping_result)
    loss_num = len(loss_info)
    if loss_num < count_local:
        delay_info = re.search('Times min\/avg\/max is\s(.+)\sms', ping_result).group(1)
        delay_avg = delay_info.split('/')[2]
    loss_per = '{:.0%}'.format(loss_num / count_local)
    return delay_avg, loss_per


# 从IP地址中得到MSCG的IP地址
#   IP = VM的IP地址
#   mask = 子网掩码
#   参数为IP地址和子网掩码，返回MSCG的gia地址 ME60专用
def mscgGateway(ip, mask='255.255.254.0'):
    ipSplit = ip.split('.')  # 将IP以.为分隔符切割
    maskSplit = mask.split('.')

    ipBinary = [decSwitchBinary(i) for i in ipSplit]  # 将IP转换为二进制
    ipBinary = list(''.join(ipBinary))  # 转换为list

    maskBinary = [decSwitchBinary(i) for i in maskSplit]  # 将子网掩码转换为二进制
    maskBinary = list(''.join(maskBinary))

    for bit in range(len(maskBinary)):  # 如果子网掩码等于0，那么将IP对应的位置0
        if maskBinary[bit] == '0':
            ipBinary[bit] = '0'

    ipBinary[-1] = '1'  # IP最后一位,置1则是网关

    binGateway = [ipBinary[i:i + 8] for i in range(0, len(ipBinary), 8)]  # 将数据分段成十进制。
    gateway = []  # 定义一个list存取IP地址
    for dec in binGateway:  # 将IP地址转换为十进制
        decGateway = ''.join(dec)
        decGateway = str(binarySwitchDec(decGateway))
        gateway.append(decGateway)
    gateway_vip = '.'.join(gateway)
    gateway[3] = '2'
    gatewayMaster = '.'.join(gateway)
    gateway[3] = '3'
    gatewaybackup = '.'.join(gateway)
    gatewayALL = [gatewayMaster, gatewaybackup, gateway_vip]
    return gatewayALL


def decSwitchBinary(num):  # 将十进制转换为二进制不够8位前面补0
    num = str(num)
    binaryNum = '{0:08b}'.format(int(num))
    return str(binaryNum)


def binarySwitchDec(num):  # 将二进制转换为十进制
    num = str(num)
    decNum = int(num, base=2)
    return str(decNum)


def scanPort(ip, port):  # 端口测试 仅支持TCP
    conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    conn.settimeout(2)
    result = conn.connect_ex((ip, int(port)))
    if result == 0:  # 如果通，result=0,返回true
        return True
    else:  # 如果不通，result=1,返回false
        return False
    conn.close()


def image_to_base64(path):
    with open(path, 'rb') as img:
        # 使用base64进行编码
        b64encode = base64.b64encode(img.read())
        s = b64encode.decode()
        b64_encode = 'data:image/jpeg;base64,%s' % s
        # 返回base64编码字符串
        return b64_encode


def passwdinput(words):  # 输入密码显示*
    import msvcrt
    print(words, end='', flush=True)
    li = []
    while True:
        ch = msvcrt.getch()
        # 回车
        if ch == b'\r':
            msvcrt.putch(b'\n')
            password = b''.join(li).decode()
            return password
        # 退格
        elif ch == b'\x08':
            if li:
                li.pop()
                msvcrt.putch(b'\b')
                msvcrt.putch(b' ')
                msvcrt.putch(b'\b')
        # Esc
        elif ch == b'\x1b':
            break
        else:
            li.append(ch)
            msvcrt.putch(b'*')
    os.system('pause')

def revData_error(data):  # 判断是否包含错误代码
    errorCode = ['Error:']
    for error in errorCode:
        match = re.search(r'%s' % error, data, re.IGNORECASE)
        if match:
            return '命令执行出错'
    return 'NULL'

# 测试部分
if __name__ == '__main__':
    print(ping_check('XXXXXXXX'))
