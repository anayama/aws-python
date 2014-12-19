#!/usr/bin/python
# -*- coding:utf-8 -*-

import sys
import boto.s3.connection
import urllib2, json
import time
import traceback

from boto.s3.connection import Location

from common import *

S3_POLICY_LOGGING = """{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AWSCloudTrailAclCheck",
            "Effect": "Allow",
            "Principal": {
                "AWS": [
                    "arn:aws:iam::903692715234:root",
                    "arn:aws:iam::859597730677:root",
                    "arn:aws:iam::814480443879:root",
                    "arn:aws:iam::216624486486:root",
                    "arn:aws:iam::086441151436:root",
                    "arn:aws:iam::388731089494:root",
                    "arn:aws:iam::284668455005:root",
                    "arn:aws:iam::113285607260:root"
                ]
            },
            "Action": "s3:GetBucketAcl",
            "Resource": "arn:aws:s3:::<BucketName>"
        },
        {
            "Sid": "AWSCloudTrailWrite",
            "Effect": "Allow",
            "Principal": {
                "AWS": [
                    "arn:aws:iam::903692715234:root",
                    "arn:aws:iam::859597730677:root",
                    "arn:aws:iam::814480443879:root",
                    "arn:aws:iam::216624486486:root",
                    "arn:aws:iam::086441151436:root",
                    "arn:aws:iam::388731089494:root",
                    "arn:aws:iam::284668455005:root",
                    "arn:aws:iam::113285607260:root"
                ]
            },
            "Action": "s3:PutObject",
            "Resource": "arn:aws:s3:::<BucketName>/<Prefix>/AWSLogs/<CustomerAccountID>/*",
            "Condition": {
                "StringEquals": {
                    "s3:x-amz-acl": "bucket-owner-full-control"
                }
            }
        }
    ]
}"""

try:
    sts = 0
    # EIP有無チェック
    url = 'http://169.254.169.254/latest/meta-data/public-ipv4'
    try: urllib2.urlopen(url)
    except urllib2.HTTPError:
        sts = 1

    if sts == 0:
        # AWSアカウント取得
        url = 'http://169.254.169.254/latest/dynamic/instance-identity/document'
        account_id = json.load(urllib2.urlopen(url))['accountId']

        # バケット名
        bucket_name = 'log-'+ account_id + '-test'

        # S3作成
        s3_conn = boto.s3.connection.S3Connection()
        if bucket_name in s3_conn:
            print "get bucket"
            bucket = s3_conn.get_bucket(bucket_name)
        else:
            print "create bucket"
            bucket = s3_conn.create_bucket(bucket_name,
                               location=Location.APNortheast)
        # ポリシー設定
        policy = S3_POLICY_LOGGING.replace('<BucketName>', bucket_name)\
                                  .replace('<CustomerAccountID>', account_id)\
                                  .replace('<Prefix>/', '')
        bucket.set_policy(policy)

        # ポリシー取得
        bucket_policy = bucket.get_policy()
        print bucket_policy

except:
    # 異常終了
    log_error('Error of the S3 information list.',traceback.format_exc())
