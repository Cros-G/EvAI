import streamlit as st
import re
import time
import requests
import json
from tool_func import resp_trans, stream_data

url = "https://api.anthropic.com/v1/messages"
api_key = "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"
headers = {
    "x-api-key": api_key
}
body = {
    "model": "claude-3-opus-20240229",
    "max_tokens": 4096,
    "messages": [
        {"role": "user", "content": "介绍北京"},
    ],
    "stream": True
}
response = requests.post(url=url, headers=headers, json=body)

with st.container(height=600):
    # st.markdown(response.json()["choices"][0]["message"]["content"], unsafe_allow_html=True) # 供单步调用
    st.write_stream(stream_data(resp_trans(response.text, encoder='utf-8')))
