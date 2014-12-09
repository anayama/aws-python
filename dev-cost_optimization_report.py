#!/usr/bin/python
# -*- coding:utf-8 -*-

import sys
import boto.ec2.cloudwatch, boto.ec2.elb, boto.rds
import urllib2, json
import datetime
import traceback

from common import *

# CPU使用率 10%
cpu_utilization = 10
# ネットワークIO 5MB
network_io = 5242880
# 利用頻度の低い期間 4日間
low_period = 4
# アイドル状態の期間 7日間
idle_period = 7

MAIL_MESSAGE = """
【コスト最適化】
不要リソースやアイドル状態のリソースの除外や予約容量の契約など、いかにコストを節約するかが表示されます。

・使用率の低いAmazon EC2 Instances
・アイドル状態の Load Balancer
・利用頻度の低いAmazon EBSボリューム
・関連付けられていない Elastic IP Address
・Amazon RDSアイドル状態のDBインスタンス
"""

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
#  Amazon EC2 軽度利用インスタンス
#############################################################
def low_utilization_ec2(region):
    try:
        ec2_list = []

        end_time = datetime.datetime.now()
        start_time = end_time - datetime.timedelta(weeks=2)

        # CloudWatch
        cw_conn = boto.ec2.cloudwatch.connect_to_region(region)

        # EC2
        ec2_conn = boto.ec2.connect_to_region(region)
        reservations = ec2_conn.get_all_instances()
        for reservation in reservations:
            for instance in reservation.instances:
                cpu_low_count = 0
                nwin_low_count = 0
                nwout_low_count = 0

                # CPU Utilization (Percent)
                cpu_metrics = cw_conn.get_metric_statistics(
                                    86400,
                                    start_time,
                                    end_time,
                                    'CPUUtilization',
                                    'AWS/EC2',
                                    'Average',
                                    dimensions={'InstanceId':instance.id})

                for metric in cpu_metrics:
                    for key,val in metric.iteritems():
                        # CPU使用率が10%以下
                        if key == 'Average' and int(val) <= cpu_utilization:
                            cpu_low_count = cpu_low_count + 1
                    if cpu_low_count >= low_period:
                        break

                # Network In (Bytes)
                nwin_metrics = cw_conn.get_metric_statistics(
                                    86400,
                                    start_time,
                                    end_time,
                                    'NetworkIn',
                                    'AWS/EC2',
                                    'Average',
                                    dimensions={'InstanceId':instance.id})

                for metric in nwin_metrics:
                    for key,val in metric.iteritems():
                        # Network in が5MB以下
                        if key == 'Average' and int(val) <= network_io:
                            nwin_low_count = nwin_low_count + 1
                    if nwin_low_count >= low_period:
                        break

                # Network Out (Bytes)
                nwout_metrics = cw_conn.get_metric_statistics(
                                    86400,
                                    start_time,
                                    end_time,
                                    'NetworkOut',
                                    'AWS/EC2',
                                    'Average',
                                    dimensions={'InstanceId':instance.id})

                for metric in nwout_metrics:
                    for key,val in metric.iteritems():
                        # Network in が5MB以下
                        if key == 'Average' and int(val) <= network_io:
                            nwout_low_count = nwout_low_count + 1
                    if nwout_low_count >= low_period:
                        break

                if cpu_low_count >= low_period and \
                   ( nwin_low_count >= low_period or \
                     nwout_low_count >= low_period):
                    if 'Name' in instance.tags:
                        nametag = instance.tags['Name']
                    else :
                        nametag = 'None'
                    instance_name = instance.id + " (" + nametag + ")"
                    ec2_list.append(instance_name)

        return ec2_list

    except:
        # エラー出力
        log_error('Error of the CloudWatch.',
                  traceback.format_exc())

#############################################################
# 未活用のAmazon EBS ボリューム
#############################################################
def underused_ebs(region):
    try:
        ebs_list = []

        end_time = datetime.datetime.now()
        start_time = end_time - datetime.timedelta(weeks=1)

        # CloudWatch
        cw_conn = boto.ec2.cloudwatch.connect_to_region(region)

        # EBS
        ec2_conn = boto.ec2.connect_to_region(region)
        volumes = ec2_conn.get_all_volumes()
        for volume in volumes:
            if volume.status == 'available':
                ebs_list.append(volume.id)
                print volume.id
            else:
                # VolumeReadOps (Count)
                write_metrics = cw_conn.get_metric_statistics(
                                    86400,
                                    start_time,
                                    end_time,
                                    'VolumeWriteOps',
                                    'AWS/EBS',
                                    'Maximum',
                                    dimensions={'VolumeId':volume.id})

                for metric in write_metrics:
                    for key,val in metric.iteritems():
                        if key == 'Maximum' and int(val) == 0:
                            print volume.id
                            ebs_list.append(volume.id)

        return ebs_list

    except:
        # エラー出力
        log_error('Error of the CloudWatch.',
                  traceback.format_exc())

#############################################################
# 関連付けられていないd Elastic IP アドレス
#############################################################
def underused_eip(region):
    try:
        eip_list = []

        # EC2
        ec2_conn = boto.ec2.connect_to_region(region)
        addresses = ec2_conn.get_all_addresses()
        for address in addresses:
            if address.instance_id is None:
                eip_list.append(address.public_ip)

        return eip_list

    except:
        # エラー出力
        log_error('Error of the CloudWatch.',
                  traceback.format_exc())

#############################################################
# アイドル中のロードバランサー
#############################################################
def idle_elb(region):
    try:
        elb_list = []

        end_time = datetime.datetime.now()
        start_time = end_time - datetime.timedelta(weeks=1)

        # CloudWatch
        cw_conn = boto.ec2.cloudwatch.connect_to_region(region)

        elb_conn = boto.ec2.elb.connect_to_region(region)
        load_balancers = elb_conn.get_all_load_balancers()
        for elb in load_balancers:
            print elb.name

    except:
        # エラー出力
        log_error('Error of the CloudWatch.',
                  traceback.format_exc())

#############################################################
# アイドル中の Amazon RDS DB インスタンス
#############################################################
def idle_rds(region):
    try:
        rds_list = []

        end_time = datetime.datetime.now()
        start_time = end_time - datetime.timedelta(weeks=1)

        # CloudWatch
        cw_conn = boto.ec2.cloudwatch.connect_to_region(region)

        # RDS
        rds_conn = boto.rds.connect_to_region(region)
        instances = rds_conn.get_all_dbinstances()
        for instance in instances:
            no_connect_count = 0

            # DatabaseConnections (Count)
            db_metrics = cw_conn.get_metric_statistics(
                            86400,
                            start_time,
                            end_time,
                            'DatabaseConnections',
                            'AWS/RDS',
                            'Maximum',
                            dimensions={'DBInstanceIdentifier':instance.id})

            for metric in db_metrics:
                for key,val in metric.iteritems():
                    # 直近、1週間コネクションが発生していない
                    if key == 'Maximum'and int(val) == 0:
                        no_connect_count = no_connect_count + 1
  
            if no_connect_count >= idle_period:
                rds_list.append(instance.id)

        return rds_list

    except:
        # エラー出力
        log_error('Error of the CloudWatch.',
                  traceback.format_exc())

#############################################################
#   メイン処理
#############################################################
if __name__ == '__main__':
    try:
        # EIPの割当がない場合は終了
        if not run_check:
            exit(1)

        # リージョン取得
        url = 'http://169.254.169.254/latest/dynamic/instance-identity/document'
        region = json.load(urllib2.urlopen(url))['region']

        # Low Utilization Amazon EC2 Instances
        for instance_name in low_utilization_ec2(region):
            print instance_name

        # Underutilized Amazon EBS Volumes
        for ebs in underused_ebs(region):
            print ebs

        # Unassociated Elastic IP Addresses
        for ip in underused_eip(region):
            print ip

        # Idle Load Balancers
        for els in idle_elb(region):
            print elb

        # Amazon RDS Idle DB Instances
        for instance_name in idle_rds(region):
            print instance_name

    except:
        # 異常終了
        log_info('CloudWatch abnormal termination')
        # エラー出力
        log_error('Error of the CloudWatch.',traceback.format_exc())

