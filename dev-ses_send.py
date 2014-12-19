#!/usr/bin/python
# -*- coding:utf-8 -*-

import sys
import boto.ses
import urllib2, json
import ConfigParser
import traceback

from common import *

# 定義ファイルの取込み
path = os.environ["PYTHONPATH"]
DEV = os.path.join(path,'development.conf')
config = ConfigParser.RawConfigParser()
config.read(DEV)
REGION = config.get('ses','region')
FROM_MAIL = config.get('ses','from_address')
TO_MAIL = config.get('ses','to_address')

try:
    sts = 0
    # EIP有無チェック
    url = 'http://169.254.169.254/latest/meta-data/public-ipv4'
    try: urllib2.urlopen(url)
    except urllib2.HTTPError:
        sts = 1

    if sts == 0:
        # リージョン取得
        ses_region = 'us-east-1'
        for region in boto.ses.regions():
            if REGION in region.name:
                ses_region = REGION

        # SES
        ses_conn = boto.ses.connect_to_region(ses_region)
        addresses = ses_conn.list_verified_email_addresses()
        address = addresses["ListVerifiedEmailAddressesResponse"]\
                                ["ListVerifiedEmailAddressesResult"]\
                                ["VerifiedEmailAddresses"]
        if TO_MAIL in address and FROM_MAIL in address:
            print FROM_MAIL, TO_MAIL
#           ses_conn.send_email(FROM_MAIL,
#                               '[AWS]SES Send a Test Email',
#                               'Python SDK からのテストメールを送信します',
#                               TO_MAIL)

except:
    # 異常終了
    log_error('Error of the SES.',traceback.format_exc())
