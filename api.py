#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import json
import logging
import urllib
import urllib2
from collections import OrderedDict

# 关闭证书验证(12306的证书坑爹，你懂得！)
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

reload(sys)
sys.setdefaultencoding('utf-8')

def _get_res(url, params=None, times=5):
    """通过curl命令获取url资源，最多重试times次"""
    if params is None:
        params = {}

    try_times = 0

    while try_times < times:
        try_times += 1

        if try_times > 1:
            logging.debug('Try %d time for "%s"' % (try_times, url))

        try:
            ret = urllib2.urlopen('%s?%s' % (url, urllib.urlencode(params))).read()
            res = json.loads(ret)
        except ValueError as e:
            logging.error(e)
        else:
            return res

    raise IOError('Try 3 times and error: "%s"!' % (url,))


def _parse_station():
    """解析station_name.js，获取列表
    列表项: ['bjb', '北京北', 'VAP', 'beijingbei', 'bjb', '0']
    """
    content = open('station_name.js', 'r').read().split("'")[1]
    stations = [i.split('|') for i in content.split('@')][1:]

    return stations


STATIONS = _parse_station()


def _station_code(station_name):
    """从station获取station的code"""
    return [i for i in STATIONS if i[1] == station_name][0][2]


def query_train(train_no, from_, to, date):
    """获取某列车所有站点
    返回站点列表"""
    url = 'https://kyfw.12306.cn/otn/czxx/queryByTrainNo'

    params = OrderedDict()
    params['train_no'] = train_no
    params['from_station_telecode'] = _station_code(from_)
    params['to_station_telecode'] = _station_code(to)
    params['depart_date'] = date

    res = _get_res(url, params)
    # ret = res['data']['data']
    ret = [i for i in res['data']['data'] if i['isEnabled']]

    return ret


def query_tickets(train_date, from_, to):
    """查询从from_到to的余票信息
    train_date  查询日期，如'2016-10-17'
    from_       出发地，如'吉安'
    to          终到地，如'深圳'"""
    url = 'https://kyfw.12306.cn/otn/leftTicket/queryT'

    params = OrderedDict()
    params['leftTicketDTO.train_date'] = train_date
    params['leftTicketDTO.from_station'] = _station_code(from_)
    params['leftTicketDTO.to_station'] = _station_code(to)
    params['purpose_codes'] = 'ADULT'

    res = _get_res(url, params)
    ret = res['data']

    return ret


def has_tickets(result, filters):
    """查看余票数量
    filters     过滤条件，列表，如['yz_num', 'yw_num']查询硬座或硬卧
                rw_num 软卧 yw_num 硬卧 rz_num 软座 yz_num 硬座 wz_num 无座"""
    tickets = result[0]['queryLeftNewDTO']
    has = any([i != '--' and i != '无' for i in map(tickets.get, filters)])

    return has


def format_result(tickets):
    """格式化余票查询结果
    tickets     query_tickets的结果"""
    tickets = tickets[0]['queryLeftNewDTO']

    return '%s(%s) -> %s(%s) 无座: %3s 硬座: %3s 软座: %3s 硬卧: %3s 软卧 %3s' % (
        tickets['from_station_name'], tickets['start_time'],
        tickets['to_station_name'], tickets['arrive_time'],
        tickets['wz_num'], tickets['yz_num'], tickets['rz_num'],
        tickets['yw_num'], tickets['rw_num']
    )


if __name__ == '__main__':
    dt = '2016-10-17'
    my_stations = query_train('490000T39604', '吉安', '深圳', dt)
    for from_ in range(0, len(my_stations)-1):
        for to in range(from_+1, len(my_stations)):
            result = query_tickets(dt, my_stations[from_]['station_name'], my_stations[to]['station_name'])
            result = [i for i in result if i['queryLeftNewDTO']['station_train_code'] == 'T397']
            if result and has_tickets(result, ['yw_num', 'yz_num']):
                print(format_result(result))
