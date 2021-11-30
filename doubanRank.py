#!/usr/bin/python3
# -*- coding: utf-8 -*-

import requests
import re
import time, random
import json


def douban():
    header = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36'
    }
    url = 'https://movie.douban.com/chart'
    session = requests.session()
    resp = session.post(url, headers=header)
    # print(resp.text)
    rules = re.compile(r'<div class="pl2">.*?"(htt.*?)".*?</a>', re.S)
    filemIndexUrls = rules.findall(resp.text)
    result = ''  # 返回结果
    for filemIndexUrl in filemIndexUrls:
        indexResp = session.post(filemIndexUrl, headers=header)
        indexRule = re.compile(
            r'<span property="v:itemreviewed">(.*?)</span>.*?<span property="v:initialReleaseDate" content=".*?">(.*?)</span>'
            r'.*?<strong class="ll rating_num" property="v:average">(.*?)</strong>', re.S)
        filemInfo = indexRule.findall(indexResp.text)
        matchType = re.findall(r'<span property="v:genre">(.*?)</span>', indexResp.text)
        filmType = ','.join(matchType)
        result += '电影名称：%s\n类型：%s\n上映时间：%s\n评分：%s\n===============================\n' % (filemInfo[0][0], filmType, filemInfo[0][1], filemInfo[0][2])
        time.sleep(random.randint(3, 8))
    return result


def sendtoVx():
    header = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36',
        'Content-Type': 'application/json'
    }
    url = 'http://www.pushplus.plus/send'
    token = '94f397f4a2ef4979afa5beaf9b2d8cd1'  # 在pushpush网站中可以找到
    title = '每周五电影推荐'  # 改成你要的标题内容
    content = douban()  # 改成你要的正文内容
    data = {
        "token": token,
        "title": title,
        "content": content
    }
    body = json.dumps(data).encode(encoding='utf-8')
    resp = requests.post(url, data=body, headers=header)
    print(resp.text)


if __name__ == '__main__':
    sendtoVx()
