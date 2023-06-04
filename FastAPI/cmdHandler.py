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
    with open('light_status.txt', 'r') as f:
        if f.read() == '1':
            return '目前燈是開的'
        else:
            return '目前燈是關的'


def get_usage() -> dict:
    with open('response/usage.json', 'r', encoding='utf-8') as f:
        return json.load(f)


def set_cronjob(time: str, action: int):
    hour, minute = map(int, time.split(':'))
    scheduler.add_job(turn_on_off_light, trigger='cron', hour=hour, minute=minute, args=[action])
    print(f'[set_cronjob] 已設定排程: {hour}:{minute} {action}')
    

def turn_on_off_light(action: int):
    DAN.push('MSG-I', action)
    with open('light_status.txt', 'w') as f:
        f.write(str(action))
    print(f'已執行排程: {action}')


def parse_cmd(message: str, id: str = "") -> ResponseData:

    message = message.lower().strip()

    command_mapping = {
        'open': ResponseData(line_reply='已開燈', iot_command=1, msg_type='text'),
        'close': ResponseData(line_reply='已關燈', iot_command=0, msg_type='text'),
        'status': ResponseData(line_reply=get_light_status(), iot_command=-1, msg_type='text'),
        'schedule': ResponseData(line_reply='請使用以下指令：\nschedule <HH:MM> <on/off>', iot_command=-1, msg_type='text'),
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
            with open('userId.txt', 'w') as f:
                f.write('\n'.join(idList))
            return ResponseData(line_reply='幫您開啟通知囉！', iot_command=-1, msg_type='text')
        else:
            idList.remove(id)
            with open('userId.txt', 'w') as f:
                f.write('\n'.join(idList))
            return ResponseData(line_reply='幫您關閉通知囉！', iot_command=-1, msg_type='text')
        
    return command_mapping.get(message, ResponseData(line_reply=get_usage(), iot_command=-1, msg_type='flex'))


def loadUserId():
    with open('userId.txt', 'r') as f:
        return [id for id in f.read().split('\n') if id]