#!/usr/bin/python
# -*- coding:utf-8 -*-

import sys
import boto.ec2
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

        # EC2インスタンス
        conn = boto.ec2.connect_to_region(region)
        reservations = conn.get_all_instances()
        for reservation in reservations:
            for instance in reservation.instances:
                print "Instance: " + instance.private_ip_address
                print instance.spot_instance_request_id
                print "  root_device_type: " + instance.root_device_type

                for key,value in instance.tags.iteritems():
                    print "  " + key + ": " + value

                block_device = instance.block_device_mapping
                for key,value in block_device.iteritems():
                    # EBSボリュームIDの取得
                    print "  volume_id: " + value.volume_id

except:
    # エラー出力
    log_error('Error of the EC2 information detail.',traceback.format_exc())
