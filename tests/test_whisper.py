import requests
import time
import librosa

def test_whisper(file):
    url = "http://whisper:9000/asr"
    params = {
        'task': 'transcribe',
        'language': 'ru',
        'word_timestamps': 'true',
        'output': 'json'
    }
    headers = {'accept': 'application/json'}
    print(f"Processing file \"{file}\"")
    files = {'audio_file': (file, open(file, 'rb'), 'audio/mpeg')}

    audio_length = librosa.get_duration(filename=file)

    start_time = time.time()
    response = requests.post(url, params=params, headers=headers, files=files)
    end_time = time.time()
    processing_time = end_time - start_time
    RTF = processing_time / audio_length
    print(f"RTF = {RTF}")

    #parsing
    data = response.json()
    words = []
    for segment in data["segments"]:
        for word_structure in segment["words"]:
            words.append(word_structure)
            print(word_structure)
