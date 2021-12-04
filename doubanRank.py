#!/usr/bin/python3
# -*- coding: utf-8 -*-

import requests
import re
import time, random
import json


def doubanHeader():
    header = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/96.0.4664.45 Safari/537.36',
        'Referer': 'https://movie.douban.com/explore'
    }
    return header


def searchByResp(urls, session):  # 通过搜索豆瓣网页返回电影信息
    filmIndexUrls = urls
    result = ''  # 返回结果
    for filmIndexUrl in filmIndexUrls:
        indexResp = session.get(filmIndexUrl, headers=doubanHeader())
        indexRule = re.compile(
            r'<span property="v:itemreviewed">(.*?)</span>.*?<span property="v:initialReleaseDate" '
            r'content=".*?">(.*?)</span>'
            r'.*?<strong class="ll rating_num" property="v:average">(.*?)</strong>', re.S)
        filemInfo = indexRule.findall(indexResp.text)
        matchType = re.findall(r'<span property="v:genre">(.*?)</span>', indexResp.text, re.S)
        filmType = ','.join(matchType)
        # print(indexResp.text)
        content = re.findall(r'<span property="v:summary".*?>(.*?)</span>', indexResp.text, re.S)
        try:
            content = re.sub('\s', '', content[0]).strip('\n')
        except:
            content = '暂无'
        # print(content)
        result += '电影&电视剧名称：%s\n类型：%s\n上映时间：%s\n评分：%s\n简介：%s\n===============================\n' % (
            filemInfo[0][0], filmType, filemInfo[0][1], filemInfo[0][2], content)
        time.sleep(random.randint(3, 8))
    return result


def timeNow():  # 返回当前时间
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))


def doubanMovieRank():  # 豆瓣热门电影
    url = 'https://movie.douban.com/j/search_subjects?type=movie&tag=热门&sort=recommend&page_limit=20&page_start=0'
    session = requests.session()
    print('%s 搜索电影中...' % timeNow())
    resp = session.get(url, headers=doubanHeader())
    movieUrls = []
    for cell in resp.json()['subjects']:
        movieUrls.append(cell['url'])
        # print(cell['url'])
    result = searchByResp(movieUrls, session)
    print('%s 搜索完毕!' % timeNow())
    print('%s 开始发送...' % timeNow())
    sendtoVx('豆瓣热门电影推荐', result)
    print('%s 发送完毕' % timeNow())


def doubanTvRank():  # 采集豆瓣热门电视剧
    url = 'https://movie.douban.com/j/search_subjects?type=tv&tag=热门&sort=recommend&page_limit=20&page_start=0'
    session = requests.session()
    print('%s 搜索电视剧中...' % timeNow())
    resp = session.get(url, headers=doubanHeader())
    movieUrls = []
    for cell in resp.json()['subjects']:
        movieUrls.append(cell['url'])
    result = searchByResp(movieUrls, session)
    print('%s 搜索完毕!' % timeNow())
    print('%s 开始发送...' % timeNow())
    sendtoVx('豆瓣热门电视剧推荐', result)
    print('%s 发送完毕!' % timeNow())


def sendtoVx(title, content):  # 调用WX接口发送消息
    header = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/96.0.4664.45 Safari/537.36',
        'Content-Type': 'application/json'
    }
    url = 'http://www.pushplus.plus/send'
    token = '94f397f4a2ef4979afa5beaf9b2d8cb1'  # 在pushpush网站中可以找到
    title = title  # 改成你要的标题内容
    content = content  # 改成你要的正文内容
    topic = '54412331'
    data = {
        "token": token,
        "title": title,
        "content": content,
        "topic": topic
    }
    body = json.dumps(data).encode(encoding='utf-8')
    resp = requests.post(url, data=body, headers=header)
    print(timeNow(), resp.text)


if __name__ == '__main__':
    doubanMovieRank()
    doubanTvRank()
