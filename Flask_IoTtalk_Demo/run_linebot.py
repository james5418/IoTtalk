import random
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import DAN
import threading
import queue
import time
from dotenv import load_dotenv
import os

load_dotenv()
channel_token = os.getenv("CHANNEL_TOKEN")
channel_secret = os.getenv("CHANNEL_SECRET")
line_bot_api = LineBotApi(channel_token)
handler = WebhookHandler(channel_secret)

user_id_set = set()
app = Flask(__name__)

# msgQueue is a queue for storing messages from LineBot
msgQueue = queue.Queue()
lightStatus = None
lsLock = threading.Lock()

# IoTtalk Setting, comment out because 7.iottalk.tw currently is down
# ServerURL = 'https://7.iottalk.tw/'
# Reg_addr = None
# mac_addr = 'CD8601D38' + str(5634)
# Reg_addr = mac_addr
# DAN.profile['dm_name'] = 'WPS_LineBot'
# DAN.profile['df_list'] = ['MSG-I', 'MSG-O']
# DAN.profile['d_name'] = DAN.profile['dm_name'] + str(random.randint(0, 100))
# DAN.device_registration_with_retry(ServerURL, Reg_addr)
# print("dm_name is ", DAN.profile['dm_name'])
# print("Server is ", ServerURL)


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


@ app.route("/", methods=['GET'])
def hello():
    return "HTTPS Test OK."


@ app.route("/", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']
    # get request body as text
    body = request.get_data(as_text=True)
    print("Request body: " + body, "Signature: " + signature)
    try:
        handler.handle(body, signature)                # handle webhook body
    except InvalidSignatureError:
        abort(400)
    return 'OK'


# Handle Incoming Message, puts the message into msgQueue
@ handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    global msgQueue
    Msg = event.message.text

    userId = event.source.user_id
    if not userId in user_id_set:
        user_id_set.add(userId)
        saveUserId(userId)

    msgQueue.put((userId, Msg.lower()))


# Pulls data from msgQueue and sends it to LineBot
def pull_lineMessage():
    global q, lsLock
    while True:
        # get user message from msgQueue, lock boardData
        (id, data) = msgQueue.get()
        lsLock.acquire()

        # process the message and get the reply
        lineReply, IoTCommand = someProcessing(id, data)

        # send the reply to IoTtalk
        if IoTCommand:
            DAN.push('MSG-I', IoTCommand)

        # send the reply to LineBot
        for userId in user_id_set:
            line_bot_api.push_message(
                userId, TextSendMessage(text=lineReply))
            user_id_set.remove(userId)
            break

        # mark the task as done, release boardData
        lsLock.release()
        msgQueue.task_done()


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
                line_bot_api.push_message(
                    userId, TextSendMessage(text='偵測到人員進出！'))
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


if __name__ == "__main__":
    idList = loadUserId()
    print(idList)
    if idList:
        user_id_set = set(idList)

    try:
        for userId in user_id_set:
            line_bot_api.push_message(userId, TextSendMessage(
                text='LineBot is ready for you.'))  # Push API example
    except Exception as e:
        print(e)

    thread1 = threading.Thread(target=pull_lineMessage)
    thread1.daemon = True
    thread1.start()

    thread2 = threading.Thread(target=pull_BoardData)
    thread2.daemon = True
    thread2.start()

    app.run('127.0.0.1', port=32768, threaded=True, use_reloader=False)
