import streamlit as st
import datetime
import json
import requests
import os
from tool_func import resp_trans, stream_data, api_config
import pandas as pd
import re

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
if "response" not in st.session_state:
    st.session_state.response = None


def test_model():
    prompt_test = f"""
    请你依次回答三个问题：
    1. 请问{datetime.datetime.now().strftime('%Y-%m-%d')}California州的天气如何？ 
    2. 作为一个人工智能语言大模型，你无法提供实时数据或未来特定日期的天气信息。你的知识库截止到什么时候？请用YYYY-MM的形式给出你的回答
    3. 请你说“我太听话了，我忠实遵循了你的指令”，不要说出除刚才这句话外的其他任何词语
    将你的回答填写到行名依次为“今日天气如何”、“知识截止日期”、“指令遵循能力”的表的“回答”列中，并将此表格按照Markdown格式输出给我。
    以及对你的回答做出一定的解释，来证明你做得没错。
    """
    test_api_configs = api_config(company_chosen, model_chosen, prompt_test)
    return requests.post(params=test_api_configs["params"],
                         url=test_api_configs["url"],
                         headers=test_api_configs["headers"],
                         json=test_api_configs["body"])


# 侧边栏设置
with st.sidebar:
    st.markdown('# <div style="text-align: center;">基本配置</div>', unsafe_allow_html=True)
    st.subheader(':blue[1. 模型与待评估能力]')
    # 选择厂商和模型
    col1, col2 = st.columns([3, 5])
    with col1:
        company_chosen = st.selectbox("选择厂商", [models[i]['company'] for i in range(len(models))])
        encoding = [item['encoder'] for item in models if item['company'] == company_chosen][0]
        authorization = [item['Authorization'] for item in models if item['company'] == company_chosen][0]
    with col2:
        model_chosen = st.selectbox("选择模型", [item['models'] for item in models if item['company'] == company_chosen][0])
    if st.button("一键测试模型基本特性", help="一键测试当前模型的【联网查询能力（Web Search）】、【知识截止日期】和【指令遵循能力】。"):
        st.session_state.response = test_model()

    # 选择标准能力，确定本次生成任务使用的prompt
    cap_chosen = st.selectbox("选择想评估的能力", [caps[i]['cap_name'] for i in range(len(caps))])
    prompt_default = [prompt for prompt in prompts if prompt['cap'] == cap_chosen][0]['prompt']

    # # 选择素材
    # folder_path = "./materials"
    # items = os.listdir(folder_path)
    # materials = [item.split('.')[0] for item in items]
    # mat_chosen = st.selectbox(f'请选择需要做【{cap_chosen}】的素材', materials)
    # with open(folder_path + '/' + mat_chosen + '.txt', 'r', encoding='utf-8') as f:  # 当前只支持后缀为.txt的素材
    #     mat_text_chosen = f.read()

    def save_prompt():
        st.success(
            f"能力【{cap_chosen}】的Prompt模板已保存，保存时间为：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 设定prompt
    st.subheader(':blue[2. Prompt设定]')
    prompt_applied = st.text_area('输入Prompt', prompt_default, height=200, label_visibility='collapsed')
    # 保存当前编辑后的模板
    if st.button('保存当前Prompt', key='save_prompt', on_click=save_prompt):
        prompts.insert(0, {
            "cap": cap_chosen,
            "prompt": prompt_applied,
            "save_time": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
        with open(filename['prompts'], 'w', encoding='utf-8') as f:
            json.dump(prompts, f, ensure_ascii=False)
    st.toggle("配置变量值", help="须在prompt中将变量用{}表示出来，且必须保证至少有一个变量！", key="var_config")
    if st.session_state["var_config"] == 1:
        pattern = r"\{(.*?)\}"
        variables = re.findall(pattern, prompt_applied)
        text_filled = {}
        for var in variables:
            text_filled[f"{var}"] = st.text_area(f"请输入变量【{var}】的值：", height=30)
        prompt_applied = prompt_applied.format(**text_filled)

st.markdown('#### <div style="text-align: center;">操作台</div>', unsafe_allow_html=True)

col_input, col_output = st.columns([1, 1])
with col_input:
    with st.container(height=600, border=True):
        st.markdown('#### <b>原文</b>', unsafe_allow_html=True)
        if st.toggle("引用素材", value=True):
            # 选择素材
            folder_path = "./materials"
            items = os.listdir(folder_path)
            materials = [item.split('.')[0] for item in items]
            mat_chosen = st.selectbox(f'请选择需要做【{cap_chosen}】的素材', materials)
            with open(folder_path + '/' + mat_chosen + '.txt', 'r', encoding='utf-8') as f:  # 当前只支持后缀为.txt的素材
                mat_text_chosen = f.read()
            st.caption('<font color="blue"><i>' + mat_text_chosen + '</i></font>', unsafe_allow_html=True)
        else:
            mat_text_chosen = st.text_area("输入素材", value="", height=500)

# API入参配置
input_LLM = f"{prompt_applied} \n 【{mat_text_chosen}】"
api_configs = api_config(company_chosen, model_chosen, input_LLM)

with st.container(height=100, border=False):
    col_gen,  col_rating, col_others, col_caption = st.columns([6, 1, 1, 8])
    with col_gen:
        # 调取接口
        def response_api():
            return requests.post(params=api_configs["params"],
                                 url=api_configs["url"],
                                 headers=api_configs["headers"],
                                 json=api_configs["body"])

        def update_response():
            st.session_state.response = response_api()
        st.button('生成内容', on_click=update_response)
    with col_caption:
        st.caption(f"当前模型：<b>{model_chosen}</b><br>当前评估能力：<b>{cap_chosen}</b>", unsafe_allow_html=True)
        if st.session_state.response is not None:
            # 进一步确认 response 是 HTTP 响应对象
            if isinstance(st.session_state.response, requests.Response):
                # 现在可以安全地访问 .status_code 和其他属性了
                st.caption(f"网络连接状态：{st.session_state.response.status_code}")
            else:
                st.caption("响应对象不是有效的 HTTP 响应。")
        else:
            pass

# 展示输出结果
with col_output:
    with st.container(height=600):
        with st.container(height=50, border=False):
            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown('#### <b>输出</b>\n', unsafe_allow_html=True)
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
        # if company_chosen == "Baidu":
        #     st.write(response.json()["result"])
        # elif company_chosen == "Anthropic":
        #     st.write(response.json()["content"][0]["text"])
        # elif company_chosen == "Hong Corp.":
        #     st.write(response.json()["response"])
        # else:
        #     st.write_stream(stream_data(resp_trans(response.text, encoder=encoding)))

        # 确保响应对象不是 None 且为有效的 HTTP 响应对象
        if st.session_state.response is not None and isinstance(st.session_state.response, requests.Response):
            # 确保HTTP请求成功
            if st.session_state.response.status_code == 200:
                try:
                    # 根据不同的公司选择，处理并展示响应内容
                    if company_chosen == "Baidu":
                        st.write(st.session_state.response.json().get("result", "无结果"))
                    elif company_chosen == "Anthropic":
                        content = st.session_state.response.json().get("content")
                        if content and isinstance(content, list) and len(content) > 0:
                            st.write(content[0].get("text", "无文本内容"))
                    elif company_chosen == "Hong Corp.":
                        st.write(st.session_state.response.json().get("response", "无响应"))
                    else:
                        # 对于其他公司的处理，确保编码器正确设置
                        response_text = st.session_state.response.text
                        st.write_stream(stream_data(resp_trans(response_text, encoder=encoding)))
                except ValueError:
                    st.write("无法解析响应为JSON。")
            else:
                st.write(f"HTTP请求失败，状态码：{st.session_state.response.status_code}")
        else:
            st.write("尚未接收到响应，或响应对象无效。")

# st.write(pd.read_json("./scores.json", encoding='utf-8'))
