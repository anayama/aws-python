aws-python
==========

## 設定ファイル

### Python環境設定

~~~
/apps/admin/conf/python.env
~~~

| セクション | パラメータ | 説明 | デフォルト |
| -------- | ----------- | ---- | ----------- |
|なし| PYTHONPATH | 設定ファイル群のディレクトリパスを指定 | /apps/admin/conf |

### 共通パラメータ

~~~
/apps/admin/conf/common.conf
~~~

| セクション | パラメータ | 説明 | デフォルト |
| -------- | ----------- | ---- | ----------- |
| common | log_path | アプリケーションログのフルパス | /var/log/apps/application.log |
| backup | latest_backup_date | バックアップ実行最新日の記録ファイルパス | /var/log/apps/autobackup.last |
| schedule | schedule_conf | スケジュール管理のファイルパス | /apps/admin/conf/schedule.conf |
| schedule | schedule_lock | 排他制御のファイルパス | /var/log/apps/schedule.lock |
| optimization | optimization_lock | 排他制御のファイルパス | /var/log/apps/optimization.lock |

### 個別パラメータ

~~~
/apps/admin/conf/user.conf
~~~

| セクション | パラメータ | 説明 | デフォルト |
| -------- | ----------- | ---- | ----------- |
| schedule | start_time | EC2 起動時刻（時）のデフォルト ||
| schedule | stop_time | EC2停止時刻（時）のデフォルト ||
| schedule | week_period | 週における実行周期のデフォルト everyday：毎日 weekday：平日のみ disabled：無効 |
| optimization | ec2_cpu_utilization | 1日当たりの平均CPU使用率の閾値（%） | 10 |
| optimization | ec2_low_period | 2週間のうち、閾値を下回る期間（日） | 4 |
| optimization | rds_idle_period | 1週間のうち、DBコネクションがない期間（日） | 4 |
| optimization | elb_few_request | 1日当たりの最低リクエスト数 | 100 |
| optimization | ebs_max_iops | 1日あたりの最低IOPS（書込み） | 100 |
| optimization | region | SESのリージョン | us-east-1 |
| optimization | from_address | SESからメッセージ送信するFromメールアドレス（複数不可） ||
| optimization | to_address | SESからメッセージ送信するToメールアドレス（複数不可） ||
