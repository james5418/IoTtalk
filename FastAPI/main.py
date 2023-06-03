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

user_id_set = set()
app = FastAPI()


ServerURL = 'https://3.iottalk.tw/'
mac_addr = 'CD8601D38' + str(5634)
Reg_addr = mac_addr
DAN.profile['dm_name'] = 'SD_LineBot'
DAN.profile['df_list'] = ['MSG-I', 'MSG-O']
DAN.profile['d_name'] = DAN.profile['dm_name'] + str(random.randint(0, 100))
DAN.device_registration_with_retry(ServerURL, Reg_addr)
print("dm_name is ", DAN.profile['dm_name'])
print("Server is ", ServerURL)


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

        if res.iot_command != -1:
            DAN.push('MSG-I', res.iot_command)
    
        if res.msg_type == 'flex':
            await line_bot_api.reply_message(event.reply_token, FlexSendMessage('flex message', res.line_reply))
        else:    
            await line_bot_api.reply_message(event.reply_token, TextSendMessage(text=res.line_reply))
        
    return 'OK'


def pull_BoardData():
    global lsLock
    lsLock = threading.Lock()
    while True:
        data = DAN.pull('MSG-O')
        if data and data[0]:
            with lsLock:
                with open("light_status.txt", "w") as f:
                    if data[0] >= 1000:
                        f.write("0")
                        DAN.push('MSG-I', 0)
                    else:
                        f.write("1")
                        DAN.push('MSG-I', 1)
        time.sleep(1)


def loadUserId():
    try:
        idFile = open('idfile', 'r')
        idList = idFile.readlines()
        idFile.close()
        idList = idList[0].split(';')
        idList.pop()
        return idList
    except Exception as e:
        print(e)
        return []


def saveUserId(userId):
    idFile = open('idfile', 'a')
    idFile.write(userId+';')
    idFile.close()


if __name__ == '__main__':
    idList = loadUserId()
    if idList:
        user_id_set = set(idList)

    thread2 = threading.Thread(target=pull_BoardData)
    thread2.daemon = True
    thread2.start()

    uvicorn.run("main:app", host="0.0.0.0", port=8888, reload=True)