import json
from pydantic import BaseModel
from typing import Union


class ResponseData(BaseModel):
    line_reply: Union[dict, str]
    iot_command: int  # -1, 0, 1
    msg_type: str  # text, flex


def parse_cmd(message: str) -> ResponseData:

    message = message.lower()
    message = message.strip()

    if message == 'help':
        usage = json.load(open('response/usage.json', 'r', encoding='utf-8'))
        return ResponseData(line_reply=usage, iot_command=0, msg_type='flex')


    return ResponseData(line_reply=message, iot_command=0, msg_type='text')
