#!/usr/bin/python
# -*- coding:utf-8 -*-

import sys
import boto.cloudtrail, boto.s3.connection, boto.sns, boto.sqs
import urllib2, json
import time
import traceback

from boto.s3.connection import Location

# 共通
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
                    "arn:aws:iam::113285607260:root",
                    "arn:aws:iam::035351147821:root"
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
                    "arn:aws:iam::113285607260:root",
                    "arn:aws:iam::035351147821:root"
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

SNS_TOPIC_POLICY = """{
  "Version": "2008-10-17",
  "Id": "__default_policy_ID",
  "Statement": [
    {
      "Sid": "__default_statement_ID",
      "Effect": "Allow",
      "Principal": {
        "AWS": "*"
      },
      "Action": [
        "SNS:Publish",
        "SNS:RemovePermission",
        "SNS:SetTopicAttributes",
        "SNS:DeleteTopic",
        "SNS:ListSubscriptionsByTopic",
        "SNS:GetTopicAttributes",
        "SNS:Receive",
        "SNS:AddPermission",
        "SNS:Subscribe"
      ],
      "Resource": "arn:aws:sns:<AWSRegion>:<CustomerAccountID>:<SNSTopicName>",
      "Condition": {
        "StringEquals": {
          "AWS:SourceOwner": "<CustomerAccountID>"
        }
      }
    },
    {
      "Sid": "AWSCloudTrailSNSPolicy20140219",
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
          "arn:aws:iam::113285607260:root",
          "arn:aws:iam::035351147821:root"
        ]
      },
      "Resource": "arn:aws:sns:<AWSRegion>:<CustomerAccountID>:<SNSTopicName>",
      "Action": "SNS:Publish"
    }
  ]
}"""

SQS_SUBSCRIBE_TOPIC_BEGIN = """{
  "Version": "2008-10-17",
  "Id": "AWSCloudTrailSQSPolicy",
  "Statement": ["""

SQS_SUBSCRIBE_TOPIC = """
    {
      "Sid": "Sid123456789012<SerialNumber>",
      "Effect": "Allow",
      "Principal": {
        "AWS": "*"
      },
      "Action": "SQS:SendMessage",
      "Resource": "arn:aws:sqs:<AWSRegion>:<CustomerAccountID>:<SQSQueueName>",
      "Condition": {
        "ArnEquals": {
          "aws:SourceArn": "arn:aws:sns:<AWSRegion>:<CustomerAccountID>:<SNSTopicName>"
        }
      }
    }"""

SQS_SUBSCRIBE_TOPIC_END = """
  ]
}"""

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
#   リージョン一覧取得
#############################################################
def get_regions():
    region_range = []
    try:
        for region in boto.cloudtrail.regions():
            # Govと北京は除外
            if not region.name == "cn-north-1" and \
               not region.name == "us-gov-west-1":
                region_range.append(region.name)
        return region_range
    except:
        return region_range

#############################################################
#   CloudTrail初期化処理
#############################################################
def init_cloudtrail():
    try:
        for region in get_regions():
            cloudtrail_conn = boto.cloudtrail.connect_to_region(region)
            cloudtrail_list = cloudtrail_conn.describe_trails()
            for cloudtrail in cloudtrail_list["trailList"]:
                cloudtrail_name = cloudtrail['Name']
                if "SnsTopicName" in cloudtrail:
                    topic_name = cloudtrail['SnsTopicName']
                else:
                    topic_name = None

                # CloudTrail削除
                cloudtrail_conn.delete_trail(name=cloudtrail_name)

                if not topic_name is None:
                    delete_sns(topic_name, region)

    except:
        # エラー出力
        log_error('Error of the CloudTrail Setting. - init_cloudtrail()',
                  traceback.format_exc())

#############################################################
#   SNS初期化
#############################################################
def delete_sns(topic_name, region):
    try:
        # SNS
        sns_conn = boto.sns.connect_to_region(region)
        all_topics = sns_conn.get_all_topics()
        topics = all_topics["ListTopicsResponse"]\
                           ["ListTopicsResult"]["Topics"]
        for topic in topics:
            topic_arn = topic["TopicArn"]
            if topic_name in topic_arn:
                all_subs = sns_conn.get_all_subscriptions_by_topic(topic_arn)
                subscripts = all_subs["ListSubscriptionsByTopicResponse"]\
                                     ["ListSubscriptionsByTopicResult"]\
                                     ["Subscriptions"]
                for subscript in subscripts:
                    subscript_arn = subscript["SubscriptionArn"]

                    # Subscription削除
                    sns_conn.unsubscribe(subscript_arn)

                # Topic削除
                sns_conn.delete_topic(topic_arn)

    except:
        # エラー出力
        log_error('Error of the CloudTrail Setting. - delete_sns()',
                  traceback.format_exc())

#############################################################
#   CloudTrail作成
#############################################################
def do_cloudtrail():
    try:
        # CloudTrail設定名
        cloudtrail_name = 'cloudtrail'

        url = 'http://169.254.169.254/latest/dynamic/instance-identity/document'
        # AWSアカウント取得
        account_id = json.load(urllib2.urlopen(url))['accountId']
        # リージョン取得
        region = json.load(urllib2.urlopen(url))['region']
        # S3バケット名
        bucket_name = 'log-'+ account_id

        # S3作成
        s3_conn = boto.s3.connection.S3Connection()
        if bucket_name in s3_conn:
            bucket = s3_conn.get_bucket(bucket_name)
        else:
            bucket = s3_conn.create_bucket(bucket_name,
                               location=Location.APNortheast)

        s3_policy = S3_POLICY_LOGGING\
                              .replace('<BucketName>', bucket_name)\
                              .replace('<CustomerAccountID>', account_id)\
                              .replace('<Prefix>/', '')
        bucket.set_policy(s3_policy)

        #SQS作成(本アプリの実行リージョン)
        sqs_conn = boto.sqs.connect_to_region(region)
        queue = sqs_conn.create_queue(cloudtrail_name)
        sqs_policy = SQS_SUBSCRIBE_TOPIC_BEGIN

        # リージョン一覧
        count = 0
        for region in get_regions():
            # SNS作成
            sns_conn = boto.sns.connect_to_region(region)
            sns_topic = sns_conn.create_topic(cloudtrail_name)
            topic_arn = sns_topic["CreateTopicResponse"]\
                                 ["CreateTopicResult"]\
                                 ["TopicArn"]
            sns_conn.subscribe_sqs_queue(topic_arn, queue)

            sns_policy = SNS_TOPIC_POLICY\
                                 .replace('<SNSTopicName>', cloudtrail_name)\
                                 .replace('<CustomerAccountID>', account_id)\
                                 .replace('<AWSRegion>', region)
            sns_conn.set_topic_attributes(topic_arn, "Policy", sns_policy)

            # CloudTrail設定
            cloudtrail_conn = boto.cloudtrail.connect_to_region(region)
            cloudtrail = cloudtrail_conn.create_trail(name=cloudtrail_name,
                                       s3_bucket_name=bucket_name,
                                       sns_topic_name=cloudtrail_name)
            cloudtrail = cloudtrail_conn.start_logging(name=cloudtrail_name)

            # SQS Subscription Policy 追加編集
            if count > 0:
                sqs_policy = sqs_policy + ","

            sqs_policy = sqs_policy + SQS_SUBSCRIBE_TOPIC\
                                .replace('<SNSTopicName>', cloudtrail_name)\
                                .replace('<SQSQueueName>', cloudtrail_name)\
                                .replace('<CustomerAccountID>', account_id)\
                                .replace('<AWSRegion>', region)\
                                .replace('<SerialNumber>', str(count))
            count = count + 1
            print region + " Succeed CloudTrail!"

        # Subscription Queue 追加
        sqs_policy = sqs_policy + SQS_SUBSCRIBE_TOPIC_END
        queue.set_attribute('Policy', sqs_policy)

    except:
        # エラー出力
        log_error('Error of the CloudTrail Setting. - do_cloudtrail()',
                  traceback.format_exc())

#############################################################
#   CloudTrail結果表示
#############################################################
def describe_cloudtrail():
    try:
        print "----------------------------------------"

        # CloudTrail
        count = 1
        for region in get_regions():
            print str(count) + ". " + region
            cloudtrail_conn = boto.cloudtrail.connect_to_region(region)
            cloudtrail_list = cloudtrail_conn.describe_trails()
            for cloudtrail in cloudtrail_list["trailList"]:
                cloudtrail_name = cloudtrail['Name']
                status = cloudtrail_conn.get_trail_status(name=cloudtrail_name)
                bucket_name = cloudtrail['S3BucketName']
                if "SnsTopicName" in cloudtrail:
                    topic_name = cloudtrail['SnsTopicName']
                else:
                    topic_name = None

                print "   Logging:        " + str(status['IsLogging'])
                print "   S3 bucket:      " + bucket_name
                print "   SNS Topic:      " + topic_name

            count = count + 1

    except:
        # エラー出力
        log_error('Error of the CloudTrail Setting. - describe_cloudtrail()',
                  traceback.format_exc())

#############################################################
#   メイン処理
#############################################################
if __name__ == '__main__':
    try:
        # EIPの割当がない場合は終了
        if not run_check:
            exit(1)

        # 開始メッセージ
        log_info('CloudTrail setting start')
        print "CloudTrail setting start."
        # 初期化
        init_cloudtrail()
        # CloudTral設定
        do_cloudtrail()
        # 設定確認
        describe_cloudtrail()
        # 終了メッセージ
        print "CloudTrail setting successful."
        log_info('CloudTrail setting successful')

    except:
        # 異常終了
        print "CloudTrail abnormal termination."
        log_info('CloudTrail abnormal termination')
        # エラー出力
        log_error('Error of the CloudTrail Setting.',traceback.format_exc())
