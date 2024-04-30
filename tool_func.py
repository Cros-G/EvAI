import time
import re
import json


def resp_trans(response_text, encoder='utf-8'):
    """将https接口返回的response做预处理"""
    content_list = re.findall(r'^data:\s*(.*)', response_text, flags=re.MULTILINE)
    for_yield = content_list[:-2]
    return [json.loads(for_yield[i])['choices'][0]['delta']['content'].encode(f'{encoder}').decode('utf-8')
            for i in range(len(for_yield))]


# def resp_tokens_count(response_text, encoder='utf-8'):
#     """将API接口流式输出返回的response做tokens统计"""
#     content_list = re.findall(r'^data:\s*(.*)', response_text, flags=re.MULTILINE)
#     prompt_tokens = json.loads(content_list[-2])['choices'][0]['usage']['prompt_tokens']
#     completion_tokens = json.loads(content_list[-2])['choices'][0]['usage']['completion_tokens']
#     total_tokens = json.loads(content_list[-2])['choices'][0]['usage']['total_tokens']
#     return [prompt_tokens, completion_tokens, total_tokens]


def stream_data(data):
    """形成可迭代对象，便于write_stream组件使用"""
    for item in data:
        yield item
        time.sleep(0.02)


def api_config(company_chosen, model_chosen, input_LLM, stream):
    """根据厂商和模型的接口特性，返回调取api所必须的参数"""
    with open("./models.json", 'r', encoding='utf-8') as f:
        models = json.load(f)
    authorization = [item['Authorization'] for item in models if item['company'] == company_chosen][0]
    url = [model['url'] for model in models if model['company'] == company_chosen][0]
    api_key = [model['api_key'] for model in models if model['company'] == company_chosen][0]
    params = {f"{authorization}": api_key}
    headers = {f"{authorization}": api_key}
    if company_chosen == "Baidu":
        url = [model['url'] for model in models if model['company'] == company_chosen][0] + model_chosen.split('|')[1]
        body = {
            "messages": [
                {"role": "user", "content": "你好"},
                {"role": "assistant", "content": "你是AI助手"},
                {"role": "user", "content": f"{input_LLM}"}
            ]
        }
    elif company_chosen == "Anthropic":
        headers = {
            f"{authorization}": api_key,
            "anthropic-version": "2023-06-01"
        }
        body = {
            "model": model_chosen,
            "max_tokens": 4096,
            "messages": [
                {"role": "user", "content": f"{input_LLM}"}
            ]
        }
    # elif company_chosen == "Hong Corp.":
    #     body = {
    #         "model": model_chosen,
    #         "messages": [
    #             {"role": "system", "content": "你是AI助手"},
    #             {"role": "user", "content": f"{input_LLM}"}
    #         ],
    #         "history": []
    #     }
    else:
        body = {
            "model": model_chosen,
            "messages": [
                {"role": "system", "content": "你是AI助手"},
                {"role": "user", "content": f"{input_LLM}"}
            ],
            "stream": stream
        }
    return {"url": url, "params": params, "headers": headers, "body": body}
