#!/usr/bin/python
# -*- coding:utf-8 -*-

import sys
import boto.s3.connection
import urllib2,json,csv
import traceback

from common import *

CSV_FILE = 'dev-s3list-csv.py'

try:
    sts = 0
    # EIP有無チェック
    url = 'http://169.254.169.254/latest/meta-data/public-ipv4'
    try: urllib2.urlopen(url)
    except urllib2.HTTPError:
        sts = 1

    if sts == 0:
        url = 'http://169.254.169.254/latest/dynamic/instance-identity/document'
        # AWSアカウント取得
        account_id = json.load(urllib2.urlopen(url))['accountId']
        # S3バケット名
        bucket_name = 'log-'+ account_id

        # CSVファイル(書込み)
        writecsv = csv.writer(file(CSV_FILE, 'w'), lineterminator='\n')

        conn = boto.connect_s3()
        bucket = conn.get_bucket(bucket_name)

        keys = bucket.get_all_keys(prefix='AWSLogs')
        for key in keys:
            writecsv.writerow([time.strftime('%Y/%m/%d %H:%M:%S',time.localtime()),
                               key.bucket.name,
                               key.name,
                               key.size,
                               key.last_modified])

except:
    # 異常終了
    log_error('Error of the S3 information list.',traceback.format_exc())
