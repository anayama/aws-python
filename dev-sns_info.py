#!/usr/bin/python
# -*- coding:utf-8 -*-

import sys
import boto.sns
import urllib2, json
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
        # リージョン取得
        url = 'http://169.254.169.254/latest/dynamic/instance-identity/document'
        region = json.load(urllib2.urlopen(url))['region']

        # SNS
        sns_conn = boto.sns.connect_to_region(region)

        all_topics = sns_conn.get_all_topics()
        topics = topics = all_topics["ListTopicsResponse"]\
                                    ["ListTopicsResult"]\
                                    ["Topics"]
        for topic in topics:
            topic_attr = sns_conn.get_topic_attributes(topic["TopicArn"])
            print topic_attr["GetTopicAttributesResponse"]\
                            ["GetTopicAttributesResult"]\
                            ["Attributes"]\
                            ["TopicArn"]
            print topic_attr["GetTopicAttributesResponse"]\
                            ["GetTopicAttributesResult"]\
                            ["Attributes"]["Policy"]

except:
    # 異常終了
    log_error('Error of the SNS.',traceback.format_exc())
