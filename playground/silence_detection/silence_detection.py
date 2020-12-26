from webrtcvad_wrapper.webrtcvad_wrapper import VAD
from pydub import AudioSegment


def silence_voice_len(audio_segment, sensetivity=3):
    vad = VAD(sensitivity_mode=sensetivity)
    filtered_segments = vad.filter(audio_segment)

    segmets_with_voice = [[fs[0], fs[1]] for fs in filtered_segments if fs[-1]]

    voice_len = 0
    for i, segment in enumerate(segmets_with_voice):
        voice_len += len(audio[segment[0]*1000:segment[1]*1000])

    silence_len = len(audio) - voice_len

    return voice_len / 1000, silence_len / 1000


if __name__ == '__main__':
    file_path = input()
    audio = AudioSegment.from_wav(file_path)

    print('audio_len:', len(audio) / 1000)
    print('voice_len: {}\nsilence_len:{}'.format(*silence_voice_len(audio)))
