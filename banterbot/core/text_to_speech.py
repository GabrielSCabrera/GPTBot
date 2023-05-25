import datetime
import os
import threading
import time
from typing import Dict, Generator, List, Optional

import azure.cognitiveservices.speech as speechsdk
from azure.cognitiveservices.speech import SpeechSynthesisOutputFormat

from banterbot import config
from banterbot.utils.text_to_speech_output import TextToSpeechOutput
from banterbot.utils.text_to_speech_word import TextToSpeechWord


class TextToSpeech:
    """
    A class to handle text-to-speech synthesis utilizing Azure's Cognitive Services.
    """

    # Create a lock that prevents race conditions when speaking
    speech_lock = threading.Lock()

    def __init__(
        self,
        output_format: SpeechSynthesisOutputFormat = SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3,
    ) -> None:
        """
        Initializes an instance of the TextToSpeech class with a specified output format.

        Args:
            output_format (SpeechSynthesisOutputFormat, optional): The desired output format for the synthesized speech.
                Default is Audio16Khz32KBitRateMonoMp3.
        """

        # Initialize the speech configuration with the Azure subscription and region
        self._speech_config = speechsdk.SpeechConfig(
            subscription=os.environ.get(config.azure_cognitive_services_speech_api_key),
            region=os.environ.get(config.azure_cognitive_services_speech_region),
        )

        # Initialize the output and total length variables
        self._outputs: List[TextToSpeechOutput] = []

        # Set the speech synthesis output format to the specified output format
        self._speech_config.set_speech_synthesis_output_format(output_format)

        # Initialize the speech synthesizer with the speech configuration
        self._synthesizer = speechsdk.SpeechSynthesizer(speech_config=self._speech_config)

        # Connect the speech synthesizer events to their corresponding callbacks
        self._synthesizer_events_connect()

        # Preconnecting the speech synthesizer for reduced latency
        self._connection = speechsdk.Connection.from_speech_synthesizer(self._synthesizer)
        self._connection.open(True)

        # Reset the state variables of the TTS synthesizer
        self._reset()

    @property
    def output(self) -> List[TextToSpeechOutput]:
        """
        Getter for the output property, which is a list of TextToSpeechOutput objects.

        Returns:
            List[TextToSpeechOutput]: The list of synthesized outputs.
        """
        return self._outputs

    def interrupt(self) -> None:
        """
        Interrupts an ongoing TTS process, if any.
        """
        self._interrupt = True

    def _callback_completed(self, event: speechsdk.SessionEventArgs) -> None:
        """
        Callback function for synthesis completed event.
        Sets the synthesis completed flag to True.

        Args:
            event (speechsdk.SessionEventArgs): Event arguments containing information about the synthesis completed.
        """
        self._synthesis_completed = True

    def _callback_started(self, event: speechsdk.SessionEventArgs) -> None:
        """
        Callback function for synthesis started event.
        Signals that the synthesis process has started.

        Args:
            event (speechsdk.SessionEventArgs): Event arguments containing information about the synthesis started.
        """
        self._start_synthesis.set()

    def _callback_word_boundary(self, event: speechsdk.SessionEventArgs) -> None:
        """
        Callback function for word boundary event.
        Appends the boundary information to the boundaries list.

        Args:
            event (speechsdk.SessionEventArgs): Event arguments containing information about the word boundary.
        """
        # Check if the boundary is not a sentence boundary
        if event.boundary_type != speechsdk.SpeechSynthesisBoundaryType.Sentence:

            # Calculate the offset and duration of the boundary in nanoseconds
            offset_ns = 100 * event.audio_offset
            duration = 1e9 * event.duration.total_seconds()

            # Add the boundary information to the list of boundaries
            self._boundaries.append(
                {
                    "offset_ns": offset_ns,
                    "text": event.text,
                    "word_length": event.word_length,
                    "duration": duration,
                    "boundary_type": event.boundary_type,
                    "t_word": offset_ns + duration / event.word_length,
                }
            )

    def _create_ssml(self, text: str, voice_name: str, style: Optional[str] = None) -> str:
        """
        Creates an SSML string from the given text, voice, and style.

        Args:
            text (str): The text to be converted to SSML.
            voice_name (str): The name of the voice to be used.
            style (str, optional): The speaking style to be applied. Defaults to None.

        Returns:
            str: The SSML string.
        """
        # Start the SSML string with the required header and voice tag
        ssml = (
            '<speak version="1.0" '
            'xmlns="http://www.w3.org/2001/10/synthesis" '
            'xmlns:mstts="https://www.w3.org/2001/mstts" '
            'xml:lang="en-US">'
            f'<voice name="{voice_name}">'
        )

        # If a speaking style is specified, add the express-as tag
        if style:
            text = f'<mstts:express-as style="{style}">{text}</mstts:express-as>'

        # Add the text to the SSML string
        ssml += text

        # Close the voice and speak tags and return the SSML string
        ssml += "</voice></speak>"
        return ssml

    def _reset(self) -> None:
        """
        Resets the state variables of the TTS synthesizer.
        """
        # Reset the list of boundaries that have been processed
        self._boundaries: List[Dict[str, str]] = []

        # Reset the synthesis completed, synthesis started, and interrupt flags
        self._interrupt = False
        self._synthesis_completed = False
        self._start_synthesis = threading.Event()

    def _synthesizer_events_connect(self) -> None:
        """
        Connects the TTS synthesizer events to their corresponding callbacks.
        """
        # Connect the synthesis_started event to the _callback_started method
        self._synthesizer.synthesis_started.connect(self._callback_started)

        # Connect the synthesis_word_boundary event to the _callback_word_boundary method
        self._synthesizer.synthesis_word_boundary.connect(self._callback_word_boundary)

        # Connect the synthesis_canceled and synthesis_completed events to the _callback_completed method
        self._synthesizer.synthesis_canceled.connect(self._callback_completed)
        self._synthesizer.synthesis_completed.connect(self._callback_completed)

    def _process_boundary(
        self, boundary: dict, word_index: int, timestamp: datetime.datetime, output: TextToSpeechOutput
    ) -> TextToSpeechWord:
        """
        Processes a synthesis boundary and updates the output and total length.

        Args:
            boundary (dict): The synthesis boundary to be processed.
            word_index (int): The index of the current word.
            timestamp (datetime.datetime): The timestamp of the current boundary.
            output (TextToSpeechOutput): The output object to which the processed word will be added.

        Returns:
            TextToSpeechWord: The processed word with contextual information.
        """
        text = boundary["text"]
        if word_index > 0 and boundary["boundary_type"] == speechsdk.SpeechSynthesisBoundaryType.Word:
            text = text.insert(0, " ")
        word = TextToSpeechWord(
            word=text, timestamp=timestamp, word_index=word_index, category=boundary["boundary_type"]
        )
        return word

    def _process_callbacks(self, output: TextToSpeechOutput) -> Generator[TextToSpeechWord, None, bool]:
        """
        Monitors the synthesis progress and updates the output accordingly.

        Args:
            output (TextToSpeechOutput): The output object to which the processed words will be added.

        Yields:
            TextToSpeechWord: A word with contextual information.

        Returns:
            bool: True if the process completed successfully, False otherwise.
        """
        # Initialize variables
        word_index = 0
        self._interrupt = False
        self._outputs.append(output)

        # Wait until the synthesis has started before proceeding
        self._start_synthesis.wait()

        # Record the start time
        start_time = time.perf_counter_ns()

        # Continuously monitor the synthesis progress
        while not self._synthesis_completed or word_index < len(self._boundaries):

            if self._interrupt:
                return False

            current_time = time.perf_counter_ns()
            elapsed_time = current_time - start_time

            while word_index < len(self._boundaries) and elapsed_time >= self._boundaries[word_index]["t_word"]:
                word = self._process_boundary(self._boundaries[word_index], word_index, current_time, output)
                output.append(word)
                word_index += 1
                yield word

            # Wait for a short amount of time before checking the synthesis progress again
            time.sleep(0.005)

        # Stop the synthesizer
        self._synthesizer.stop_speaking()
        return True

    def speak(self, input_string: str, voice_name: str, style: str) -> Generator[TextToSpeechWord, None, bool]:
        """
        Speaks the given text using the specified voice and style.

        Args:
            input_string (str): The text to be spoken.
            voice_name (str): The name of the voice to be used.
            style (str): The speaking style to be applied.

        Yields:
            TextToSpeechWord: A word with contextual information.
        """
        # Create SSML markup for the given input_string, voice, and style
        ssml = self._create_ssml(input_string, voice_name, style)

        # Prepare an instance of TextToSpeechOutput while will yield values iteratively
        output = TextToSpeechOutput(input_string=input_string)

        with self.__class__._speech_lock:

            # Reset all state attributes
            self._reset()

            # Create a new thread to handle the speech synthesis, and start it
            speech_thread = threading.Thread(target=self._synthesizer.speak_ssml, args=(ssml,), daemon=True)
            speech_thread.start()

            # Continuously monitor the synthesis progress in the main thread
            for word in self._process_callbacks(output):
                yield word