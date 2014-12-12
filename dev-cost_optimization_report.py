#!/usr/bin/python
# -*- coding:utf-8 -*-

import sys
import boto.ec2.cloudwatch, boto.ec2.elb, boto.rds
import urllib2, json
import datetime
import traceback

from common import *

# 定義ファイルの取込み
path = os.environ["PYTHONPATH"]
USER = os.path.join(path,'user.conf')

config = ConfigParser.RawConfigParser()
config.read(USER)
EC2CPU = int(config.get('optimization','ec2_cpu_utilization'))
EC2PERIOD = int(config.get('optimization','ec2_low_period'))
EBSIOPS = int(config.get('optimization','ebs_max_iops'))
ELBREQ = int(config.get('optimization','elb_few_request'))
RDSPERIOD = int(config.get('optimization','rds_idle_period'))

MAIL_MESSAGE = """
【コスト最適化】
 不要リソースやアイドル状態など、コストを節約できるリソースは下記のとおりです。

1. 使用率の低いAmazon EC2 Instances
<EC2-LowUtilization>
2. アイドル状態の Load Balancer
<ELB-Idle>
3. 利用頻度の低いAmazon EBSボリューム
<EBS-Underutilized>
4. 関連付けられていない Elastic IP Address
<EIP-Unassociated>
5. Amazon RDSアイドル状態のDBインスタンス
<RDS-Idle>
"""

# EC2とNameタグの対比表
ec2_tags = {}

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
                # マッピング表
                if 'Name' in instance.tags:
                    nametag = instance.tags['Name']
                else :
                    nametag = 'None'

                ec2_tags[instance.id] = nametag

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
                        if key == 'Average' and int(val) <= EC2CPU:
                            cpu_low_count = cpu_low_count + 1
                    if cpu_low_count >= EC2PERIOD:
                        break

                if cpu_low_count >= EC2PERIOD:
                    instance_name = instance.id + " / " \
                                  + ec2_tags[instance.id] + " (" \
                                  + instance.instance_type + ")"
                    ec2_list.append(instance_name)

        return ec2_list

    except:
        # エラー出力
        log_error('Error of the CloudWatch. - low_utilization_ec2()',
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
        # EC2/EBS
        ec2_conn = boto.ec2.connect_to_region(region)

        volumes = ec2_conn.get_all_volumes()
        for volume in volumes:
            volume_low_count = 0
            if volume.status == 'available':
                volume_low_count = 1
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
                        if key == 'Maximum' and int(val) <= EBSIOPS:
                            volume_low_count = volume_low_count + 1
            if volume_low_count >= 1:
                volume_name = volume.id + " / " \
                        + ec2_tags[volume.attach_data.instance_id] + " (" \
                        + volume.type + " - " + str(volume.size) + "GB)"
                ebs_list.append(volume_name)

        return ebs_list

    except:
        # エラー出力
        log_error('Error of the CloudWatch. - underused_ebs()',
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
        log_error('Error of the CloudWatch. - underused_eip()',
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
        # EC2/ELB
        elb_conn = boto.ec2.elb.connect_to_region(region)
        loadbalancers = elb_conn.get_all_load_balancers()

        for loadbalancer in loadbalancers:
            health_count = 0
            few_request_count = 0
            for instances in loadbalancer.get_instance_health():
                # バックエンドインスタンスの確認
                if instances.state == "InService":
                    health_count = health_count + 1
            # リクエスト数が少ない
            if health_count >= 1:
                # DatabaseConnections (Count)
                lb_metrics = cw_conn.get_metric_statistics(
                            86400,
                            start_time,
                            end_time,
                            'RequestCount',
                            'AWS/ELB',
                            'Maximum',
                            dimensions={'LoadBalancerName':loadbalancer.name})

                for metric in lb_metrics:
                    for key,val in metric.iteritems():
                        # コネクションが発生していない
                        if key == 'Maximum'and int(val) <= ELBREQ:
                            few_request_count = few_request_count + 1

            if health_count == 0 or few_request_count >= 1:
                elb_name = loadbalancer.name + " (Instance Count: " \
                         + str(health_count) + ")"
                elb_list.append(elb_name)

        return elb_list

    except:
        # エラー出力
        log_error('Error of the CloudWatch. - idle_elb()',
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
                    # コネクションが発生していない
                    if key == 'Maximum'and int(val) == 0:
                        no_connect_count = no_connect_count + 1

            if no_connect_count >= RDSPERIOD:
                instance_name = instance.id + " - " + instance.instance_class +\
                    " (" + instance.engine + " " + instance.engine_version + ")"
                rds_list.append(instance_name)

        return rds_list

    except:
        # エラー出力
        log_error('Error of the CloudWatch. - idle_rds()',
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
        mes_ec2 = ""
        for ec2instance in low_utilization_ec2(region):
            mes_ec2 = mes_ec2 + "  " + ec2instance + "\n"

        # Underutilized Amazon EBS Volumes
        mes_ebs = ""
        for ebsvolume in underused_ebs(region):
            mes_ebs = mes_ebs + "  " + ebsvolume + "\n"

        # Unassociated Elastic IP Addresses
        mes_eip = ""
        for ipaddress in underused_eip(region):
            mes_eip = mes_eip + "  " + ipaddress + "\n"

        # Idle Load Balancers
        mes_elb = ""
        for loadbalancer in idle_elb(region):
            mes_elb = mes_elb + "  " + loadbalancer + "\n"

        # Amazon RDS Idle DB Instances
        mes_rds = ""
        for rdsinstance in idle_rds(region):
            mes_rds = mes_rds + "  " + rdsinstance + "\n"

        message = MAIL_MESSAGE.decode('utf-8')\
                     .replace('<EC2-LowUtilization>', mes_ec2)\
                     .replace('<EBS-Underutilized>', mes_ebs)\
                     .replace('<EIP-Unassociated>', mes_eip)\
                     .replace('<ELB-Idle>', mes_elb)\
                     .replace('<RDS-Idle>', mes_rds)
        print message

    except:
        # 異常終了
        log_info('CloudWatch abnormal termination')
        # エラー出力
        log_error('Error of the CloudWatch.',traceback.format_exc())

