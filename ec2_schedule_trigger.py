#!/usr/bin/python
# -*- coding:utf-8 -*-

import os, sys
import boto.ec2
import urllib2, json
import fcntl
import ConfigParser
import traceback

from datetime import datetime

# 共通
from common import *

# 定義ファイルの取込み
path = os.environ["PYTHONPATH"]
COMMON = os.path.join(path,'common.conf')
USER = os.path.join(path,'user.conf')

config = ConfigParser.RawConfigParser()
config.read(COMMON)
SCHEDULE = config.get('schedule','schedule_conf')
LOCK_FILE = config.get('schedule','schedule_lock')
config.read(USER)
EC2START = config.get('schedule','start_time')
EC2STOP = config.get('schedule','stop_time')
EC2PERIOD = config.get('schedule','week_period')

#############################################################
#   排他制御の開始
#############################################################
def do_lock():
    try:
        lock_file = open(LOCK_FILE, "r")
        # 処理の排他用のファイルロック
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX|fcntl.LOCK_NB)
        return True
    except:
        return False

#############################################################
#   排他制御の解除
#############################################################
def do_unlock():
    try:
        if lock_file != None:
            # 排他制御の解除
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
    finally:
        if lock_file != None:
            lock_file.close()

#############################################################
#   事前チェック
#############################################################
def run_check():
    # EIP有無チェック
    eip_flag = 1
    url = 'http://169.254.169.254/latest/meta-data/public-ipv4'
    try: urllib2.urlopen(url)
    except urllib2.HTTPError:
        eip_flag = 0

    if eip_flag == 1:
        return True
    else:
        return False

#############################################################
#   スケジュール設定の確認
#############################################################
def init_config():
    instance_tag_name = []
    try:
        config = ConfigParser.RawConfigParser()
        config.read(SCHEDULE)

        # インスタンスID取得
        url = 'http://169.254.169.254/latest/meta-data/instance-id'
        my_instance_id = urllib2.urlopen(url).read()
        # リージョン取得
        url = 'http://169.254.169.254/latest/dynamic/instance-identity/document'
        region = json.load(urllib2.urlopen(url))['region']

        # EC2情報の取得
        conn = boto.ec2.connect_to_region(region)
        reservations = conn.get_all_instances()
        for reservation in reservations:
            for instance in reservation.instances:
                # 実行環境のEC2は対象外
                if my_instance_id == instance.id:
                    continue
                # スポットインスタンスは対象外
                if not instance.spot_instance_request_id is None:
                    continue
                # インスタンスストアは対象外
                if instance.root_device_type == 'instance-store':
                    continue

                if 'Name' in instance.tags and len(instance.tags['Name']) > 0:
                    name_tag = instance.tags['Name']
                    instance_tag_name.append(name_tag)

                    if not config.has_section(name_tag):
                        # 新しいEC2を設定ファイルへ追加
                        config.add_section(name_tag)
                        config.set(name_tag, 'start', EC2START)
                        config.set(name_tag, 'stop', EC2STOP)
                        config.set(name_tag, 'period', EC2PERIOD)

        # 存在しないEC2を設定ファイルから削除
        for section in config.sections():
            if not section in instance_tag_name:
                config.remove_section(section)

        # 設定ファイルへの書込み
        config.write(open(SCHEDULE, 'w'))

    except:
        log_error('EC2 Schedule management. - init_config', traceback.format_exc())

#############################################################
#   スケジュール実行
#############################################################
def do_scheduler():
    try:
        # 当日の日時取得
        now = datetime.now().strftime("%Y/%m/%d %H:%M:%S")

        # 設定情報の取得
        config = ConfigParser.RawConfigParser()
        config.read(SCHEDULE)

        # インスタンスID取得
        url = 'http://169.254.169.254/latest/meta-data/instance-id'
        my_instance_id = urllib2.urlopen(url).read()
        # リージョン取得
        url = 'http://169.254.169.254/latest/dynamic/instance-identity/document'
        region = json.load(urllib2.urlopen(url))['region']

        # EC2情報の取得
        conn = boto.ec2.connect_to_region(region)
        reservations = conn.get_all_instances()
        for reservation in reservations:
            for instance in reservation.instances:
                # 実行環境のEC2は対象外
                if my_instance_id == instance.id:
                    continue
                # スポットインスタンスは対象外
                if not instance.spot_instance_request_id is None:
                    continue
                # インスタンスストアは対象外
                if instance.root_device_type == 'instance-store':
                    continue

                if 'Name' in instance.tags and len(instance.tags['Name']) > 0:
                    name_tag = instance.tags['Name']
                else:
                    name_tag = '@Default@'

                if name_tag in config.sections():
                    start = get_parameter(config.get(name_tag,'start'))
                    stop = get_parameter(config.get(name_tag,'stop'))
                    period = get_parameter(config.get(name_tag,'period'))
                else:
                    start = EC2START
                    stop = EC2STOP
                    period = EC2PERIOD

                # パラメータ不整合のため対象外
                if start == stop:
                    instance.add_tag('Schedule: Latest start time',
                                     'Parameters Error')
                    instance.add_tag('Schedule: Latest stop time',
                                     'Parameters Error')
                    continue

                if check_config_action(start, period) and \
                   instance.state == 'stopped':
                    # EC2起動
                    instance.start()
                    instance.add_tag('Schedule: Latest start time', now)

                if check_config_action(stop, period) and \
                   instance.state == 'running':
                    # EC2停止
                    instance.stop()
                    instance.add_tag('Schedule: Latest stop time', now)
 
    except:
        log_error('EC2 Schedule management. - do_scheduler', traceback.format_exc())

#############################################################
#   パラメータ整形
#############################################################
def get_parameter(items):
    param = [item for item in items.replace(' ', '').split(',')]
    return param if len(param) > 1 else param[0]

#############################################################
#   スケジュールの判定チェック
#############################################################
def check_config_action(hour, period):
    # 時刻チェック
    if hour == datetime.now().strftime("%H"):
        time_flag = 1
    else:
        time_flag = 0

    # 周期のチェック
    if period == 'everyday':
        period_flag = 1
    elif period == 'weekday':
        if datetime.now().weekday() in [0, 1, 2, 3, 4]:
            period_flag = 1
        else:
            period_flag = 0
    elif period == 'disabled':
        period_flag = 0
    else:
        period_flag = False

    # 時刻＆周期のチェック
    if time_flag == 1 and period_flag == 1:
        return True
    else:
        return False

#############################################################
#   メイン処理
#############################################################
if __name__ == '__main__':

    try:
        # 排他制御の開始
        with open(LOCK_FILE, "r") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX|fcntl.LOCK_NB)

            try:
                # 開始メッセージ
                log_info('EC2 Schedule Management Start')

                # EIPの割当がない場合は終了
                if not run_check:
                    exit(1)

                # 事前チェック
                init_config()
                # EC2スケジュール実行
                do_scheduler()

                # 終了メッセージ
                log_info('EC2 Schedule Management End')

            except:
                log_info('EC2 Schedule Management Fail')
            finally:
                # 排他制御の解除
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    except IOError:
        pass
