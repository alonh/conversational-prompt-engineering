from collections import Counter

import streamlit as st
import os
import pandas as pd

from conversational_prompt_engineering.backend.evaluation import get_prompts_to_evaluate, summarize

NUM_EXAMPLES = 5


def display_text():
    text = st.session_state.generated_data[st.session_state.count]['text']
    st.write(text)


def next_text():
    if st.session_state.count + 1 >= len(st.session_state.generated_data):
        st.session_state.count = 0
    else:
        st.session_state.count += 1


def previous_text():
    if st.session_state.count - 1 < 0:
        st.session_state.count = len(st.session_state.generated_data) - 1
    else:
        st.session_state.count -= 1


def display_summary(side):
    summary = st.session_state.generated_data[st.session_state.count][side]
    st.write(summary)


def display_selected(selection):
    if st.session_state.generated_data[st.session_state.count]['selected_side'] and \
            st.session_state.generated_data[st.session_state.count]['selected_side'] == selection:
        st.write(":+1:")


def select(prompt, side):
    selected_prompt = "0" if prompt == st.session_state.prompts[0]['prompt'] else "1"
    st.session_state.generated_data[st.session_state.count]['selected_prompt'] = selected_prompt
    st.session_state.generated_data[st.session_state.count]['selected_side'] = side


def calculate_results():
    counter = Counter([d['selected_prompt'] for d in st.session_state.generated_data if d['selected_prompt'] is not None])
    return counter


def reset_evaluation():
    st.session_state.generated_data = []
    st.session_state.evaluate_clicked = False


def run():
    # present instructions
    st.title("IBM Research Conversational Prompt Engineering - Evaluation")
    with st.expander("Instructions (click to expand)"):
        st.markdown("1) First, upload test data in csv format, containing a single column named text.")
        st.markdown(f"2) After file is uploaded, {NUM_EXAMPLES} examples are chosen at random for evaluation.")
        st.markdown("3) Below you can see the prompts that were curated during your chat and will be used for evaluation.")
        st.markdown(f"4) Next, click on ***Summarize***. Each prompt will be used to generate a summary for each of the {NUM_EXAMPLES} examples.")
        st.markdown("5) After the summaries are generated, select the best summary for each text.")
        st.markdown("6) When you are done, click on ***Submit*** to present the evaluation scores.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Reset evaluation"):
            reset_evaluation()

    if 'BAM_APIKEY' in os.environ:
        st.session_state['key'] = os.environ['BAM_APIKEY']

    # upload test data
    with col2:
        uploaded_file = st.file_uploader("Upload test file", type={"csv"})
        if uploaded_file is not None:
            df = pd.read_csv(uploaded_file)
            df = df.sample(NUM_EXAMPLES) ###
            st.empty()
            texts = df.text.tolist()

    # get prompts to evaluate
    st.session_state.prompts = st.session_state.manager.get_prompts()
    st.session_state.prompts = get_prompts_to_evaluate(st.session_state.prompts)

    if 'count' not in st.session_state:
        st.session_state.count = 0

    # show prompts
    col1, col2 = st.columns(2)
    with col1:
        st.text_area("Prompt 1", st.session_state.prompts[0]['prompt'])

    with col2:
        st.text_area("Prompt 2", st.session_state.prompts[1]['prompt'])

    # show summarize button
    st.session_state.evaluate_clicked = False
    if uploaded_file is not None:
        st.session_state.evaluate_clicked = st.button("Summarize")

    # summarize texts using prompts
    if st.session_state.evaluate_clicked:
        generated_data_mixed, generated_data_ordered = summarize(st.session_state.prompts, texts)
        st.session_state.generated_data = generated_data_mixed
        for row in st.session_state.generated_data:
            row['selected_side'] = None
            row['selected_prompt'] = None

    # showing texts and summaries to evaluate
    if 'generated_data' in st.session_state and len(st.session_state.generated_data) > 0:
        display_text()

        col1, col2 = st.columns(2)
        st.write(f"{st.session_state.count+1}/{len(st.session_state.generated_data)}")
        with col1:
            if st.button("⏮️ Previous", on_click=previous_text):
                pass
            display_summary("0")
            if st.button("Select", key="left", on_click=select, args=(st.session_state.generated_data[st.session_state.count]["0_prompt"], "0", )):
                pass
            display_selected("0")

        with col2:
            if st.button("Next ⏭️", on_click=next_text):
                pass
            display_summary("1")
            if st.button("Select", key="right", on_click=select, args=(st.session_state.generated_data[st.session_state.count]["1_prompt"], "1", )):
                pass
            display_selected("1")

        # if all([row['selected_prompt'] for row in st.session_state.generated_data]):
        finish_clicked = st.button("Submit")
        if finish_clicked:
            # showing aggregated results
            results = calculate_results()
            total_votes = sum(results.values())
            for item in results.most_common():
                st.write(f"Prompt {int(item[0])+1} was chosen {item[1]} {'times' if item[1] > 1 else 'time'} ({100*item[1]/total_votes}%)")


if __name__ == "__main__":
    run()
