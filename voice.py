import os
from dotenv import load_dotenv
from io import BytesIO
from elevenlabs.client import ElevenLabs
import sounddevice as sd
import numpy as np
from scipy.io import wavfile
import queue
import threading

load_dotenv()
client = ElevenLabs(
    api_key=os.getenv("ELEVENLABS_API_KEY"),
)

def voice_to_text(voice_data):
    transcription = client.speech_to_text.convert(
        file=voice_data,
        model_id="scribe_v1", # Model to use, for now only "scribe_v1" is supported
        tag_audio_events=True, # Tag audio events like laughter, applause, etc.
        language_code="eng", # Language of the audio file. If set to None, the model will detect the language automatically.
        diarize=True, # Whether to annotate who is speaking
    )
    print(transcription)
    return transcription

class AudioRecorder:
    def __init__(self):
        self.sample_rate = 44100
        self.channels = 1
        self.recording = False
        self.audio_data = []
        self.stream = None
        self.audio_queue = queue.Queue()

    def callback(self, indata, frames, time, status):
        if status:
            print(status)
        if self.recording:
            self.audio_queue.put(indata.copy())

    def start_recording(self):
        self.recording = True
        self.audio_data = []
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            callback=self.callback
        )
        self.stream.start()
        print("Recording started...")

    def stop_recording(self):
        if self.recording:
            self.recording = False
            if self.stream:
                self.stream.stop()
                self.stream.close()
            
            # Get all remaining audio data from queue
            while not self.audio_queue.empty():
                self.audio_data.append(self.audio_queue.get())

            if self.audio_data:
                # Combine all audio chunks
                audio_data = np.concatenate(self.audio_data)
                
                # Convert to wav format in memory
                wav_buffer = BytesIO()
                wavfile.write(wav_buffer, self.sample_rate, audio_data)
                wav_buffer.seek(0)
                
                print("Recording stopped. Converting speech to text...")
                # Pass the audio data to voice_to_text
                result = voice_to_text(wav_buffer)
                return result
            else:
                print("No audio data recorded")
                return None

if __name__ == "__main__":
    recorder = AudioRecorder()
    
    print("Press Enter to start recording...")
    input()
    recorder.start_recording()
    
    print("Press Enter to stop recording...")
    input()
    result = recorder.stop_recording()
