#!/usr/bin/python
# -*- coding:utf-8 -*-

import os, sys
import time, socket
import ConfigParser
import logging,traceback

# 定義ファイルの取込み
path = os.environ["PYTHONPATH"]
COMMON = os.path.join(path,'common.conf')
config = ConfigParser.RawConfigParser()
config.read(COMMON)
LOG_FILE = config.get('common','log_path')

#############################################################
#   ログファイルへの書込み
#############################################################
def set_logging(message, level):
    # ログ設定
    LOG_FORMAT = '%(asctime)s %(host)s [%(levelname)s] %(message)s'
    logging.basicConfig(filename=LOG_FILE,
                        format=LOG_FORMAT,
                        level=logging.INFO)

    # ホスト名
    hostname = {}
    hostname['host'] = socket.gethostname()

    # ログメッセージの生成
    if level == 'error':
        logging.error(message, extra=hostname)
    elif level == 'warning':
        logging.warning(message, extra=hostname)
    else :
        logging.info(message, extra=hostname)

#############################################################
#   ログ出力(INFO)
#############################################################
def log_info(message):
    set_logging(message, 'info')

#############################################################
#   ログ出力(WARNING)
#############################################################
def log_warning(message):
    set_logging(message, 'warning')

#############################################################
#   ログ出力(ERROR)
#############################################################
def log_error(message, exception):
    set_logging(message, 'error')
    set_logging(exception, 'error')

#if __name__ == '__main__':
#    log_info("test info")
#    log_warning("test warning")
#    log_error("test error", "error")
