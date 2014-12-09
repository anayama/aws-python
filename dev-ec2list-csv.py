#!/usr/bin/python
# -*- coding:utf-8 -*-

import sys
import boto.ec2
import urllib2
import csv
import traceback

from common import *

CSV_FILE = 'dev-ec2list-csv.py'

try:
    sts = 0
    # EIP有無チェック
    url = 'http://169.254.169.254/latest/meta-data/public-ipv4'
    try: urllib2.urlopen(url)
    except urllib2.HTTPError:
        sts = 1

    if sts == 0:
        # CSV生成
        writecsv = csv.writer(file(CSV_FILE, 'w'), lineterminator='\n')
        writecsv.writerow([
            'Instance',
            'Tag',
            'Instance Type',
            'Elastic IP',
            'Private IPs',
            'Key Pair Name',
            'Kernel ID',
            'RAM Disk ID',
            'State' ])

        # リージョン取得
        regions = boto.ec2.regions()
        for region in regions:
            # Govと北京は除外
            if region.name == "cn-north-1" or region.name == "us-gov-west-1":
                continue

            print "Region: " + region.name

            # EC2インスタンス
            conn = region.connect()
            instances = conn.get_all_instances()
            for ec2 in instances:
                for instance in ec2.instances:
                    if instance.id != None :
                        print "    Instance ID:" + str(instance.id)
                        if 'Name' in instance.tags and \
                           len(instance.tags['Name']) > 0:
                            name_tag = instance.tags['Name'].encode('utf8')
                        else:
                            name_tag = 'None'
                        writecsv.writerow([
                            instance.id,
                            name_tag,
                            instance.instance_type,
                            instance.private_ip_address,
                            instance.ip_address,
                            instance.key_name,
                            instance.kernel,
                            instance.ramdisk,
                            instance.state ])

except:
    # 異常終了
    log_error('Error of the EC2 information list.',traceback.format_exc())
