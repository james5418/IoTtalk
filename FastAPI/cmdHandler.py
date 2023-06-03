from pydantic import BaseModel
from typing import Union
import json


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
    with open('response/usage.json', 'r') as f:
        return json.load(f)


def parse_cmd(message: str) -> ResponseData:

    message = message.lower().strip()

    command_mapping = {
        'open': ResponseData(line_reply=message, iot_command=1, msg_type='text'),
        'close': ResponseData(line_reply=message, iot_command=0, msg_type='text'),
        'status': ResponseData(line_reply=get_light_status(), iot_command=-1, msg_type='text'),
        'schedule': ResponseData(line_reply=message, iot_command=-1, msg_type='text'),
        'help': ResponseData(line_reply=get_usage(), iot_command=-1, msg_type='flex')
    }

    return command_mapping.get(message, ResponseData(line_reply=message, iot_command=-1, msg_type='text'))
