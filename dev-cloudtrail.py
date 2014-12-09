#!/usr/bin/python
# -*- coding:utf-8 -*-

import sys
import boto.cloudtrail, boto.sns, boto.sqs, boto.s3.connection
import urllib2, json
import traceback

from boto.cloudtrail.exceptions import TrailNotFoundException

from common import *

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

def get_s3bucket():
    try:
        # メタデータ取得
        url = 'http://169.254.169.254/latest/dynamic/instance-identity/document'
        account_id = json.load(urllib2.urlopen(url))['accountId']
        return 'log-' + account_id
    except:
        return None

def get_regions():
    region_range = []
    try:
        regions = boto.s3.regions()
        for region in regions:
            # Govと北京は除外
            if not region.name == "cn-north-1" and \
               not region.name == "us-gov-west-1":
                region_range.append(region.name)
        return region_range
    except:
        return region_range

def get_cloudtrail(region):
    try:
        # CloudTrail
        cloudtrail_conn = boto.cloudtrail.connect_to_region(region)
        cloudtrail_list = cloudtrail_conn.describe_trails()
        for cloudtrail in cloudtrail_list["trailList"]:
            cloudtrail_name = cloudtrail['Name']
            bucket_name = cloudtrail['S3BucketName']
            if "SnsTopicName" in cloudtrail:
                topic_name = cloudtrail['SnsTopicName']
            else:
                topic_name = None
            status = cloudtrail_conn.get_trail_status(name=cloudtrail_name)

            print "   Logging:        " + str(status['IsLogging'])
            print "   CloudTrail:     " + cloudtrail_name
            print "   S3 bucket:      " + bucket_name

            # SNS
            if not topic_name is None:
                get_sns(topic_name, region)

            # SQS
            get_sqs(cloudtrail_name, region)

    except:
        # エラー出力
        log_error('Error of the CloudTrail get_cloudtrail.',traceback.format_exc())

def get_sns(topic_name, region):
    try:
        # SNS
        sns_conn = boto.sns.connect_to_region(region)
        all_topics = sns_conn.get_all_topics()
        topics = all_topics["ListTopicsResponse"]\
                           ["ListTopicsResult"]["Topics"]
        for topic in topics:
            topic_arn = topic["TopicArn"]
            if topic_name in topic_arn:
                print "   SNS Topic:      " + topic_name

    except:
        # エラー出力
        log_error('Error of the CloudTrail get_sns.',traceback.format_exc())

def get_sqs(queue_name, region):
    try:
        # SQS
        sqs_conn = boto.sqs.connect_to_region(region)
        try: queue = sqs_conn.get_queue(queue_name)
        except: queue = None

        if not queue is None:
            queue_attributes = sqs_conn.get_queue_attributes(queue)
            print "   SQS Queue:      " + queue_attributes["QueueArn"]

    except:
        # エラー出力
        log_error('Error of the CloudTrail get_sqs.',traceback.format_exc())

def del_cloudtrail(region):
    try:
        # CloudTrail
        cloudtrail_conn = boto.cloudtrail.connect_to_region(region)
        cloudtrail_list = cloudtrail_conn.describe_trails()
        for cloudtrail in cloudtrail_list["trailList"]:
            cloudtrail_name = cloudtrail['Name']
            if "SnsTopicName" in cloudtrail:
                topic_name = cloudtrail['SnsTopicName']
            else:
                topic_name = None

            # 削除
            cloudtrail_conn.delete_trail(name=cloudtrail_name)

            # SNS
            if not topic_name is None:
                del_sns(topic_name, region)

            # SQS
            del_sqs(cloudtrail_name, region)

    except:
        # エラー出力
        log_error('Error of the CloudTrail del_cloudtrail.',traceback.format_exc())

def del_sns(topic_name, region):
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
        log_error('Error of the CloudTrail del_sns.',traceback.format_exc())

def del_sqs(queue_name, region):
    try:
        # SQS
        sqs_conn = boto.sqs.connect_to_region(region)
        try: queue = sqs_conn.get_queue(queue_name)
        except: queue = None

        if not queue is None:
            sqs_conn.delete_queue(queue)

    except:
        # エラー出力
        log_error('Error of the CloudTrail del_sqs.',traceback.format_exc())

if __name__ == '__main__':
    # 引数取得
    argv = sys.argv
    argc = len(argv)

    if argc != 2:
        print "Usage: python %s {del|info}" %argv[0]
        exit(1)
    proc = argv[1]

    try:
        # EIPの割当がない場合は終了
        if not run_check:
            exit(1)

        # S3
        s3_conn = boto.s3.connection.S3Connection()
        bucket_name = get_s3bucket()
        if bucket_name in s3_conn:
            print "S3: " + bucket_name
            print "----------------------------------------"

        count = 1
        for region in get_regions():
            print str(count) + ". " + region
            if proc == 'info':
                get_cloudtrail(region)
            if proc == 'del':
                del_cloudtrail(region)
            count = count + 1

    except:
        # 異常終了
        log_error('Error of the CloudTrail',traceback.format_exc())
