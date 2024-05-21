import logging
import os

import pandas as pd
import streamlit as st
from streamlit_js_eval import streamlit_js_eval

from conversational_prompt_engineering.backend.double_chat_manager import DoubleChatManager
from conversational_prompt_engineering.backend.manager import Manager, Mode
from conversational_prompt_engineering.util.csv_file_utils import read_user_csv_file

from st_pages import Page, show_pages, hide_pages

st.set_page_config(layout="wide")

show_pages(
    [
        Page("cpe.py", "Chat", ""),
        Page("pages/evaluation.py", "Evaluate", ""),
    ]
)


def old_reset_chat():
    st.session_state.manager = Manager(st.session_state.mode, st.session_state.key)
    st.session_state.messages = []


def new_cycle():
    # 1. create the manager if necessary
    if "manager" not in st.session_state:
        st.session_state.manager = DoubleChatManager(bam_api_key=st.session_state.key, model=st.session_state.model)
    manager = st.session_state.manager

    # 2. hide evaluation option in sidebar
    # prompts = manager.get_prompts()

    # if len(prompts) < 2:
    #     hide_pages(["Evaluate"])

    # 3. layout reset and upload buttons in 2 columns
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Reset chat"):
            streamlit_js_eval(js_expressions="parent.window.location.reload()")
    if manager.enable_upload_file:
        with col2:
            if uploaded_file := st.file_uploader("Upload text examples csv"):
                manager.process_examples(read_user_csv_file(uploaded_file))

    # 4. user input
    if user_msg := st.chat_input("Write your message here"):
        manager.add_user_message(user_msg)

    # 5. render the existing messages
    for msg in manager.user_chat:
        with st.chat_message(msg['role']):
            st.write(msg['content'])

    # 6. generate and render the agent response
    msg = manager.generate_agent_message()
    if msg is not None:
        with st.chat_message(msg['role']):
            st.write(msg['content'])


def old_cycle():
    def show_and_call(prompt, show_message=True):
        st.session_state.messages.append({"role": "user", "content": prompt, "show": show_message})
        if show_message:
            with st.chat_message("user"):
                st.markdown(prompt)

        with st.chat_message("assistant"):
            response = st.session_state.manager.call(
                messages=[
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages
                ]
            )
            st.write(response)
        st.session_state.messages.append({"role": "assistant", "content": response, "show": True})

    if "key" in st.session_state:
        if st.button("Reset chat"):
            reset_chat()

        mode = st.radio(label="Mode", options=["Basic", "Advanced"],
                        captions=["basic zero-shot -> few-shot (default)",
                                  "basic zero-shot -> custom zero-shot -> few-shot"])

        if "mode" not in st.session_state:
            st.session_state.mode = Mode.Basic

        old_mode = st.session_state.mode
        if mode == "Basic":
            st.session_state.mode = Mode.Basic
        else:
            st.session_state.mode = Mode.Advanced
        new_mode = st.session_state.mode
        if old_mode != new_mode:
            old_reset_chat()

        if "manager" not in st.session_state:
            st.session_state.manager = Manager(st.session_state.mode, st.session_state.key)

        if "messages" not in st.session_state:
            st.session_state.messages = []

        for message in st.session_state.messages:
            if message["show"]:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
        if 'messages' in st.session_state and len(st.session_state.messages) == 0:
            show_and_call(f"hi", show_message=False)  # {threading.get_ident()}
        # st.write("Hi, please provide your BAM API key")
        if prompt := st.chat_input("What is up?"):
            show_and_call(prompt)


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

st.title("IBM Research Conversational Prompt Engineering")
if 'BAM_APIKEY' in os.environ:
    st.session_state['key'] = os.environ['BAM_APIKEY']

if 'BAM_APIKEY' not in os.environ and "key" not in st.session_state:
    with st.form("my_form", clear_on_submit=True):
        st.write("Welcome to IBM Research Conversational Prompt Engineering service.")
        st.write(
            "This service is intended to help users build an effective prompt, tailored to their specific summarization use case, through a simple chat with an LLM.")
        st.write(
            "To make the most out of this service, it would be best to prepare in advance 3 *input* examples, that represent your use case.")
        st.write("For more information feel free to contact us in slack via #foundation-models-lm-utilization.")
        st.write(
            "This assistant system uses BAM to serve LLMs. Do not include PII or confidential information in your responses.")
        st.write("To proceed, please provide your BAM API key and select a model.")
        key = st.text_input(label="BAM API key")
        model = st.radio(label="Select model", options=["llama3", "mixtral"],
                         captions=["Recommended for most use-cases",
                                   "Recommended for very long documents"])
        submit = st.form_submit_button()
        if submit:
            st.session_state.key = key
            st.session_state.model = model

if 'key' in st.session_state:
    new_cycle()
    # old_cycle()
