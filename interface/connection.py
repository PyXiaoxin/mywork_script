#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os, re
import paramiko
import time
import ftplib
from telnetlib import Telnet
import pymysql
import logging
from openpyxl import load_workbook
from openpyxl import Workbook
from openpyxl.styles import Font
from concurrent import futures
from .public_env import get_value


#   变量说明
#   ip = ip地址
#   username = 用户名
#   password = 密码
#   port = 端口号
#   by xiaoxin
# 免责声明：仅用于自己测试,出了问题，概不负责


class deviceControl:  # 交换机登陆模块
    def __init__(self, ip, username, password, port=22):
        self.password = password
        self.username = username
        self.ip = ip
        self.port = port

    def connectDevice(self):  # 适用于连接路由，交换机。登录成功返回True
        times = 0
        # paramiko.util.log_to_file('paramiko.log') 调试日志
        while True:  # 尝试3次登陆
            try:
                self.ssh = paramiko.SSHClient()
                self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                self.ssh.connect(self.ip, self.port, self.username, self.password, timeout=300)
                break
            except Exception as e:
                # print(Exception, e)
                time.sleep(2)
                times += 1
                if times == 2:  # 超时次数=3返回错误
                    self.close()  # 关闭会话
                    return False
        self.ssh_shell = self.ssh.invoke_shell()  # 使用invoke是为了可以执行多条命令
        self.ssh_shell.get_pty()
        self.ssh_shell.settimeout(1)  # tunnel超时
        return True

    def sendCmd(self, cmd):  # 发送命令(PS:加上了回车符)，返回发送的字节数
        _cmd = cmd
        status = self.ssh_shell.send(' %s\n' % _cmd)
        return status

    def recData(self):  # 接受返回数据
        data = ''  # 定义一个变量用于返回数据
        times = 0  # 循环次数叠加
        while True:
            try:
                rec = self.ssh_shell.recv(1024)
                data += rec.decode('utf-8')
            except:
                if data.endswith('---- More ----'):  # 判断末尾是否包含more，包含则发出3个空格
                    for i in range(2):  # 连续发三个空格
                        self.ssh_shell.send(' ')
                        time.sleep(1)
                    time.sleep(2)
                else:
                    times += 1
                    if times == 3:  # 超时次数=3的时候跳出循环
                        break
        data = deleteUnknownStr(data)  # 去掉转义字符
        return data

    def close(self):  # 关闭session
        try:
            self.ssh.close()
        except:
            pass

    def connectLinux(self):  # 适用于连接F5/netscaler设备
        try:
            self.t = paramiko.Transport(sock=(self.ip, 22))
            self.t.connect(username=self.username, password=self.password)
            self.chan = self.t.open_session(timeout=5)
            self.chan.settimeout(0.5)  # 设置session超时
            self.chan.get_pty()
            self.chan.invoke_shell()
            return True
        except Exception as e:
            self.close()
            return False

    def sendCmdLinux(self, cmd):  # 适用于F5/netscaler设备发送命令（PS:自带回车符），返回运行结果
        cmd += '\n'  # 命令加上回车符
        result = ''
        self.chan.send(cmd)  # 发送要执行的命令
        times = 1
        while True:  # 回显很长的命令可能执行较久，通过循环10次获取回显信息
            time.sleep(0.5)
            try:
                ret = self.chan.recv(10240)
                result += ret.decode('utf-8')
            except:
                times += 1
                if times == 5:
                    break
        return result

    def telnetConnect(self):
        times = 0
        while True:
            try:
                self.tn = Telnet(self.ip, port=23, timeout=10)
                break
            except:
                times += 1
                if times == 3:
                    self.telnetClose()
                    return False
        # 输入登录用户名
        self.tn.read_until(b'Username:', timeout=10)
        self.tn.write(self.username.encode('ascii') + b'\n')
        # 输入登录密码
        self.tn.read_until(b'Password:', timeout=10)
        self.tn.write(self.password.encode('ascii') + b'\n')
        times = 0
        while True:
            time.sleep(0.5)
            loginInfo = self.tn.read_very_eager()
            # print(times,loginInfo)
            if loginInfo.endswith(b'>'):  # 判断是否登录成功
                return True
            else:
                times += 1
                if times == 3:  # 尝试4次不成功则返回错误
                    return False

    def telnetSendReturn(self, cmd):  # 发送命令并获取数据
        _cmd = cmd
        data = ''  # 定义一个变量获取返回的
        times = 0
        try:
            _cmd = _cmd.encode('ascii') + b'\n'
            self.tn.write(_cmd)
        except Exception as e:
            return data
        while True:
            time.sleep(0.5)
            try:
                rec = self.tn.read_very_eager()
                rec = rec.decode('utf-8')
            except:
                rec = self.tn.read_very_eager()
            data += str(rec)
            if data.endswith(('---- More ----')):
                self.tn.write(' '.encode('ascii'))
            else:
                times += 1
                if times == 10:
                    break
        # data = re.re('  ---- More ----\x1b[42D                                          \x1b[42D', '')
        data = deleteUnknownStr(data)
        return data

    def telnetClose(self):  # 关闭连接
        try:
            self.tn.close()
        except:
            pass


class deviceContrl_auto(deviceControl):  # 继承deviceControl的简洁登录 SSH TELNET合并
    def __init__(self, ip, username, password, port=22):  # 继承构造方法
        deviceControl.__init__(self, ip, username, password, port)

    def sendCmd_auto(self, cmd_list=[]):  # 使用Telnet SSH 执行多条命令返回结果
        cmd_local = cmd_list  # list
        result = {}  # 命令返回的结果
        ssh_login = deviceControl.connectDevice(self)  # 使用父类SSH登录
        if ssh_login:
            loginWay = 'BY SSH'
            deviceControl.recData(self)  # 欢迎数据获取
            for cmd in cmd_local:
                deviceControl.sendCmd(self, cmd)
                rec_data = deviceControl.recData(self)
                result[cmd] = rec_data
                result['loginWay'] = loginWay
            deviceControl.close(self)  # 关闭会话
        else:
            telnet_login = deviceControl.telnetConnect(self)
            if telnet_login:
                loginWay = 'BY TELNET'
                for cmd in cmd_local:
                    rec_data = deviceControl.telnetSendReturn(self, cmd)
                    result[cmd] = rec_data
                    result['loginWay'] = loginWay
                deviceControl.telnetClose(self)
            else:
                raise RuntimeError('SSH TELNET FAIL')
        return result


def deleteUnknownStr(line_p):  # 删除垃圾字符，转义序列字符
    line, i, imax = '', 0, len(line_p)
    while i < imax:
        ac = ord(line_p[i])
        if (32 <= ac < 127) or ac in (9, 10):  # printable, \t, \n
            line += line_p[i]
        elif ac == 27:  # remove coded sequences
            i += 1
            while i < imax and line_p[i].lower() not in 'abcdhsujkm':
                i += 1
        elif ac == 8 or (ac == 13 and line and line[-1] == ' '):  # backspace or EOL spacing
            if line:
                line = line[:-1]
        i += 1
    line = re.sub('\s{2}---- More ----\s+', '', line)
    return line


# =======================================分割线=============================================================


# 变量说明
# ip = FTP服务器地址
# username = 用户名
# password = 密码
# port = 端口号 默认为21
# filename = 文件名
# remotePath = 远程路径 默认是进入FTP服务器的当前路径
# localPath = 本地路径
class easyftp:  # FTP模块
    def __init__(self, ip, username, password, port=21):
        self.ip = ip
        self.username = username
        self.password = password
        self.port = port

    def connetServer(self):  # 登录FTP服务器，如果成功返回欢迎信息，如果失败则返回false
        try:
            self.ftp = ftplib.FTP()  # 调用ftplib的FTP()类
            self.ftp.connect(self.ip, self.port, timeout=10)  # 连接FTP服务器
            self.ftp.login(self.username, self.password)  # 输入用户密码登录
            welInfo = self.ftp.getwelcome()  # 登录成功返回欢迎信息
            return welInfo
        except:  # 登录失败返回false
            return False

    def ftpGet(self, filename, remotePath=''):  # 下载文件,不支持中文文件名
        try:
            self.ftp.cwd(remotePath)  # 切换FTP的目录
            remoteFiles = self.ftp.nlst()  # 获取当前目录的文件名
            for i in remoteFiles:  # 遍历文件名
                if filename == i:  # 如果文件名等于输入的文件名
                    # self.makeDir(self.ip)  # 创建以IP地址命名的文件夹
                    localPathFile = filename  # self.ip + '\\' + filename  # 本地存放路径，当前路径下，以IP为文件夹名+文件名
                    with open(localPathFile, 'wb') as fd:  # 打开本地文件以写入的方式
                        self.ftp.retrbinary('RETR ' + filename, fd.write, 1024)  # 执行下载操作
                    remoteDir = []
                    self.ftp.dir('', remoteDir.append)
                    for fileLine in remoteDir:
                        if filename in fileLine:
                            try:
                                remoteFileSize = str(fileLine).split()[4]  # 获取上传的文件大小，通过查看大小命令来查看文件大小
                            except:
                                remoteFileSize = str(fileLine).split()[2]  # Windows目录获取文件大小
                    localFileSize = os.path.getsize(localPathFile)  # 获取本地的文件大小
                    # print remoteFileSize,localFileSize
                    if int(localFileSize) == int(remoteFileSize):  # 判断远程的文件和本地的的大小是否相等
                        return True
                    else:
                        return False
            print('%s not found' % filename)
            return False
        except Exception as e:
            print(e)
            return False

    def ftpPut(self, filename, remotePath='', localPath=''):  # 文件上传，不支持中文文件名。
        try:
            filename = filename.lower()  # 将文件名转换为小写字母。
            self.ftp.cwd(remotePath)  # 切换FTP服务器的目录，有的FTP不支持
            remoteFiles = self.ftp.nlst()
            if filename not in remoteFiles and filename.upper() not in remoteFiles:  # 判断文件是否已存在
                localPathFile = filename
                if localPath != '':  # 如果有输入本地目录，那么文件名等于目录加上文件名。
                    localPathFile = localPath + filename
                with open(localPathFile, 'rb') as fd:  # 以 with的方式打开文件
                    self.ftp.storbinary('STOR %s' % filename, fd, 1024)  # 执行上传文件动作
                # remoteFileSize = self.ftp.size(filename)  # 获取FTP上的文件大小,交换机不支持这个命令
                remoteDir = []
                self.ftp.dir('', remoteDir.append)
                for fileLine in remoteDir:
                    fileLine = fileLine.lower()  # 将文件名转换为小写字母。
                    if filename in fileLine:
                        remoteFileSize = str(fileLine).split()[4]  # 获取上传的文件大小，通过查看大小命令来查看文件大小
                localFileSize = os.path.getsize(localPathFile)  # 获取本地的文件大小
                if int(localFileSize) == int(remoteFileSize):  # 判断远程的文件和本地的的大小是否相等
                    print('\'%s\' upload completed at %s' % (filename, self.ip))
                    return True
                else:
                    print('\'%s\' remote file was incomplete at %s' % (filename, self.ip))
                    return False
            else:
                print('\'%s\' this file existed on %s' % (filename, self.ip))
                return False
        except Exception as e:
            print(self.ip, e)
            return False

    def close(self):  # 退出FTP连接
        try:
            self.ftp.quit()
        except:
            pass


class mysql_db:  # 数据库模块
    def __init__(self, host, username, password, dbname):  # 初始化
        self.host = host
        self.username = username
        self.password = password
        self.dbname = dbname

    def mysql_auth(self):
        try:
            # 打开数据库连接
            self.db = pymysql.connect(self.host, self.username, self.password, self.dbname, charset='utf8')
            # 使用 cursor() 方法创建一个游标对象 cursor
            self.cur = self.db.cursor()
            return True
        except Exception:
            raise

    def db_action(self, db_sql):  # 数据库插入
        # SQL 插入语句
        sql_insert = db_sql
        try:
            # 执行sql语句
            self.cur.execute(sql_insert)
            # 提交到数据库执行
            self.db.commit()
            return True
        except Exception as e:
            # 如果发生错误则回滚
            self.db.rollback()
            self.db_close()
            raise

    def db_get(self, db_sql):  # 查询
        sql_query = db_sql
        try:
            self.cur.execute(sql_query)
        except Exception as e:
            self.db_close()
            raise e
        db_data = self.cur.fetchall()  # 获取全部数据
        return db_data

    def db_close(self):  # 关闭数据库
        try:
            self.cur.close()
            self.db.close()
        except:
            pass


class excel:  # Excel表格处理 只支持.xlsx格式
    def __init__(self, filename):  # 初始化
        self.filename = filename  # 文件名 .xlsx
        self.wb_obj = Workbook()  # 写入对象初始化
        self.wb_obj.active

    # 写入数据
    def excel_write(self, title, data, sheetname='data01', sheetIndex=1):
        title_local = title  # 标题 list
        data_local = data  # 需要写入的数据 list[[],[]]
        sheetname_local = sheetname  # sheet名称
        sheetIndex_local = sheetIndex - 1  # sheet的位置 默认是第一张表 位置从0开始
        wsObj = self.wb_obj.create_sheet(sheetname_local, sheetIndex_local)
        wsObj.append(title_local)
        title_font = Font(b='bold', size='12')
        for i in range(1, len(title) + 1):
            cell = wsObj.cell(row=1, column=i)
            cell.font = title_font
        for row_data in data_local:
            # print(row_data)
            wsObj.append(row_data)  # 写入数据

    # 保存文件
    def save_file(self):
        timeNow = time.strftime('%Y-%m-%d_%H%M%S', time.localtime(time.time()))
        filename_save = self.filename.replace('.xlsx', '')
        filename_save = '%s_%s.xlsx' % (filename_save, timeNow)  # 返回文件名
        self.wb_obj.save(filename_save)  # 存盘
        self.wb_obj.close()  # 关闭
        return filename_save

    # 读取数据 默认打开第一个sheet从第二行读
    def excel_read(self, sheetnum=1, row=0, column=0, row_start=2, column_start=1):
        file_local = self.filename
        row_start_local = row_start  # 起始行
        column_start_local = column_start  # 起始列
        wb = load_workbook(filename=file_local)  # 打开一个excel对象
        sheetnames = wb.sheetnames  # 获取sheets
        ws = wb[sheetnames[sheetnum - 1]]  # 打开第X个sheet
        if row == 0:
            row = ws.max_row  # 行计数
        if column == 0:
            column = ws.max_column  # 列计数
        data_result = []  # 结果集
        for rx in range(row_start_local, row + 1):  # 循环读取每一行sheet数据
            info = []  # 一行的数据集
            for cx in range(column_start_local, column + 1):  # 循环读取每一行的列数据
                cell_info = ws.cell(row=rx, column=cx).value
                info.append(cell_info)
            data_result.append(info)
        wb.close()  # 关闭
        self.wb_obj.close()  # 关闭
        return data_result


def readTxt(filename):  # 读取TXT 返回list 忽略#号
    readReturn = []
    with open(filename, 'r', encoding='utf-8') as openfiles:
        readInfo = openfiles.readlines()
    for read_row in readInfo:  # #号行忽略
        readTemp = read_row.strip().startswith('#')
        if readTemp:
            readInfo.remove(read_row)
        else:
            readReturn.append(read_row.strip().strip('\n\r'))
    return readReturn


def makeDir(dirName):  # 在当前目录创建文件夹
    path = os.getcwd()  # 获取当前路径
    dir = os.listdir(path)  # 获取当前路径所有文件名
    if dirName not in dir:  # 判断本地是否已经有此文件。如果没有则创建，有则不创建。
        os.mkdir(dirName)


class logg:  # 日志模块
    def __init__(self, loggername, filename):
        # 创建一个logger
        self.logger = logging.getLogger(loggername)
        self.logger.setLevel(logging.DEBUG)

        # 创建一个handler，用于写入日志文件
        timeNow = time.strftime('%Y-%m-%d_%H%M%S', time.localtime(time.time()))
        filename_local = filename
        logname = '%s_%s.log' % (filename_local, timeNow)  # 日志名+日期= 存盘的文件名
        fh = logging.FileHandler(logname, encoding='utf-8')  # 指定utf-8格式编码，避免输出的日志文本乱码
        fh.setLevel(logging.DEBUG)

        # 创建一个handler，用于将日志输出到控制台
        ch = logging.StreamHandler()
        ch.setLevel(logging.ERROR)

        # 定义handler的输出格式
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s:%(message)s',
                                      datefmt='%Y-%m-%d %H:%M:%S')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        # 给logger添加handler
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)

    def get_log(self):
        # 回调logger实例
        return self.logger


class autoThreadingPool():  # 线程池
    def __init__(self, worker=30):
        self.bar = get_value('bar')
        self.worker_local = worker
        self.result = []

    def __call__(self, func, datalist=[]):  # 函数，迭代数据
        func_local = func  # function
        datalist_local = datalist  # data
        with futures.ThreadPoolExecutor(max_workers=self.worker_local) as exector:  # max_workers 线程池的数量
            future_list = []
            for row in datalist_local:
                future = exector.submit(func_local, row)
                future_list.append(future)
            unit = 0.8 / len(future_list)
            num = 0.1
            for future in futures.as_completed(future_list):
                res = future.result()
                self.result.append(res)
                num += unit
                self.bar(num)
        return self.result


if __name__ == '__main__':
    # ip = 'XXXX'
    # ip2 = 'XXXX'
    # user = 'XXX'
    # passwd = 'xxxxx'
    # cmds = ['dis clock', 'dis version']
    # conn = deviceContrl_auto(ip, user, passwd)
    # res = conn.sendCmd_auto(cmds)
    # print(res)
    unit = '{:.2f}'.format(0.8 / len(range(50)))
    print(unit)
