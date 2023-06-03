from fastapi import FastAPI, Request, HTTPException
import uvicorn
from linebot import AsyncLineBotApi, WebhookParser
from linebot.aiohttp_async_http_client import AiohttpAsyncHttpClient
from linebot.exceptions import InvalidSignatureError 
from linebot.models import MessageEvent, TextMessage, TextSendMessage, FlexSendMessage
from dotenv import load_dotenv
import aiohttp
import os
import threading
import time
import random
import DAN
from cmdHandler import parse_cmd


load_dotenv()
CHANNEL_ACCESS_TOKEN = os.environ.get("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.environ.get("CHANNEL_SECRET")

session = aiohttp.ClientSession()
async_http_client = AiohttpAsyncHttpClient(session)
line_bot_api = AsyncLineBotApi(CHANNEL_ACCESS_TOKEN, async_http_client)
parser = WebhookParser(CHANNEL_SECRET)


lightStatus = None
lsLock = threading.Lock()

user_id_set = set()
app = FastAPI()


ServerURL = 'https://3.iottalk.tw/'
Reg_addr = None
mac_addr = 'CD8601D38' + str(5634)
Reg_addr = mac_addr
DAN.profile['dm_name'] = 'SD_LineBot'
DAN.profile['df_list'] = ['MSG-I', 'MSG-O']
DAN.profile['d_name'] = DAN.profile['dm_name'] + str(random.randint(0, 100))
DAN.device_registration_with_retry(ServerURL, Reg_addr)
print("dm_name is ", DAN.profile['dm_name'])
print("Server is ", ServerURL)


def loadUserId():
    try:
        idFile = open('idfile', 'r')
        idList = idFile.readlines()
        idFile.close()
        idList = idList[0].split(';')
        idList.pop()
        return idList
    except Exception as e:
        # print(e)
        return []


def saveUserId(userId):
    idFile = open('idfile', 'a')
    idFile.write(userId+';')
    idFile.close()


@app.post("/callback")
async def handle_callback(request: Request):
    signature = request.headers['X-Line-Signature']
    body = await request.body()
    body = body.decode()

    try:
        events = parser.parse(body, signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    for event in events:
        if not isinstance(event, MessageEvent):
            continue
        if not isinstance(event.message, TextMessage):
            continue

        res = parse_cmd(event.message.text)

        if res.iot_command != 0:
            DAN.push('MSG-I', res.iot_command)
    
        if res.msg_type == 'flex':
            await line_bot_api.reply_message(event.reply_token, FlexSendMessage('flex message', res.line_reply))
        else:    
            await line_bot_api.reply_message(event.reply_token, TextSendMessage(text=res.line_reply))
        
    return 'OK'


def pull_BoardData():
    global lightStatus, lsLock
    while True:
        data = DAN.pull('MSG-O')
        if data:
            lsLock.acquire()
            lightStatus = data[0]
            lsLock.release()

            # Fake dict for demo
            user_Security = {}
            user_Security[id] = True

            # (data[0] > 0.1) will be replaced by real data format
            if (data[0] > 0.1) and user_Security[id]:
                line_bot_api.push_message(userId, TextSendMessage(text='偵測到人員進出！'))
        time.sleep(1)


# Procees the message and returns the reply
def someProcessing(id, data):
    global lightStatus
    lineReply = '我聽不懂你在說什麼'
    IoTCommand = None

    # Open/Close Lights
    if data == '開燈':
        if lightStatus == True:
            lineReply = '燈已經是開的囉'
        else:
            lightStatus = True
            lineReply = '開囉！'
            IoTCommand = '1'

    elif data == '關燈':
        if lightStatus == False:
            lineReply = '燈已經是關的囉'
        else:
            lightStatus = False
            lineReply = '關囉！'
            IoTCommand = '0'

    # Check Light Status
    elif 'status' in data:
        if lightStatus == True:
            lineReply = '目前燈是開的'
        else:
            lineReply = '目前燈是關的'

    # Track door status
    elif 'security' in data:
        # Fake dict for demo
        user_Security = {}
        user_Security[id] = True

        if user_Security[id] == True:
            lineReply = '偵測到人員進出時，會立即通知您！'
        else:
            lineReply = '已為您關閉人員進出通知！'

    return lineReply, IoTCommand


if __name__ == '__main__':
    idList = loadUserId()
    print(idList)
    if idList:
        user_id_set = set(idList)

    try:
        for userId in user_id_set:
            line_bot_api.push_message(userId, TextSendMessage(text='LineBot is ready for you.'))
    except Exception as e:
        print(e)


    thread2 = threading.Thread(target=pull_BoardData)
    thread2.daemon = True
    thread2.start()

    uvicorn.run("main:app", host="0.0.0.0", port=8888, reload=True)