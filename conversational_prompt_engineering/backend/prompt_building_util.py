# (c) Copyright contributors to the conversational-prompt-engineering project

# LICENSE: Apache License 2.0 (Apache-2.0)
# http://www.apache.org/licenses/LICENSE-2.0

import json
import os.path

LLAMA_END_OF_MESSAGE = "<|eot_id|>"

LLAMA_START_OF_INPUT = '<|begin_of_text|>'


def _get_llama_header(role):
    return "<|start_header_id|>" + role + "<|end_header_id|>"

class TargetModelHandler:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            with open(os.path.join(os.path.dirname(__file__), "prompt_formats.json"), 'r') as f:
                cls._instance.data = json.load(f)
        return cls._instance

    def get_models(self):
        model_names = self.data.keys()
        model_short_names_and_full_names = [{"full_name": key, "short_name": self.data[key]['short_name']} for key in
                                            model_names]
        return model_short_names_and_full_names

    def format_prompt(self, model, prompt, texts_and_outputs):
        if 'prompt_formats' not in self.data[model]:
            raise Exception(f"prompt format is not defined for model {model}")
        model_vars = self.data[model]['prompt_formats']
        prompt = self.build_instruction(model_vars, prompt)
        if len(texts_and_outputs) > 0:
            if len(texts_and_outputs) > 1:  # we already have at least two approved summary examples
                prompt += "Here are some typical text examples and their corresponding desired outputs."
            else:
                prompt += "Here is an example of a typical text and its desired output."
            for i, item in enumerate(texts_and_outputs):
                if i > 0:
                    prompt += model_vars.get('few_shot_examples_prefix', '')
                text = item['text']
                output = item['output']
                prompt += self.build_icl_example(model_vars, output, text)
            prompt += model_vars.get('test_example_prefix', '')
        prompt += self.build_test_example(model_vars)
        return prompt

    def build_test_example(self, model_vars):
        return f"{model_vars.get('input_prefix', '')}" + model_vars.get('test_example_placeholder',
                                                                        '') + f"{model_vars.get('end_of_message', '')}" \
               + f"{model_vars.get('output_prefix', '')}{model_vars.get('end_of_input', '')}"

    def build_icl_example(self, model_vars, output, text):
        return f"\n\n{model_vars.get('input_prefix', '')}{model_vars.get('test_example_placeholder', '').format(text=text)}{model_vars.get('end_of_message', '')}" \
               f"{model_vars.get('output_prefix', '')}{output}{model_vars.get('end_of_message', '')}"

    def build_instruction(self, model_vars, prompt):
        return ''.join([model_vars.get('start_of_input', ''), model_vars.get('system_message', ''),
                        model_vars.get('prompt_prefix', ''), prompt, model_vars.get('prompt_suffix', '') + "\n\n"])


def remove_tags_from_zero_shot_prompt(prompt, model_type):
    if model_type == "llama-3":
        return prompt.replace("<|begin_of_text|><|start_header_id|>user<|end_header_id|>\n\n", "").replace(
            "<|eot_id|><|start_header_id|>assistant<|end_header_id|>", "")
    elif model_type == "mixtral":
        return prompt.replace("[INST] ", ""). replace("[\INST]", "")
    elif model_type == "granite":
        print("Granite prompt is not cleaned up")
        return prompt

