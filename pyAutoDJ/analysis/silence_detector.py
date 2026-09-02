import librosa

def detect_trim(y, sr):

    intervals = librosa.effects.split(
        y,
        top_db=25
    )

    if len(intervals) == 0:
        return 0, librosa.get_duration(y=y, sr=sr)

    start = intervals[0][0] / sr
    end = intervals[-1][1] / sr

    return start, end
