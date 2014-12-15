#!/usr/bin/python
# -*- coding:utf-8 -*-

import os, sys
import fcntl
import ConfigParser
import datetime
import traceback

# 共通
from common import *

# 定義ファイルの取込み
path = os.environ["PYTHONPATH"]
COMMON = os.path.join(path,'common.conf')
USER = os.path.join(path,'user.conf')

config = ConfigParser.RawConfigParser()
config.read(COMMON)
LAST_BACKUP = config.get('backup','latest_backup_date')
BACKUP_LOCK = config.get('backup','backup_lock')
config.read(USER)
BACKUPTIME = config.get('backup','backup_hour')


# 排他制御
lock_file = None

#############################################################
#   バックアップ処理の判定チェック
#############################################################
def need_backup():
    fd = None
    try:
        # パラメータチェック
        try:
            backup_start = BACKUPTIME
        except:
            backup_start = 0

        # 直近のバックアップ実行日時を取得
        fd = open(LAST_BACKUP, "r")
        line = fd.readlines()
        if len(line) < 2:
            return True
        last_date = line[0].rstrip()
        last_time = line[1].rstrip()

        # 次のバックアップ実行日時を決める
        last = datetime.datetime.strptime(last_date + str(backup_start),
                                          "%Y%m%d%H")
        next = last + datetime.timedelta(1)

        # 現在日時取得
        now = datetime.datetime.now()

        if now >= next:
            return True
        else:
            return False

    except:
        return True

    finally:
        if fd != None:
            fd.close()

#############################################################
#   バックアップ日時の記録
#############################################################
def record_backup(date):
    fd = None
    try:
        fd = open(LAST_BACKUP, "w")
        fd.write(date.strftime("%Y%m%d") + "\n")
        fd.write(date.strftime("%H") + "\n")
    except:
        # バックアップ日時を記録できない
        log_error('Not possible to record the backup date and time.',
                  traceback.format_exc())
    finally:
        if fd != None:
	    fd.close()

#############################################################
#   排他制御の開始
#############################################################
def do_backup():
    try:
        global lock_file
        lock_file = open(BACKUP_LOCK, "r")
        try:
            # 処理の排他用のファイルロック
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX|fcntl.LOCK_NB)
            return need_backup()
        except:
            lock_file = None
            return False
    except:
        return False

#############################################################
#   排他制御の解除
#############################################################
def undo_backup():
    try:
        global lock_file
        if lock_file != None:
            # 排他制御の解除
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
             
    except:
        # 排他制御の解除に失敗
        log_error('The failure to release the exclusive control.',
                  traceback.format_exc())

    finally:
        if lock_file != None:
            lock_file.close()

