#!/usr/bin/python
# -*- coding:utf-8 -*-

import sys
import boto.s3.connection, boto.sqs.message
import urllib2, json, gzip
import cStringIO
import traceback

from common import *

try:
    sts = 0
    # EIP有無チェック
    url = 'http://169.254.169.254/latest/meta-data/public-ipv4'
    try: urllib2.urlopen(url)
    except urllib2.HTTPError:
        sts = 1

    if sts == 0:
        sqs_queue = "cloudtrail-es"

        # 引数取得
        argv = sys.argv
        argc = len(argv)

        if argc != 2:
            print "Usage: python %s {del|info}" %argv[0]
            quit()
        proc = argv[1]

        # リージョン取得
        url = 'http://169.254.169.254/latest/dynamic/instance-identity/document'
        region = json.load(urllib2.urlopen(url))['region']

        # SQSからキュー取得
        sqs_conn = boto.sqs.connect_to_region(region)
        queue = sqs_conn.get_queue(sqs_queue)

        queue_attr = queue.get_attributes()

        queue.set_message_class(boto.sqs.message.RawMessage)

        # キューから取込むメッセージ最大数
        queue_count = queue.count()
        if queue_count > 2048:
            queue_count = 2048

        s3_conn = boto.s3.connection.S3Connection()

        for i in xrange(queue_count):
            log_notifications = queue.get_messages(num_messages=1,visibility_timeout=20,wait_time_seconds=20)
            for notification in log_notifications:
                envelope = json.loads(notification.get_body())
                message = json.loads(envelope["Message"])

                # S3からログ取得
                bucket_name = message["s3Bucket"]
                s3_bucket = s3_conn.lookup(bucket_name)

                for key in message["s3ObjectKey"]:
                    s3_file = s3_bucket.get_key(key)
                    file_json = json.load(gzip.GzipFile(None,"rb",None,cStringIO.StringIO(s3_file.read())))
                    records = file_json["Records"]
                    for record in records:
                        print json.dumps(record)

                if proc == 'del':
                    queue.delete_message(notification)

except:
    # 異常終了
    log_error('Error of the SQS Queue message Getting.',traceback.format_exc())

