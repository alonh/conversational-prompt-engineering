import json
import logging
import time
import os
import json
import datetime

import pandas as pd
from genai.schema import ChatRole

from conversational_prompt_engineering.util.bam import BamGenerate

LLAMA_END_OF_MESSAGE = "<|eot_id|>"

LLAMA_START_OF_INPUT = '<|begin_of_text|>'


def extract_delimited_text(txt, delims):
    if type(delims) is str:
        delims = [delims]
    for delim in delims:
        if delim in txt:
            begin = txt.index(delim) + len(delim)
            end = begin + txt[begin:].index(delim)
            return txt[begin:end]
    return txt  # delims not found in text


def _get_llama_header(role):
    return "<|start_header_id|>" + role + "<|end_header_id|>"


class ChatManagerBase:
    def __init__(self, bam_api_key, model, conv_id) -> None:
        with open("backend/bam_params.json", "r") as f:
            params = json.load(f)
        logging.info(f"selected {model}")
        logging.info(f"conv id: {conv_id}")
        bam_params = params['models'][model]
        bam_params['api_key'] = bam_api_key
        bam_params['api_endpoint'] = params['api_endpoint']
        self.bam_client = BamGenerate(bam_params)
        self.conv_id = conv_id
        self.dataset_name = None
        self.state = None
        self.timing_report = []

        self.out_dir = f'_out/{self.conv_id}/{datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")}'
        logging.info(f"output is saved to {self.out_dir}")

        os.makedirs(self.out_dir, exist_ok=True)

    def save_prompts_and_config(self, approved_prompts):
        chat_dir = os.path.join(self.out_dir, "chat")
        os.makedirs(chat_dir, exist_ok=True)
        with open(os.path.join(chat_dir, "prompts.json"), "w") as f:
            # if self.state == ConversationState.CONFIRM_PROMPT:
            #     approved_prompts = approved_prompts[:-1]  # the last prompt is not confirmed yet
            # for p in approved_prompts:
            #     p['prompt_with_format'] = build_few_shot_prompt(p['prompt'], [],
            #                                                     self.bam_client.parameters['model_id'])
            #     p['prompt_with_format_and_few_shots'] = build_few_shot_prompt(p['prompt'], self.approved_summaries[
            #                                                                                :self.validated_example_idx],
            #                                                                   self.bam_client.parameters[
            #                                                                       'model_id'])
            json.dump(approved_prompts, f)
        with open(os.path.join(chat_dir, "config.json"), "w") as f:
            json.dump({"model": self.bam_client.parameters['model_id'], "dataset": self.dataset_name}, f)

    def save_chat_html(self, chat, file_name):
        chat_dir = os.path.join(self.out_dir, "chat")
        os.makedirs(chat_dir, exist_ok=True)
        df = pd.DataFrame(chat)
        df.to_csv(os.path.join(chat_dir, f"{file_name.split('.')[0]}.csv"), index=False)
        with open(os.path.join(chat_dir, file_name), "w") as html_out:
            content = "\n".join(
                [f"<p><b>{x['role'].upper()}: </b>{x['content']}</p>".replace("\n", "<br>") for x in chat])
            header = "<h1>IBM Research Conversational Prompt Engineering</h1>"
            html_template = f'<!DOCTYPE html><html>\n<head>\n<title>CPE</title>\n</head>\n<body style="font-size:20px;">{header}\n{content}\n</body>\n</html>'
            html_out.write(html_template)

    def _add_msg(self, chat, role, msg):
        chat.append({'role': role, 'content': msg})

    def _format_chat(self, chat):
        if 'mixtral' in self.bam_client.parameters['model_id']:
            bos_token = '<s>'
            eos_token = '</s>'
            chat_for_mixtral=[]
            prev_role = None
            for m in chat:
                if m["role"] == prev_role:
                    chat_for_mixtral[-1]["content"] += "\n"+m["content"]
                else:
                    chat_for_mixtral.append(m)
                prev_role = m["role"]

            for m in chat_for_mixtral:
                if m["role"] == 'user':
                    m["content"] = 'user: ' + m["content"]
                elif m["role"] == 'system':
                    m["role"] = 'user'
                    m["content"] = 'system: ' + m["content"]

            prompt = bos_token
            for m in chat_for_mixtral:
                if m['role'] == 'user':
                    prompt += '[INST] ' + m['content'] + ' [/INST] '
                else:
                    prompt += m['content'] + eos_token + ' '
            return prompt
        elif 'llama' in self.bam_client.parameters['model_id']:
            msg_str = LLAMA_START_OF_INPUT
            for m in chat:
                msg_str += _get_llama_header(m['role']) + "\n\n" + m['content'] + LLAMA_END_OF_MESSAGE
            msg_str += _get_llama_header(ChatRole.ASSISTANT)
            return msg_str
        else:
            raise Exception(f"model {self.bam_client.parameters['model_id']} not supported")

    def print_timing_report(self):
        df = pd.DataFrame(self.timing_report)
        logging.info(df)
        logging.info(f"Average processing time: {df['time'].mean()}")
        self.timing_report = sorted(self.timing_report, key=lambda row: row['time'])
        logging.info(f"Highest processing time: {self.timing_report[-1]}")
        logging.info(f"Lowest processing time: {self.timing_report[0]}")

    def _get_assistant_response(self, chat, max_new_tokens=None):
        conversation = self._format_chat(chat)
        start_time = time.time()
        generated_texts = self.bam_client.send_messages(conversation, max_new_tokens=max_new_tokens)
        elapsed_time = time.time() - start_time
        timing_dict = {"state": self.state, "context_length": len(conversation),
                       "output_length": sum([len(gt) for gt in generated_texts]), "time": elapsed_time}
        logging.info(timing_dict)
        self.timing_report.append(timing_dict)
        agent_response = ''
        for txt in generated_texts:
            if any([f'<|{r}|>' in txt for r in [ChatRole.SYSTEM, ChatRole.USER]]):
                agent_response += txt[: txt.index('<|')]
                break
            agent_response += txt
        logging.info(f"got response from model: {agent_response}")
        return agent_response.strip()
