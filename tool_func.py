import time
import re
import json


def resp_trans(response_text, encoder='utf-8'):
    """将https接口返回的response做预处理"""
    content_list = re.findall(r'^data:\s*(.*)', response_text, flags=re.MULTILINE)
    for_yield = content_list[:-2]
    return [json.loads(for_yield[i])['choices'][0]['delta']['content'].encode(f'{encoder}').decode('utf-8') for i in range(len(for_yield))]


def stream_data(data):
    """形成可迭代对象，便于write_stream组件使用"""
    for item in data:
        yield item
        time.sleep(0.02)

