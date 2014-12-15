#!/usr/bin/python
# -*- coding:utf-8 -*-
# -*- mode: python; -*-

import os, sys
import boto.ec2
import urllib2, json
import ConfigParser
import traceback

# 共通
from common import *
# バックアップ機能
from backup_error import *

# 定義ファイルの取込み
path = os.environ["PYTHONPATH"]
USER = os.path.join(path,'user.conf')
config = ConfigParser.RawConfigParser()
config.read(USER)
GENERATION = config.get('backup','generation_count')

class EC2BackupInfo:
#############################################################
#   AWSメタデータの取得
#############################################################
    def __init__(self):
        # インスタンスID取得
        url = 'http://169.254.169.254/latest/meta-data/instance-id'
        self.my_instance = urllib2.urlopen(url).read()

        # リージョン取得
        url = 'http://169.254.169.254/latest/dynamic/instance-identity/document'
        self.my_region = json.load(urllib2.urlopen(url))['region']

#############################################################
#   EC2インスタンス情報の取得
#############################################################
    def get_ec2(self):
        try:
            self.conn = boto.ec2.connect_to_region(self.my_region)
            reservations = self.conn.get_all_instances(instance_ids=self.my_instance)

            # EC2情報が複数の場合はエラー
            if len(reservations) != 1 :
                raise AwsError

            for reservation in reservations:
                for instance in reservation.instances:
                    # カーネルID
                    if not instance.kernel is None:
                        self.kernel_id = instance.kernel
                    else :
                        self.kernel_id = ''

                    # RAMディスクID
                    if not instance.ramdisk is None:
                        self.ramdisk_id = instance.ramdisk
                    else :
                        self.ramdisk_id = ''

                    # Nameタグ
                    if 'Name' in instance.tags:
                        self.ec2_nametag = instance.tags['Name']
                    else :
                        self.ec2_nametag = ''

                    # EBSボリュームID
                    block_device = instance.block_device_mapping
                    self.ebs = {}
                    for key,value in block_device.iteritems():
                        self.ebs[key] = value.volume_id

        except AwsError:
            # エラー出力
            log_error('There is more than one EC2 instance information.',
                      traceback.format_exc())
            raise
        except:
            # エラー出力
            log_error('Failed to get ec2 instance information.',
                      traceback.format_exc())
            raise

#############################################################
#   EBSのNameタグを取得
#############################################################
    def get_ebs_tag(self, volid):
        # EBSタグが複数の場合はエラー
        if len(self.conn.get_all_volumes([volid])) != 1 :
            log_error('There is more than one EBS information.',
                      traceback.format_exc())
            raise AwsError

        # EBSタグの取得
        volumes = self.conn.get_all_volumes([volid])[0]
        return str(volumes.tags.get('Name'))

#############################################################
#   スナップショット作成
#############################################################
    def ebs2snapshot(self, keyVolumeId):
        try:
            ebs = self.conn.get_all_volumes([keyVolumeId])[0]
            # EBSスナップショットの作成
            snapshot = ebs.create_snapshot('Auto Backup')
            # タグ付与
            self.conn.create_tags([snapshot.id],
                         {'Name': self.ec2_nametag,
                          'Kernel ID': self.kernel_id,
                          'RAM Disk ID': self.ramdisk_id})
            return 0

        except:
            # エラー出力
            log_error('Failed to create snapshot.' +
                      ' ec2tag=' + self.ec2_nametag +
                      ' volumeid=' + keyVolumeId +
                      ' snapshotid=' + snapshot.id ,
                      traceback.format_exc())
            return -1

#############################################################
#   スナップショットのローテート処理
#############################################################
    def snaprotate(self, keyVolumeId):
        try: max_generation = int(GENERATION)
        except: max_generation = 3

        try:
            # EBSボリュームIDをキーに、スナップショットIDを取得
            snapshot = {}
            for snapshots in self.conn.get_all_snapshots():
                # EBSボリュームIDで比較
                if snapshots.volume_id == keyVolumeId and \
                   snapshots.description == 'Auto Backup' and \
                   snapshots.tags.get('Name') == self.ec2_nametag:
                    snapshot.update({snapshots.id:snapshots.start_time})

            # ソート処理(作成日付の降順)
            snapshot = sorted(snapshot.items(),
                       key=lambda (id, date): (date, id),
                       reverse=True)

            # ログローテート（最新3世代以前を削除）
            for i in range(max_generation, len(snapshot)):
                try: self.conn.delete_snapshot(snapshot[i][0])
                except: continue

            return 0

        except:
            # エラー出力
            log_error('Fail to rotate snapshot.'
                      ' ec2=' + self.ec2_nametag +
                      ' volumeid=' + keyVolumeId ,
                      traceback.format_exc())
            return -1

#if __name__ == '__main__':
#    try:
#        ec2info = EC2BackupInfo()
#    except:
#        # エラー出力
#        log_error('Ec2Info class error',
#                  traceback.format_exc())
