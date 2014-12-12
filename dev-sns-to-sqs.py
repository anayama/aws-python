#!/usr/bin/python
# -*- coding:utf-8 -*-

import sys
import boto.sns, boto.sqs
import urllib2, json
import traceback

from common import *

stack_name = 'aws-python-demo'

SQS_SUBSCRIBE_TOPIC_BEGIN = """{
  "Version": "2008-10-17",
  "Id": "arn:aws:sqs:<AWSRegion>:<CustomerAccountID>:<SQSQueueName>/SQSDefaultPolicy",
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

def get_aws_account():
    try:
        url = 'http://169.254.169.254/latest/dynamic/instance-identity/document'
        return json.load(urllib2.urlopen(url))['accountId']
    except:
        return None

def get_region():
    try:
        url = 'http://169.254.169.254/latest/dynamic/instance-identity/document'
        return json.load(urllib2.urlopen(url))['region']
    except:
        return None

def get_regions():
    region_range = []
    try:
        regions = boto.sqs.regions()
        for region in regions:
            # Govと北京は除外
            if not region.name == "cn-north-1" and \
               not region.name == "us-gov-west-1":
                region_range.append(region.name)
        return region_range
    except:
        return region_range

def create_sns_sqs():
    try:
        # SQS
        sqs_conn = boto.sqs.connect_to_region(get_region())
        queue = sqs_conn.create_queue(stack_name)

        # Policy
        policy = SQS_SUBSCRIBE_TOPIC_BEGIN

        # リージョン一覧
        count = 0
        for region in get_regions():
            print region

            # SNS
            sns_conn = boto.sns.connect_to_region(region)

            sns_topic = sns_conn.create_topic(stack_name)
            topic_arn = sns_topic["CreateTopicResponse"]\
                                 ["CreateTopicResult"]\
                                 ["TopicArn"]
            sns_conn.subscribe_sqs_queue(topic_arn, queue)

            # Policy
            if count > 0:
                policy = policy + ","

            policy = policy + SQS_SUBSCRIBE_TOPIC\
                            .replace('<SNSTopicName>', stack_name)\
                            .replace('<SQSQueueName>', stack_name)\
                            .replace('<CustomerAccountID>', get_aws_account())\
                            .replace('<AWSRegion>', region)\
                            .replace('<SerialNumber>', str(count))
            count = count + 1

        # SQS
        policy = policy + SQS_SUBSCRIBE_TOPIC_END
        queue.set_attribute('Policy', policy)

    except:
        # エラー出力
        log_error('Error of the XXX.',traceback.format_exc())

def delete_sns_sqs():
    try:
        # SQS
        sqs_conn = boto.sqs.connect_to_region(get_region())

        # リージョン一覧
        for region in get_regions():
            print region

            # SNS
            sns_conn = boto.sns.connect_to_region(region)
            all_topics = sns_conn.get_all_topics()
            topics = topics = all_topics["ListTopicsResponse"]\
                                        ["ListTopicsResult"]\
                                        ["Topics"]

            for topic in topics:
                topic_arn = topic["TopicArn"]

                # 対象SNSの絞込み
                if stack_name in topic_arn:
                    all_subs = sns_conn.get_all_subscriptions_by_topic(topic_arn)
                    subscripts = all_subs["ListSubscriptionsByTopicResponse"]\
                                         ["ListSubscriptionsByTopicResult"]\
                                         ["Subscriptions"]
                    for subscript in subscripts:
                        subscript_arn = subscript["SubscriptionArn"]
                        # Delete Subscription
                        sns_conn.unsubscribe(subscript_arn)

                    # Delete Topic
                    sns_conn.delete_topic(topic["TopicArn"])

        # SQS
        queue = sqs_conn.get_queue(stack_name)
        sqs_conn.delete_queue(queue)

    except:
        # エラー出力
        log_error('Error of the XXX.',traceback.format_exc())

def describe_sns_sqs():
    try:
        # SQS
        sqs_conn = boto.sqs.connect_to_region(get_region())
        queue = sqs_conn.get_queue(stack_name)
        queue_attr = queue.get_attributes()
        print "SQS: " + queue_attr["QueueArn"]

        # リージョン一覧
        for region in get_regions():
            print "Region: " + region

            # SNS
            sns_conn = boto.sns.connect_to_region(region)

            all_topics = sns_conn.get_all_topics()
            topics = topics = all_topics["ListTopicsResponse"]\
                                        ["ListTopicsResult"]\
                                        ["Topics"]
            for topic in topics:
                topic_arn = topic["TopicArn"]

                # 対象SNSの絞込み
                if stack_name in topic_arn:
                    print "  SNS Topic: " + topic_arn
                    all_subs = sns_conn.get_all_subscriptions_by_topic(topic_arn)
                    subscripts = all_subs["ListSubscriptionsByTopicResponse"]\
                                         ["ListSubscriptionsByTopicResult"]\
                                         ["Subscriptions"]
                    for subscript in subscripts:
                        print "  SNS Sub:   " + subscript["SubscriptionArn"]

    except:
        # エラー出力
        log_error('Error of the XXX.',traceback.format_exc())

if __name__ == '__main__':
    # 引数取得
    argv = sys.argv
    argc = len(argv)
        
    if argc != 2:
        print "Usage: python %s {crt|del|info}" %argv[0]
        exit(1)
    proc = argv[1]

    try:
        # EIPの割当がない場合は終了
        if not run_check:
            exit(1)

        if proc == 'crt':
            create_sns_sqs()
        if proc == 'del':
            delete_sns_sqs()
        if proc == 'info':
            describe_sns_sqs()

    except:
        # 異常終了
        log_error('Error of the SNS and SQS Creating.',traceback.format_exc())
