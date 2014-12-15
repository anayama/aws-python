#!/usr/bin/python
# -*- coding:utf-8 -*-

import sys
import datetime

# 共通
from common import *
# バックアップ機能
from backup_ec2info import *
import backup_check as check

#############################################################
#   自動バックアップ機能 メイン処理
#############################################################

# 排他制御の開始
backup_on = check.do_backup()

if backup_on:
    # 開始メッセージ
    log_info('Automatic backup start')

    # EC2情報の取得
    ec2backup = EC2BackupInfo()
    ec2backup.get_ec2()

    sts = 0
    # EBS情報の取得
    for device,volid in ec2backup.ebs.iteritems():
        ebstag = ''
        try:
            # EBSタグの取得
            ebstag = ec2backup.get_ebs_tag(volid)
        except AwsError: pass
        except:
            log_error('Failed to get EBS tags' +
                      ' instanceid=' + ec2backup.instance_id +
                      ' ec2tag=' + ec2backup.ec2_nametag +
                      ' device=' + device +
                      ' volumeid=' + volid ,
                      traceback.format_exc())

        # バックアップ対象外
        if ebstag.lower().strip() == "disabled":
            continue
        # スナップショット取得
        sts = ec2backup.ebs2snapshot(volid)
        if sts != 0:
            break
        # ローテート処理
        sts = ec2backup.snaprotate(volid)
        if sts != 0:
            break

    # 正常終了
    if sts == 0:
        # 実行結果の保存
        check.record_backup(datetime.datetime.now())
        # 終了メッセージ
        log_info('Automatic backup was successful')
    # 異常終了
    else :
        log_info('Automatic backup failed')

# 排他制御の解除
check.undo_backup()
