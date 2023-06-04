from fastapi import FastAPI, Request, HTTPException
import uvicorn
from linebot import AsyncLineBotApi, WebhookParser
from linebot.aiohttp_async_http_client import AiohttpAsyncHttpClient
from linebot.exceptions import InvalidSignatureError 
from linebot.models import MessageEvent, TextMessage, TextSendMessage, FlexSendMessage
from dotenv import load_dotenv
import aiohttp
import asyncio
import os
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

app = FastAPI()


ServerURL = 'https://2.iottalk.tw/'
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

        res = parse_cmd(event.message.text, event.source.user_id)

        if res.iot_command != -1:
            DAN.push('MSG-I', res.iot_command)
            with open('light_status.txt', 'w') as f:
                f.write(str(res.iot_command))
    
        if res.msg_type == 'flex':
            await line_bot_api.reply_message(event.reply_token, FlexSendMessage('flex message', res.line_reply))
        else:    
            await line_bot_api.reply_message(event.reply_token, TextSendMessage(text=res.line_reply))
        
    return 'OK'


async def pullBoardData():
    lastDoorOpenTime = 0
    doorIsOpen = False
    while True:
        data = DAN.pull('MSG-O')
        if data and data[0]:
            jsonDict = data[0]
            with open("light_status.txt", "r") as f:
                SwitchOn = (f.read() == "1")
                LightOn = (jsonDict["light"] < 900)
                doorOpen = (jsonDict["distance"] <= 10)
            
            if doorOpen and lastDoorOpenTime + 5 < time.time():
                lastDoorOpenTime = time.time()
                doorIsOpen = True

                if not SwitchOn:
                    sendAndWriteMsg("light_status.txt", 1)

            elif (not LightOn) and SwitchOn:
                sendAndWriteMsg("light_status.txt", 0)
                    
        if doorIsOpen:
            doorIsOpen = False
            await sendMsgToAllUser("門已開啟")

        await asyncio.sleep(0.5)


def sendAndWriteMsg(filename, msg):
    DAN.push('MSG-I', msg)
    with open(filename, "w") as f:
        f.write(str(msg))


async def sendMsgToAllUser(msg):
    idList = loadUserId()
    for id in idList:
        await line_bot_api.push_message(id, TextSendMessage(text=msg))


def loadUserId():
    with open('userId.txt', 'r') as f:
        return f.read().split('\n')


@app.on_event("startup")
def main():
    loop = asyncio.get_event_loop()
    loop.create_task(pullBoardData())
    

if __name__ == '__main__':
    uvicorn.run("main:app", host="0.0.0.0", port=8888, reload=True)