# CloudWatch AlarmをクロスアカウントなLambdaからChatworkへ飛ばしたい

異なるAWSアカウントのSNS Topicをサブスクライブして、ChatworkへCloudWatch Alarmを通知するための手順と環境構築手順です。

<br>

## 概要

今回は以下のようなケースを想定しています。

<br>

![architecture](./img/architecture.png)

<br>

サービスを稼働させているアカウントAから、システム管理用アカウントBに対してCloudWatchメトリクスの閾値超過のアラームを転送し、Chartworkへ転送します。
Lambdaがサブスクライブする対象Topicを増加させば、複数のサービスアカウントを統合的にアカウントBで処理可能です。

通知対象としているAlarmはALBのRequest Countメトリクスですが、CloudWatch上でAlarmとして設定できるものであれば何でも良いです。

<br>

## 手順の流れ

手順全体の大まかな流れは以下のようになります。

#### アカウントA

1. CloudWatch Alarmを作成（手動）
2. SNS Topicを作成しクロスアカウント権限を付与（手動）

#### アカウントB

3. SAMで環境構築

<br>

## SAMについて

今回はアカウントB環境をSAMを使って簡単に構築していきます。
[テンプレート](./template.yaml)の中身（```Description```や```FunctionName```など）や、[Lambda関数](./push_chatwork.py)で送信するメッセージ表記は適宜変更して下さい。

<br>

## 本READMEで詳しく紹介しない手順

- CloudWatchのアラーム作成手順
- SNS Topicの作成手順
- AWS SAM CLIの実行環境構築手順（詳しい手順：[公式サイト](https://docs.aws.amazon.com/ja_jp/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)）

<br>

## 構築手順

### アカウントAでの作業

#### CloudWatch Alarmの作成

1. CloudWatchの```アラームの作成```を押下

2. メトリクスを選択しアラーム条件などを指定し```次へ```を押下

3. アラーム状態トリガーを```アラーム状態```にして```新しいトピックの作成```を選択（既存のものを利用するなら手順5へスキップ）

4. 適当にトピック名を記述しEメールエンドポイントを入力（初回必ずEメールアドレスを入力する必要があるが後でアンサブスクライブすると良い）

5. アラーム名と説明を適当に入力し、アラーム作成完了

#### SNS Topicへクロスアカウント権限を付与

6. SNS管理コンソールから手順4で作成したTopicを選択

7. ```編集```を押下し、アクセスポリシーへ以下のポリシーを追加
    ```json
    {
      "Sid": "lambda-access",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::{アカウントBのアカウントID}:root"
      },
      "Action": [
        "SNS:Subscribe",
        "SNS:ListSubscriptionsByTopic",
        "SNS:Receive"
      ],
      "Resource": "arn:aws:sns:{リージョン}:{アカウントAのアカウントID}:{トピック名}"
    }
    ```
    編集後は全体がこんな感じになると思われる
    ```json
    {
        "Version": "2008-10-17",
        "Id": "__default_policy_ID",
        "Statement": [
            {
            "Sid": "__default_statement_ID",
            "Effect": "Allow",
            "Principal": {
                "AWS": "*"
            },
            "Action": [
                "SNS:GetTopicAttributes",
                "SNS:SetTopicAttributes",
                "SNS:AddPermission",
                "SNS:RemovePermission",
                "SNS:DeleteTopic",
                "SNS:Subscribe",
                "SNS:ListSubscriptionsByTopic",
                "SNS:Publish",
                "SNS:Receive"
            ],
            "Resource": "arn:aws:sns:{リージョン}:{アカウントAのアカウントID}:{トピック名}",
            "Condition": {
                "StringEquals": {
                "AWS:SourceOwner": "{アカウントAのアカウントID}"
                }
            }
            },
            {
            "Sid": "lambda-access",
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::{アカウントBのアカウントID}:root"
            },
            "Action": [
                "SNS:Subscribe",
                "SNS:ListSubscriptionsByTopic",
                "SNS:Receive"
            ],
            "Resource": "arn:aws:sns:{リージョン}:{アカウントAのアカウントID}:{トピック名}"
            }
        ]
    }
    ```

8. 変更を保存

<br>

### アカウントBでの作業

#### 事前準備

9. 本リポジトリをローカル環境へクローン
    ```
    $ git clone https://github.com/momonchy/alarm-push-to-chatwork.git
    $ cd alarm-push-to-chatwork/
    ```

10. アプリケーションをビルド
    ```
    $ sam build
    ```

11. テスト用のSNSイベントを生成
    ```
    $ sam local generate-event sns notification --subject "ALARM" --message "{\"NewStateReason\": \"Threshold Crossed\"}" > event.json
    ```

12. テスト用の変数ファイルを作成
    ```json
    $ vim .env.json

    {
        "Parameters": {
            "API_TOKEN": "{ChartworkのAPIトークン}",
            "ROOM_ID": "{ChartworkのルームID}",
            "SNS_TOPIC": "arn:aws:sns:{リージョン}:{アカウントAのアカウントID}:{トピック名}"
        }
    }
    ```

#### テスト＆デプロイ

13. ローカル環境でLambda実行テスト
    ```
    $ sam local invoke -e event.json -n .env.json PushChatworkFunc
    ```
    Chatworkでメッセージを受信できることを確認

14. ローカル環境の環境変数へ手順12と同じ変数を設定

    ```
    $ echo ${API_TOKEN}
    $ echo ${ROOM_ID}
    $ echo ${SNS_TOPIC}
    ```

    SAM DEPLOYでは```parameter_overrides```でしか変数を渡せないため、ローカル環境の環境変数をパラメータとして引き渡す

15. デプロイ
    ```
    $ sam deploy --guided --parameter-overrides ApiToken=${API_TOKEN} RoomId=${ROOM_ID} SnsTopic=${SNS_TOPIC}
    ```

<br>

### 確認作業

- アカウントAのSNSトピックが、LAMBDAプロトコルでアカウントBからサブスクライブされている
- アカウントBのSNSサブスクリプションへ、アカウントAのSNSトピックをサブスクライブしているサブスクリプションが存在する
- アカウントBのLambdaのトリガーにSNSが登録されている

<br>

## 参考URL

- [クロスアカウントなLambdaをSNS TopicにSubscribeする](https://dev.classmethod.jp/articles/crossaccount-lambda-subscribing-sns-topic/)
- [Chatwork API Reference](https://developer.chatwork.com/ja/endpoint_rooms.html#POST-rooms-room_id-messages)
- [SAM Template Reference](https://github.com/aws/serverless-application-model/blob/master/versions/2016-10-31.md)
