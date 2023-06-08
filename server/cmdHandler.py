import time
from apscheduler.schedulers.background import BackgroundScheduler
from pydantic import BaseModel
from typing import Union
import json
import DAN


scheduler = BackgroundScheduler()
scheduler.start()


class ResponseData(BaseModel):
    line_reply: Union[dict, str]
    iot_command: int
    msg_type: str


def get_light_status() -> str:
    lightStatus = readMsg('light_status.txt')
    if lightStatus == '1':
        return '目前燈是開的喔！'
    else:
        return '目前燈是關的喔！'


def get_usage() -> dict:
    with open('response/usage.json', 'r', encoding='utf-8') as f:
        return json.load(f)


def set_cronjob(time: str, action: int):
    hour, minute = map(int, time.split(':'))
    scheduler.add_job(turn_on_off_light, trigger='cron',
                      hour=hour, minute=minute, args=[action])
    print(f'[set_cronjob] 已設定排程: {hour}:{minute} {action}')


def turn_on_off_light(action: int):
    DAN.push('MSG-I', action)
    writeMsg('light_status.txt', str(action))
    writeMsg("last_trigger_time.txt", time.time())
    print(f'已執行排程: {action}')


def parse_cmd(message: str, id: str = "") -> ResponseData:

    message = message.lower().strip()

    command_mapping = {
        'open': ResponseData(line_reply='幫您開燈囉！', iot_command=1, msg_type='text'),
        'close': ResponseData(line_reply='幫您關燈囉！', iot_command=0, msg_type='text'),
        'status': ResponseData(line_reply=get_light_status(), iot_command=-1, msg_type='text'),
        'schedule': ResponseData(line_reply='使用以下指令設定排程：\nschedule <HH:MM> <on/off>', iot_command=-1, msg_type='text'),
        'alert': ResponseData(line_reply='幫您開啟通知囉！', iot_command=-1, msg_type='text'),
        'help': ResponseData(line_reply=get_usage(), iot_command=-1, msg_type='flex')
    }

    cmd = message.split(' ')
    if cmd[0] == 'schedule' and len(cmd) != 1:
        if len(cmd) == 3:
            if cmd[2] == 'on':
                set_cronjob(cmd[1], 1)
                return ResponseData(line_reply=f'已設定排程：{cmd[1]} 開燈', iot_command=-1, msg_type='text')
            elif cmd[2] == 'off':
                set_cronjob(cmd[1], 0)
                return ResponseData(line_reply=f'已設定排程：{cmd[1]} 關燈', iot_command=-1, msg_type='text')
            else:
                return ResponseData(line_reply='請輸入正確的指令', iot_command=-1, msg_type='text')
        else:
            return ResponseData(line_reply='請輸入正確的指令', iot_command=-1, msg_type='text')

    if cmd[0] == 'alert' and len(cmd) == 1:
        idList = loadUserId()
        if id not in idList:
            idList.append(id)
            writeMsg('userId.txt', '\n'.join(idList))
            return ResponseData(line_reply='幫您開啟通知囉！', iot_command=-1, msg_type='text')
        else:
            idList.remove(id)
            writeMsg('userId.txt', '\n'.join(idList))
            return ResponseData(line_reply='幫您關閉通知囉！', iot_command=-1, msg_type='text')

    if cmd[0] == 'open' and len(cmd) == 1:
        lastCanTriggerTime = float(readMsg("last_trigger_time.txt"))
        canTrigger = (lastCanTriggerTime + 10 < time.time())

        if canTrigger:
            writeMsg('light_status.txt', '1')
            writeMsg("last_trigger_time.txt", time.time())
            return ResponseData(line_reply='幫您開燈囉！', iot_command=1, msg_type='text')
        else:
            return ResponseData(line_reply='電燈累了，請等一會再試哦！', iot_command=-1, msg_type='text')

    if cmd[0] == 'close' and len(cmd) == 1:
        lastCanTriggerTime = float(readMsg("last_trigger_time.txt"))
        canTrigger = (lastCanTriggerTime + 10 < time.time())

        if canTrigger:
            writeMsg('light_status.txt', '0')
            writeMsg("last_trigger_time.txt", time.time())
            return ResponseData(line_reply='幫您關燈囉！', iot_command=0, msg_type='text')
        else:
            return ResponseData(line_reply='電燈累了，請等一會再試哦！', iot_command=-1, msg_type='text')

    return command_mapping.get(message, ResponseData(line_reply=get_usage(), iot_command=-1, msg_type='flex'))


def loadUserId():
    return [id for id in readMsg('userId.txt').split('\n') if id]


def readMsg(filename):
    with open(filename, "r") as f:
        return f.read()


def writeMsg(filename, msg):
    with open(filename, "w") as f:
        f.write(str(msg))
