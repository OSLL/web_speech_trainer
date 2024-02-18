import sys
import requests
import time
import librosa

url = "http://0.0.0.0:9000/asr?encode=true&task=transcribe&word_timestamps=true&output=json"
headers = {'accept': 'application/json'}

file = sys.argv[1]
print(f"Processing file \"{file}\"")
files = {'audio_file': (file, open(file, 'rb'), 'audio/mpeg')}

audio_length = librosa.get_duration(path=file)

start_time = time.time()
response = requests.post(url, headers=headers, files=files)
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
