#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import json
import commands
import traceback
import logging


reload(sys)
sys.setdefaultencoding('utf-8')


def _get_res(cmd, times=5):
    """通过curl命令获取url资源，最多重试times次"""
    ret = commands.getoutput(cmd)
    try_times = 0

    while try_times < times:
        try_times += 1

        if try_times > 1:
            logging.debug('Try %d time for "%s"' % (try_times, cmd))

        try:
            res = json.loads(ret)
        except ValueError as e:
            logging.error(e)
        else:
            return res

    raise IOError('Try 3 times and error: "%s"!' % (cmd,))


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


def get_stations_from_to():
    """获取某列车所有站点
    返回站点列表"""
    QUERY_STATIONS_CMD = "curl -s 'https://kyfw.12306.cn/otn/czxx/queryByTrainNo?train_no=490000T39604&from_station_telecode=WFK&to_station_telecode=SZQ&depart_date=2016-10-07' -H 'Pragma: no-cache' -H 'Accept-Encoding: gzip, deflate, sdch, br' -H 'Accept-Language: en-US,en;q=0.8,zh-CN;q=0.6,zh;q=0.4' -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.106 Safari/537.36' -H 'Accept: */*' -H 'Cache-Control: no-cache' -H 'X-Requested-With: XMLHttpRequest' -H 'Cookie: JSESSIONID=E0590039B6481B984912831DD2DF7507; BIGipServerotn=1005584906.64545.0000; _jc_save_fromStation=%u6F4D%u574A%2CWFK; _jc_save_toStation=%u6DF1%u5733%2CSZQ; _jc_save_fromDate=2016-10-07; _jc_save_toDate=2016-10-03; _jc_save_wfdc_flag=dc' -H 'Connection: keep-alive' -H 'If-Modified-Since: 0' -H 'Referer: https://kyfw.12306.cn/otn/leftTicket/init' --compressed --insecure"
    res = _get_res(QUERY_STATIONS_CMD)
    stations = res['data']['data']

    return stations


def query_tickets(from_, to, stations):
    """查询从from_到to的余票信息"""
    from_code = _station_code(from_['station_name'])
    to_code = _station_code(to['station_name'])
    code_param = "leftTicketDTO.from_station=%s&leftTicketDTO.to_station=%s" % (
        from_code, to_code
    )
    QUERY_TICKET_CMD = "curl -s 'https://kyfw.12306.cn/otn/leftTicket/queryT?leftTicketDTO.train_date=2016-10-07&" + code_param + "&purpose_codes=ADULT' -H 'Pragma: no-cache' -H 'Accept-Encoding: gzip, deflate, sdch, br' -H 'Accept-Language: en-US,en;q=0.8,zh-CN;q=0.6,zh;q=0.4' -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.106 Safari/537.36' -H 'Accept: */*' -H 'Cache-Control: no-cache' -H 'X-Requested-With: XMLHttpRequest' -H 'Cookie: JSESSIONID=E0590039B6481B984912831DD2DF7507; BIGipServerotn=1005584906.64545.0000; _jc_save_fromStation=%u6F4D%u574A%2CWFK; _jc_save_toStation=%u6DF1%u5733%2CSZQ; _jc_save_fromDate=2016-10-07; _jc_save_toDate=2016-10-03; _jc_save_wfdc_flag=dc' -H 'Connection: keep-alive' -H 'If-Modified-Since: 0' -H 'Referer: https://kyfw.12306.cn/otn/leftTicket/init' --compressed --insecure"
    res = _get_res(QUERY_TICKET_CMD)

    return res['data']


def has_tickets(result, filters):
    """查看余票数量
    filters 过滤条件，列表，如['yz_num', 'yw_num']查询硬座或硬卧"""
    tickets = result[0]['queryLeftNewDTO']
    has = any([i != '--' and i != '无' for i in map(tickets.get, filters)])

    return has


def format_result(result):
    """docstring for fo"""
    result = result[0]['queryLeftNewDTO']

    return '%s(%s) -> %s(%s) 无座: %3s 硬座: %3s 硬卧: %3s' % (
        result['from_station_name'], result['start_time'],
        result['to_station_name'], result['arrive_time'],
        result['wz_num'], result['yz_num'], result['yw_num']
    )


if __name__ == '__main__':
    stations = STATIONS
    my_stations = get_stations_from_to()
    for from_ in range(0, len(my_stations)-1):
        for to in range(from_+1, len(my_stations)):
            result = query_tickets(my_stations[from_], my_stations[to], stations)
            result = [i for i in result if i['queryLeftNewDTO']['station_train_code'] == 'T396']
            # if result and has_tickets(result, ['yw_num']):
            if result:
                print(format_result(result))
