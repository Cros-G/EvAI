import streamlit as st
import datetime
import json
import requests
import os
from tool_func import resp_trans, stream_data
import pandas as pd

# 基础数据准备
filename = {"models": "./models.json",
            "caps": "./caps.json",
            "prompts": "./prompts.json"}

# 可调用的模型、能力和提示词
with open(filename['models'], 'r', encoding='utf-8') as f:
    models = json.load(f)

with open(filename['caps'], 'r', encoding='utf-8') as f:
    caps = json.load(f)

with open(filename['prompts'], 'r', encoding='utf-8') as f:
    prompts = json.load(f)

# 页面基本设置
st.set_page_config(page_title='EvAI - 模型能力评估工具', layout='wide', page_icon='👽')

# 侧边栏设置
with st.sidebar:
    st.header('基本配置', divider='grey')
    st.subheader(':blue[1. 模型与待评估能力]')
    # 选择厂商和模型
    col1, col2 = st.columns([3, 5])
    with col1:
        company_chosen = st.selectbox("选择厂商", [models[i]['company'] for i in range(len(models))])
        encoding = [item['encoder'] for item in models if item['company'] == company_chosen][0]
        authorization = [item['Authorization'] for item in models if item['company'] == company_chosen][0]
    with col2:
        model_chosen = st.selectbox("选择模型", [item['models'] for item in models if item['company'] == company_chosen][0])

    # 选择标准能力，确定本次生成任务使用的prompt
    cap_chosen = st.selectbox("选择想评估的能力", [caps[i]['cap_name'] for i in range(len(caps))])
    prompt_default = [prompt for prompt in prompts if prompt['cap'] == cap_chosen][0]['prompt']

    # 选择素材
    folder_path = "./materials"
    items = os.listdir(folder_path)
    materials = [item.split('.')[0] for item in items]
    mat_chosen = st.selectbox(f'请选择需要做【{cap_chosen}】的素材', materials)
    with open(folder_path + '/' + mat_chosen + '.txt', 'r', encoding='utf-8') as f:  # 当前只支持后缀为.txt的素材
        mat_text_chosen = f.read()

    # 设定prompt
    st.subheader(':blue[2. Prompt设定]')
    col_prompt, col_save = st.columns([8, 2])
    with col_prompt:
        prompt_applied = st.text_area('输入Prompt', prompt_default, height=300, label_visibility='collapsed')
    with col_save:
        # 保存当前编辑后的模板
        if st.button('保存'):
            prompts.insert(0, {
                "cap": cap_chosen,
                "prompt": prompt_applied,
                "save_time": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
            with open(filename['prompts'], 'w', encoding='utf-8') as f:
                json.dump(prompts, f, ensure_ascii=False)

# 调取接口，获得输出结果
input_LLM = f"{prompt_applied} \n 【{mat_text_chosen}】"
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
elif company_chosen == "Claude":
    url = [model['url'] for model in models if model['company'] == company_chosen][0]
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
else:
    url = [model['url'] for model in models if model['company'] == company_chosen][0]
    body = {
        "model": model_chosen,
        "max_tokens": 4096,
        "messages": [
            {"role": "system", "content": "你是AI助手"},
            {"role": "user", "content": f"{input_LLM}"}
        ],
        "stream": True
    }

st.subheader('操作台', divider="grey")

with st.container(height=45, border=False):
    col_gen,  col_rating, col_others, col_caption= st.columns([6, 1, 1, 8])
    with col_gen:
        if st.button('生成内容'):
            response = requests.post(params=params, url=url, headers=headers, json=body)
    with col_caption:
        st.caption(f"当前模型：<b>{model_chosen}</b><br>当前评估能力：<b>{cap_chosen}</b>", unsafe_allow_html=True)
    # with col_rating:
    #     score = st.number_input('给模型打分', min_value=1, max_value=10, value=5, step=1, label_visibility='collapsed')
    # with col_others:
    #     st.empty()

col_input, col_output = st.columns([1, 1])
with col_input:
    with st.container(height=600, border=True):
        st.markdown('<b>素材原文</b>', unsafe_allow_html=True)
        st.caption('<font color="blue"><i>' + mat_text_chosen + '</i></font>', unsafe_allow_html=True)

with col_output:
    with st.container(height=600):
        with st.container(height=50, border=False):
            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown('<b>输出结果</b>\n', unsafe_allow_html=True)
            with col2:
                score = st.text_input('给模型打分', placeholder='打分，1~10间的整数', label_visibility='collapsed')
                # 更新当前模型的当前能力下的得分
                with open("./scores.json", "r", encoding='utf-8') as f:
                    scores = json.load(f)
                found_and_updated = False  # 标记是否找到并更新了数据
                for item in scores:
                    if item["model"] == model_chosen and item["cap"] == cap_chosen:
                        item["score"] = score
                        found_and_updated = True
                        break
                if not found_and_updated:  # 如果没有找到匹配的项，可以选择添加新项
                    scores.append({"model": model_chosen, "cap": cap_chosen, "score": score})
                with open("./scores.json", "w", encoding='utf-8') as f:
                    json.dump(scores, f, ensure_ascii=False, indent=4)

        # st.markdown(response.json()["choices"][0]["message"]["content"], unsafe_allow_html=True) # 供单步调用
        if company_chosen == "Baidu":
            st.write(response.json()["result"])
        elif company_chosen == "Claude":
            st.write(response.json()["content"][0]["text"])
        else:
            st.write_stream(stream_data(resp_trans(response.text, encoder=encoding)))

st.write(pd.read_json("./scores.json", encoding='utf-8'))