import os
from dotenv import load_dotenv
from io import BytesIO
from elevenlabs.client import ElevenLabs
import sounddevice as sd
import numpy as np
from scipy.io import wavfile
    

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

def record_audio():
    duration = 5  # seconds
    sample_rate = 44100  # Hz
    recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1)
    print("Recording...")
    sd.wait()  # Wait until recording is finished
    print("Done recording")
    return recording

if __name__ == "__main__":
    # Record audio from microphone
    recording = record_audio()
    sample_rate = 44100  # Hz

    # Convert to wav format in memory
    wav_buffer = BytesIO()
    wavfile.write(wav_buffer, sample_rate, recording)
    wav_buffer.seek(0)
    
    # Pass the audio data to voice_to_text
    result = voice_to_text(wav_buffer)
