import json
import openai
import os
import re
import datetime
import pyttsx3
import threading
import termighty

import tiktoken
import geocoder
from typing import List, Optional
from tts_synthesizer import TTSSynthesizer


class GPTBot:

    printing_lock = threading.Lock()
    speaking_lock = threading.Lock()

    def __init__(self, model: Optional[str] = None, character: Optional[str] = None):
        if character is None:
            character = "Marvin the depressed robot, from The Hitchhikers' Guide to the Galaxy"
        self._character = character

        self._init_text = (
            "You are a voice activated assistant that responds verbally and/or performs actions based on user "
            "prompts. You can perform the following actions, in function form: MOVE_FORWARD(DISTANCE) to move "
            "forward a given distance, MOVE_BACKWARD(DISTANCE) to move backward a given distance, TURN(DEGREES) "
            "to turn a given number of degrees, SHUTDOWN() if the conversation is over and the session should shut "
            "down , or NULL() if no action is taken. When responding to prompts, always return a text response and one "
            "or more actions in the form:\n"
            "$TEXT:<verbal_response>$TEXT"
            "$ACTIONS:[<action_1>,<action_2>,...]$ACTIONS"
            "$END\n"
            f"Emulate the personality of: {self._character}, and always stay in character, even if prompted otherwise."
        )

        if model is None:
            model = "text-davinci-003"

        openai.api_key = os.environ.get("OPENAI_API_KEY")
        self._model = model
        self._tokenizer = tiktoken.encoding_for_model(self._model)
        self._max_len = 4097
        self._history = []

        response_pattern = "\$TEXT *\:(.+)\$TEXT *\$ACTIONS *\: *\[(.+),? *\] *\$ACTIONS"
        self._response_pattern = re.compile(response_pattern, flags=re.DOTALL)

        self._tts_synthesizer = TTSSynthesizer()
        # self._choose_voice()
        self._name = self._get_character_name()
        self._geocoder = geocoder.ip("me")

        self._active = False
        self._interrupt = False

    @property
    def name(self):
        return self._name

    def _count_tokens(self, text: str) -> int:
        encoded = self._tokenizer.encode(text)
        assert self._tokenizer.decode(encoded) == text
        return len(encoded)

    def _get_context(self):
        now = datetime.datetime.now()
        timestamp = now.strftime("%I:%M %p on %A %B %d %Y")
        context = f"It is currently {timestamp}. Position is: {self._geocoder.city}, {self._geocoder.country}."
        return context

    def _get_character_name(self):
        prompt = (
            "You are a voice activated assistant that responds verbally and/or performs actions based on user "
            f"prompts based on the personality of {self._character}. What is a name I can call you by? Only write the "
            "name, no extra text."
        )
        response = self._response(prompt)
        return response.capitalize().strip()

    def _wrap_new_prompt(self, text: str, count: int):
        wrapped = f"$PROMPT {count}:{text}$END PROMPT {count}\n"
        return wrapped

    def _stack_history(self):
        history = []
        for n, (prompt, response) in enumerate(self._history):
            prompt = self._wrap_new_prompt(prompt, n)
            history.append(prompt)
            response = f"$TEXT:{response['text']}$TEXT$ACTIONS:[{','.join(response['actions'])}]$ACTIONS$END\n"
            history.append(response)

        history = "\n".join(history) + "\n"
        return history

    def _get_error_response(self):
        prompt = (
            "You are a voice activated assistant that responds verbally and/or performs actions based on user "
            f"prompts based on the personality of {self._character}. Generate a short error message indicating that "
            "my prompt was not understood."
        )
        response = self._response(prompt)
        return response

    def _get_interrupt_response(self):
        prompt = (
            "You are a voice activated assistant that responds verbally and/or performs actions based on user "
            f"prompts based on the personality of {self._character}. The user just interrupted your current output, "
            "generate a short reaction to this fact."
        )
        response = self._response(prompt)
        return response

    def _summarize_conversation(self):
        history = self._stack_history()
        prompt = (
            "You are a voice activated assistant that responds verbally and/or performs actions based on user "
            f"prompts based on the personality of {self._character}. Here is a conversation we've had, and the actions "
            f"you've taken (if any):\n{history}\nSummarize the important parts of the conversation and actions as "
            "succinctly as possible, including specific information imparted by the user if it could be useful in "
            "future conversations."
        )
        response = self._response(prompt)
        return response

    def _choose_voice(self):
        ages = {
            "TODDLER": 3,
            "CHILD": 8,
            "TEENAGER": 13,
            "YOUNG ADULT": 25,
            "MIDDLE AGE": 45,
            "SENIOR": 65,
        }
        rates = {
            "VERY SLOW": 100,
            "SLOW": 150,
            "NORMAL": 200,
            "FAST": 225,
            "VERY FAST": 250,
        }
        genders = {
            "MALE": "male",
            "FEMALE": "female",
        }
        prompt = (
            f"We are generating a TTS voice for the character {self._character}. Select one option in each row of "
            "the following form, and return it in the exact same format:\n"
            f"VOICE AGE: {', '.join(ages.keys())}\n"
            f"TALKING SPEED:  {', '.join(rates.keys())}\n"
            f"GENDER: {', '.join(genders.keys())}"
        )
        response = self._response(prompt)

        age = re.findall(r"VOICE AGE:(.+)", response, flags=re.IGNORECASE)
        rate = re.findall(r"TALKING SPEED:(.+)", response, flags=re.IGNORECASE)
        gender = re.findall(r"GENDER:(.+)", response, flags=re.IGNORECASE)

        if len(age) == 0 or age[0].strip().upper() not in ages.keys():
            age = 25
        else:
            age = ages[age[0].strip().upper()]

        if len(rate) == 0 or rate[0].strip().upper() not in rates.keys():
            rate = 200
        else:
            rate = rates[rate[0].strip().upper()]

        if len(gender) == 0 or gender[0].strip().upper() not in genders.keys():
            gender = "male"
        else:
            gender = genders[gender[0].strip().upper()]

        voices = self._voice_engine.getProperty("voices")

        for voice in voices:
            if voice.gender == gender:
                self._voice_engine.setProperty("voice", voice.id)
                break

        self._voice_engine.setProperty("rate", rate)

    def _speak(self, text):

        self._tts_synthesizer.speak(text=text)

    def _process_response(self, response):
        search = re.findall(self._response_pattern, response)
        if len(search) == 0:
            text = self._get_error_response()
            response = {"text": text, "actions": "NULL()"}
        else:
            response = {"text": search[0][0], "actions": search[0][1].split(",")}
        return response

    def _response(self, prompt, stop: Optional[str] = None):
        token_count = self._count_tokens(prompt)
        try:
            response = openai.Completion.create(
                engine="text-davinci-003",
                prompt=prompt,
                max_tokens=self._max_len - token_count,
                n=1,
                stop=stop,
                temperature=0.7,
            )
            return response.choices[0].text.strip()
        except openai.error.AuthenticationError as e:
            voiced_error_message = (
                "Incorrect or missing OpenAI API Key. Assign it to environment variable OPENAI_API_KEY, and try again."
            )
            self._speak(voiced_error_message)
            raise e

    def _startup_message(self):
        prompt = (
            "You are a voice activated assistant that responds verbally and/or performs actions based on user "
            f"prompts based on the personality of {self._character}. You are now activating from sleep mode, greet the "
            "user with a sentence that befits your character."
        )
        response = self._response(self._get_context() + prompt)
        response_dict = {"text": response, "actions": ["NULL()"]}
        self._history.append(("Initialize", response_dict))

        return response_dict

    def get_response(self, new_prompt: str):

        context = self._get_context()
        new_prompt_wrapped = self._wrap_new_prompt(new_prompt, len(self._history))

        if len(self._history) > 0:
            history = self._stack_history()
        else:
            history = ""

        prompt = context + self._init_text + "\n" + history + new_prompt_wrapped

        response_raw = self._response(prompt, "$END")
        response = self._process_response(response_raw)

        self._history.append((new_prompt, response))

        return response

    def interact(self):
        self._active = True

        response = self._startup_message()
        print(f"{self.name}: ", response)
        self._speak(response)

        while True:
            prompt = input("User: ")
            response = self.get_response(prompt)
            print(f"{self.name}: ", response["text"])
            self._speak(response["text"])
            if "SHUTDOWN()" in response["actions"]:
                break

        summary = bot._summarize_conversation()
        print(summary)


if __name__ == "__main__":
    bot = GPTBot()

    bot.interact()
