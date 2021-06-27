import os
from requests import post
from json import dumps, loads

api_token = os.environ['API_TOKEN']
room_id = os.environ['ROOM_ID']

def lambda_handler(event, context):
    sub = event['Records'][0]['Sns']['Subject']
    msg = loads(event['Records'][0]['Sns']['Message'])

    url = 'https://api.chatwork.com/v2/rooms/{}/messages'.format(room_id)
    header = {'X-ChatWorkToken': api_token}
    payload = {'body': '[info][title]{}[/title]{}[/info]'.format(sub, msg['NewStateReason'])}

    res = post(url, headers=header, data=payload)

    return 'OK'