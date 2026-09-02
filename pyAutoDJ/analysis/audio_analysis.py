import os
import json
import hashlib

import librosa
import numpy as np
from mutagen import File as MutagenFile

from analysis.silence_detector import detect_trim

CACHE_DIR = "assets/cache"

KEY_NAMES = [
    "C", "C#", "D", "D#",
    "E", "F", "F#", "G",
    "G#", "A", "A#", "B"
]

def detect_musical_key(chroma):
    chroma_mean = np.mean(chroma, axis=1)
    return KEY_NAMES[int(np.argmax(chroma_mean))]


def detect_phrases(beat_times):
    """
    16 beat = frase tipica EDM / house
    """
    if len(beat_times) < 16:
        return []

    return [
        float(beat_times[i])
        for i in range(0, len(beat_times), 16)
    ]


def build_beat_grid(beat_times):
    return [float(b) for b in beat_times]


def analyze_track(path, progress_callback=None):
    import warnings
    import logging
    
    os.makedirs(CACHE_DIR, exist_ok=True)

    stat = os.stat(path)
    track_hash = hashlib.md5(path.encode()).hexdigest()
    cache_key = f"{track_hash}_{stat.st_mtime}_{stat.st_size}"
    cache_path = os.path.join(CACHE_DIR, f"{cache_key}.json")
    
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r") as f:
                return json.load(f)
        except:
            pass

    # === FIX: Sopprimi warning librerie audio ===
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        logging.getLogger('librosa').setLevel(logging.ERROR)
        
        try:
            y_full, sr = librosa.load(path, sr=22050, mono=True, duration=300)
        except Exception as e:
            print(f"⚠️ Errore caricamento {path}: {e}")
            return None  # Restituisce None invece di crashare

    segment = sr * 60

    if len(y_full) > segment * 2:
        y_short = np.concatenate([
            y_full[:segment],
            y_full[-segment:]
        ])
    else:
        y_short = y_full

    if len(y_short) == 0:
        raise ValueError("Audio vuoto")

    if np.max(np.abs(y_short)) < 1e-5:
        raise ValueError("Audio troppo silenzioso")

    # ================= BPM + BEAT GRID =================
    if progress_callback:
        progress_callback("Analyzing BPM...", 10)
    
    try:
        tempo, beat_frames = librosa.beat.beat_track(y=y_short, sr=sr)
        tempo = float(np.atleast_1d(tempo)[0])
        beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    except Exception as e:
        print(f"⚠️ Errore analisi BPM {path}: {e}")
        tempo = 128.0
        beat_times = []

    # ================= CHROMA =================
    if progress_callback:
        progress_callback("Building chroma map...", 30)
    try:
        chroma = librosa.feature.chroma_stft(y=y_short, sr=sr, n_fft=4096)
        chroma = np.nan_to_num(chroma)
    except:
        chroma = np.zeros((12, 1000))
        beat_times = []

    # ================= KEY =================
    musical_key = detect_musical_key(chroma)

    # ================= ENERGY =================
    energy = float(np.mean(librosa.feature.rms(y=y_short)))

    # ================= SILENCE =================
    start_trim, end_trim = detect_trim(y_full, sr)

    duration = librosa.get_duration(y=y_full, sr=sr)
    play_duration = end_trim - start_trim

    # ================= PHRASES =================
    if progress_callback:
        progress_callback("Detecting phrases...", 55)
    phrases = detect_phrases(beat_times)

    # ================= META =================
    if progress_callback:
        progress_callback("Extracting cover and writing cache......", 85)
    
    title = os.path.basename(path)
    artist = "Unknown"
    cover = None

    try:
        meta = MutagenFile(path)
        if meta:
            try:
                title = str(meta.get("TIT2", [title])[0])
                artist = str(meta.get("TPE1", [artist])[0])
            except:
                pass
            
            # Estrai cover se presente
            for k in meta.keys():
                if str(k).startswith("APIC"):
                    cover_data = meta[k].data
                    cover_path = os.path.join(CACHE_DIR, f"{cache_key}_cover.jpg")
                    with open(cover_path, "wb") as f:
                        f.write(cover_data)
                    cover = cover_path
                    break
    except Exception as e:
        print(f"⚠️ Errore metadati {path}: {e}")

    data = {
        "path": path,
        "title": title,
        "artist": artist,
        "tempo": tempo,
        "musical_key": musical_key,
        "energy": energy,
        "duration": float(duration),
        "play_duration": float(play_duration),
        "start_trim": float(start_trim),
        "end_trim": float(end_trim),
        "phrases": phrases
    }

    # Salva Chroma separatamente
    chroma_path = os.path.join(CACHE_DIR, f"{cache_key}_chroma.npy")
    np.save(chroma_path, chroma)
    data["chroma_file"] = chroma_path

    if cover:
        data["cover"] = cover

    with open(cache_path, "w") as f:
        json.dump(data, f)
        
    if progress_callback:
        progress_callback("Track ready", 100)
    return data