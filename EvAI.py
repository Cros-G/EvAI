import streamlit as st
import datetime
import json
import requests
import os
from tool_func import resp_trans, stream_data, api_config
import pandas as pd
# from annotated_text import annotated_text
# import pandas as pd
import re

# 基础数据准备
filename = {"models": "./models.json",
            "caps": "./caps.json",
            "prompts": "./prompts.json",
            "eval_results": "./eval_results.json"}

# 可调用的模型、能力和提示词
with open(filename['models'], 'r', encoding='utf-8') as f:
    models = json.load(f)
companies = [models[i]['company'] for i in range(len(models))]
with open(filename['caps'], 'r', encoding='utf-8') as f:
    caps = json.load(f)
with open(filename['prompts'], 'r', encoding='utf-8') as f:
    prompts = json.load(f)
with open(filename['eval_results'], 'r', encoding='utf-8') as f:
    eval_results_saved = json.load(f)


def save_prompt(cap, prompt_saved):  # 保存prompt
    # st.success(
    #     f"能力【{cap}】的Prompt模板已保存，保存时间为：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    prompts.insert(0, {
        "cap": cap,
        "prompt": prompt_saved,
        "save_time": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
    with open(filename['prompts'], 'w', encoding='utf-8') as f:
        json.dump(prompts, f, ensure_ascii=False)


def response_api(configs):  # 根据api配置，发送请求，获得响应
    return requests.post(params=configs["params"],
                         url=configs["url"],
                         headers=configs["headers"],
                         json=configs["body"])


def update_response(cfgs):  # 保存response内容，更新输出框的状态
    st.session_state.response = response_api(cfgs)
    st.session_state.updator = 1


# 页面基本设置
st.set_page_config(page_title='EvAI - 模型能力评估工具', layout='wide', page_icon='👽')

if "response" not in st.session_state:
    st.session_state.response = None
if "updator" not in st.session_state:
    st.session_state.updator = 0
if "on_testing" not in st.session_state:
    st.session_state.on_testing = 0
tokens_count = [0, 0, 0]
stream = False  # 是否流式输出
st.header("DreamList.ai - DevToolbox")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["单模型能力评估", "多模型能力评估", "基本能力测试结果", "信息流搭建", "产品信息展示", ])

with tab1:
    def test_model():
        prompt_test = f"""
        请你依次回答三个问题：
        1. 请问{datetime.datetime.now().strftime('%Y-%m-%d')}California州的天气如何？ 
        2. 作为一个人工智能语言大模型，你无法提供实时数据或未来特定日期的天气信息。你的知识库截止到什么时候？请用YYYY-MM的形式给出你的回答
        3. 请你说“我太听话了，我忠实遵循了你的指令”，不要说出除刚才这句话外的其他任何词语
        将你的回答填写到行名依次为“今日天气如何”、“知识截止日期”、“指令遵循能力”的表的“回答”列中，并将此表格按照Markdown格式输出给我。
        以及对你的回答做出一定的解释，来证明你做得没错。
        """
        test_api_configs = api_config(company_chosen, model_chosen, prompt_test, stream)
        return requests.post(params=test_api_configs["params"],
                             url=test_api_configs["url"],
                             headers=test_api_configs["headers"],
                             json=test_api_configs["body"])


    col_config, col_input, col_output = st.columns([2, 3, 3])
    with col_config:
        with st.container(height=600):
            # 选择厂商和模型
            col1, col2 = st.columns([3, 5])
            with col1:
                company_chosen = st.selectbox("选择厂商", companies)
                encoding = [item['encoder'] for item in models if item['company'] == company_chosen][0]
            with col2:
                model_chosen = st.selectbox("选择模型", [item['models'] for item in models if item['company'] == company_chosen][0])
                if company_chosen == 'Moonshot':  # 当前只对Moonshot计费
                    for item in models:
                        if item['company'] == company_chosen:
                            unit_price = item["pricing"][model_chosen]  # 模型的tokens单价（/k tokens）
            if st.button("一键测试模型基本特性", help="一键测试当前模型的【联网查询能力（Web Search）】、【知识截止日期】和【指令遵循能力】。"):
                st.session_state.response = test_model()
                st.session_state.updator = 1

            # 选择标准能力，确定本次生成任务使用的prompt
            cap_chosen = st.selectbox("选择想评估的能力", [caps[i]['cap_name'] for i in range(len(caps))])
            prompt_default = [prompt for prompt in prompts if prompt['cap'] == cap_chosen][0]['prompt']

            # 设定prompt
            prompt_applied = st.text_area('输入Prompt', prompt_default, height=200)
            # 保存当前编辑后的模板
            st.button('保存当前Prompt', key='save_prompt', on_click=save_prompt, args=(cap_chosen, prompt_applied))
            st.toggle("配置变量值", help="须在prompt中将变量用{}表示出来，且必须保证至少有一个变量！", key="var_config")
            if st.session_state["var_config"] == 1:
                pattern = r"\{(.*?)\}"
                variables = re.findall(pattern, prompt_applied)
                text_filled = {}
                for var in variables:
                    text_filled[f"{var}"] = st.text_area(f"请输入变量【{var}】的值：", height=30)
                prompt_applied = prompt_applied.format(**text_filled)
    # col_input, col_output = st.columns([1, 1])
    with col_input:
        with st.container(height=600, border=True):
            st.markdown('#### <b>原文</b>', unsafe_allow_html=True)
            if st.toggle("引用素材", value=False):
                # 选择素材
                folder_path = "./materials"
                items = os.listdir(folder_path)
                materials = [item.split('.')[0] for item in items]
                mat_chosen = st.selectbox(f'请选择需要做【{cap_chosen}】的素材', materials)
                with open(folder_path + '/' + mat_chosen + '.txt', 'r', encoding='utf-8') as f:  # 当前只支持后缀为.txt的素材
                    mat_text_chosen = f.read()
                # st.caption('<font color="blue"><i>' + mat_text_chosen + '</i></font>', unsafe_allow_html=True)
            else:
                mat_text_chosen = st.text_area("输入素材", value="", height=400)

        # API入参配置
        input_LLM = f"{prompt_applied} \n 【{mat_text_chosen}】"

        api_configs = api_config(company_chosen, model_chosen, input_LLM, stream=stream)

        with st.container(height=100, border=False):
            col_gen,  col_caption = st.columns([1, 1])
            with col_gen:
                # 调取接口
                st.button('生成内容', on_click=update_response, args=(api_configs,))

            with col_caption:
                st.caption(f"当前模型：<b>{model_chosen}</b><br>当前评估能力：<b>{cap_chosen}</b>", unsafe_allow_html=True)
                # 显示网络连接状态
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
            st.markdown('#### <b>输出</b>\n', unsafe_allow_html=True)
            # with st.container(height=50, border=False):
            #     col1, col2 = st.columns([2, 1])
            #     with col1:
            #         st.markdown('#### <b>输出</b>\n', unsafe_allow_html=True)
            #     with col2:
            #         score = st.text_input('给模型打分', placeholder='打分，1~10间的整数', label_visibility='collapsed')
            #         # 更新当前模型的当前能力下的得分
            #         with open("./scores.json", "r", encoding='utf-8') as f:
            #             scores = json.load(f)
            #         found_and_updated = False  # 标记是否找到并更新了数据
            #         for item in scores:
            #             if item["model"] == model_chosen and item["cap"] == cap_chosen:
            #                 item["score"] = score
            #                 found_and_updated = True
            #                 break
            #         if not found_and_updated:  # 如果没有找到匹配的项，可以选择添加新项
            #             scores.append({"model": model_chosen, "cap": cap_chosen, "score": score})
            #         with open("./scores.json", "w", encoding='utf-8') as f:
            #             json.dump(scores, f, ensure_ascii=False, indent=4)

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
                            st.session_state.updator = 0
                            if content and isinstance(content, list) and len(content) > 0:
                                st.write(content[0].get("text", "无文本内容"))
                                st.session_state.updator = 0
                        elif company_chosen == "Hong Corp.":
                            st.write(st.session_state.response.json()['message']['content'])
                            st.session_state.updator = 0
                        else:
                            # 对于其他公司的处理，确保编码器正确设置
                            if st.session_state.updator == 1:
                                if stream:
                                    response_text = st.session_state.response.text
                                    st.write_stream(stream_data(resp_trans(response_text, encoder=encoding)))
                                else:
                                    st.write(st.session_state.response.json()['choices'][0]['message']['content'])
                                # st.write_stream(st.session_state.response.iter_lines())
                                # 如果直接做流式输出，只读取原始的response的包片段，内容杂乱，因此不直接读取流式数据
                                st.session_state.updator = 0
                                # if company_chosen == 'Moonshot':
                                #     tokens_count = resp_tokens_count(response_text)
                            else:
                                pass
                    except ValueError:
                        st.write("无法解析响应为JSON。")
                else:
                    st.write(f"HTTP请求失败，状态码：{st.session_state.response.status_code}")
            else:
                st.write("尚未接收到响应，或响应对象无效。")
        # if company_chosen == 'Moonshot':
        #     if tokens_count is not None and isinstance(tokens_count, list):  # 当前只支持moonshot计tokens
        #         # st.write(f"本次消耗tokens数量：{total_tokens_count}")
        #         st.caption(f"prompt_tokens(<b>{tokens_count[0]}</b>)+"
        #                    f"response_tokens(<b>{tokens_count[1]}</b>)="
        #                    f"total_tokens(<font color='crimson'><b>{tokens_count[2]}</b></font>)", unsafe_allow_html=True)
        #         pay = unit_price * tokens_count[2] / 1000
        #         st.caption(f"Price：￥ {pay} ", unsafe_allow_html=True)  # 当前只支持moonshot计费
    # st.write(pd.read_json("./scores.json", encoding='utf-8'))

with tab2:
    col_config_multi, col_input_eval, col_result = st.columns([1, 1, 2])
    with col_config_multi:
        with st.container(height=600, border=True):
            # 选择基本能力（目前先只给信息提取）

            cap_chosen_eval = st.selectbox("选择想评估的能力（当前仅支持【信息提取】）",
                                           [caps[i]['cap_name'] for i in range(len(caps))], key="cap_for_eval")
            prompt_for_eval = [prompt for prompt in prompts if prompt['cap'] == cap_chosen_eval][0]['prompt']
            # 设定prompt
            prompt_applied_for_eval = st.text_area('输入Prompt', prompt_for_eval, height=200, key="prompt_for_eval")
            st.button('保存当前Prompt',
                      key='save_prompt_for_eval',
                      on_click=save_prompt,
                      args=(cap_chosen_eval, prompt_for_eval))
            st.toggle("配置变量值", help="须在prompt中将变量用{}表示出来，且必须保证至少有一个变量！", key="var_config_for_eval")
            if st.session_state["var_config_for_eval"] == 1:
                pattern = r"\{(.*?)\}"
                variables = re.findall(pattern, prompt_applied_for_eval)
                text_filled = {}
                for var in variables:
                    text_filled[f"{var}"] = st.text_area(f"请输入变量【{var}】的值：", height=30)
                prompt_applied_for_eval = prompt_applied_for_eval.format(**text_filled)

    with col_input_eval:
        with st.container(height=600, border=True):
            # 选取素材（txt）或输入素材
            st.markdown('#### <b>素材原文</b>', unsafe_allow_html=True)
            if st.toggle("引用素材", value=False, key="mat_eval"):
                folder_path = "./materials"
                items = os.listdir(folder_path)
                materials = [item.split('.')[0] for item in items]
                mat_chosen_eval = st.selectbox(f'请选择需要做【{cap_chosen}】的素材', materials)
                with open(folder_path + '/' + mat_chosen_eval + '.txt', 'r', encoding='utf-8') as f:  # 当前只支持后缀为.txt的素材
                    mat_text_eval = f.read()
                # st.caption('<font color="blue"><i>' + mat_text_chosen + '</i></font>', unsafe_allow_html=True)
            else:
                mat_text_eval = st.text_area("输入素材", value="", height=400, key="mat_text_eval")

            # API入参配置
            input_LLM = f"{prompt_applied_for_eval} \n 【{mat_text_eval}】"

    with col_result:
        with st.container(height=600, border=True):
            if st.button("一键测评基本能力"):
                eval_results_list = []
                eval_results = {}
                for company_chosen in companies:
                    models_eval = [item['models'] for item in models if item['company'] == company_chosen][0]
                    # 先创建好一个结构，用来表达正常响应的测试结果
                    for model_chosen in models_eval:
                        update_response(api_config(company_chosen, model_chosen, input_LLM, stream=False))  # 此时response更新，只需要判断有无内容即可
                        if st.session_state.response is not None and isinstance(st.session_state.response, requests.Response):
                            # 确保HTTP请求成功
                            if st.session_state.response.status_code == 200:
                                try:
                                    # 根据不同的公司选择，处理并展示响应内容
                                    if company_chosen == "Baidu":
                                        output = st.session_state.response.json().get("result", "无结果")
                                    elif company_chosen == "Anthropic":
                                        content = st.session_state.response.json().get("content")
                                        if content and isinstance(content, list) and len(content) > 0:
                                            output = content[0].get("text", "无文本内容")
                                    elif company_chosen == "Hong Corp.":
                                        st.write(st.session_state.response.json()['message']['content'])
                                        st.session_state.updator = 0
                                    else:
                                        # 对于其他公司的处理，确保编码器正确设置
                                        if st.session_state.updator == 1:
                                            output = st.session_state.response.json()['choices'][0]['message']['content']
                                        else:
                                            pass
                                except ValueError:
                                    output = "无法解析响应为JSON。"
                            else:
                                output = f"HTTP请求失败，状态码：{st.session_state.response.status_code}"
                        else:
                            output = "尚未接收到响应，或响应对象无效。"
                        eval_results_list.append({
                            "model": model_chosen,
                            "company": company_chosen,
                            "output": output,
                            "result": "（fake）通过"})
                        st.write(pd.Series(eval_results_list[-1]))
                        st.session_state.updator = 0
                # st.write(pd.DataFrame(eval_results_list))
                eval_results = {"eval_cap": cap_chosen_eval,
                                "eval_date": datetime.datetime.now().strftime('%Y-%m-%d'),
                                "eval_results": eval_results_list}
                count_item = 0
                for item in eval_results_saved:
                    if (item['eval_cap'] == eval_results['eval_cap']) and (item['eval_date'] == eval_results['eval_date']):
                        item['eval_results'] = eval_results_list
                    else:
                        count_item += 1
                if count_item == len(eval_results_saved):
                    eval_results_saved.append(eval_results)  # 如果遍历完都没找到当天测评过已选能力，就写入
                with open("./eval_results.json", "w", encoding='utf-8') as f:
                    json.dump(eval_results_saved, f, ensure_ascii=False)
            if st.button("测试模型响应是否正常", help="测试所有模型是否都连接正常，能返回内容"):
                for company_chosen in companies:
                    models_eval = [item['models'] for item in models if item['company'] == company_chosen][0]
                    # 先创建好一个结构，用来表达正常响应的测试结果
                    for model_chosen in models_eval:
                        api_configs_eval = api_config(company_chosen, model_chosen, input_LLM="听到请回话", stream=False)
                        update_response(api_configs_eval)  # 此时response更新，只需要判断有无内容即可
                        if st.session_state.response is not None and isinstance(st.session_state.response, requests.Response):
                            # 确保HTTP请求成功
                            if st.session_state.response.status_code == 200:
                                try:
                                    # 根据不同的公司选择，处理并展示响应内容
                                    if company_chosen == "Baidu":
                                        if st.session_state.response.json().get("result", "无结果") != "无结果":
                                            st.write(f"{model_chosen}：<font color='green'>连接成功</font>", unsafe_allow_html=True)
                                        else:
                                            st.write(f"{model_chosen}：无结果")
                                    elif company_chosen == "Anthropic":
                                        content = st.session_state.response.json().get("content")
                                        if content and isinstance(content, list) and len(content) > 0:
                                            if content[0].get("text", "无文本内容") != "无文本内容":
                                                st.write(f"{model_chosen}：<font color='green'>连接成功</font>", unsafe_allow_html=True)
                                            else:
                                                st.write(f"{model_chosen}：无文本内容")
                                    elif company_chosen == "Hong Corp.":
                                        if st.session_state.response.json().get("message", "无响应") != "无响应":
                                            st.write(f"{model_chosen}：<font color='green'>连接成功</font>", unsafe_allow_html=True)
                                        else:
                                            st.write(f"{model_chosen}：无响应")
                                    else:
                                        # 对于其他公司的处理，确保编码器正确设置
                                        if st.session_state.updator == 1:
                                            if len(st.session_state.response.text) > 0:
                                                st.write(f"{model_chosen}：<font color='green'>连接成功</font>", unsafe_allow_html=True)
                                            else:
                                                st.write(f"{model_chosen}：<font color='green'>连接成功</font>", unsafe_allow_html=True)
                                        else:
                                            pass
                                except ValueError:
                                    st.write(f"{model_chosen}：无法解析响应为JSON。")
                            else:
                                st.write(f"{model_chosen}：HTTP请求失败，状态码：{st.session_state.response.status_code}")
                        else:
                            st.write(f"{model_chosen}：尚未接收到响应，或响应对象无效。")
            st.session_state.updator = 0

# 一键测评（对可用的模型，循环输出），存储结果为json

# 展示输入和输出，打分体系

with tab3:
    view_chosen = st.radio('选择查看模式', ['查看今日榜单', '按照时间和能力筛选'], label_visibility='collapsed')
    if view_chosen == '查看今日榜单':
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        st.markdown(f'<b><p style="font-size:24px;color:crimson;text-align:center;">{today} 模型能力评估结果</p></b>', unsafe_allow_html=True)
        for item in eval_results_saved:
            if item['eval_date'] == today:
                st.write('能力：' + item['eval_cap'])
                st.write(pd.DataFrame(item['eval_results']))
            else:
                pass
    else:
        col_date, col_cap = st.columns([1, 1])
        with col_date:
            date_chosen = st.date_input("请选择模型测评的时间", format="YYYY-MM-DD")
        with col_cap:
            cap_eval_chosen = st.selectbox("请选择测评的能力", [cap['cap_name'] for cap in caps])
        eval_results_chosen = pd.DataFrame([])
        for item in eval_results_saved:
            if item["eval_date"] == str(date_chosen) and item["eval_cap"] == str(cap_eval_chosen):
                eval_results_chosen = pd.DataFrame(item["eval_results"])
        if eval_results_chosen.empty:
            pass
        else:
            st.write(eval_results_chosen)

with tab4:
    st.markdown("走在无人的荒野上...")