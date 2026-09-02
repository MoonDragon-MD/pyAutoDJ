import soundfile as sf
import numpy as np

from analysis.silence_detector import detect_trim


def create_waveform(path, progress_callback=None):
    if progress_callback:
        progress_callback("Loading audio for waveform...", 10)

    # Leggi il file
    y, sr = sf.read(path)

    if len(y.shape) > 1:
        y = np.mean(y, axis=1)

    if progress_callback:
        progress_callback("Trimming silence...", 40)

    # Trim silence
    start, end = detect_trim(y, sr)
    start_i = int(start * sr)
    end_i = int(end * sr)
    y = y[start_i:end_i]

    if len(y) < 100:
        y = np.zeros(1000)  # fallback

    # Normalizzazione più forte
    mx = np.max(np.abs(y))
    if mx > 0:
        y = y / mx * 0.95   # non arrivare a 1.0 esatto

    # Downsampling per visualizzazione fluida
    step = max(1, len(y) // 1200)   # circa 1200 punti
    y = y[::step]

    # Aggiungi un po' di "corpo" se è troppo piatto
    if np.max(np.abs(y)) < 0.3:
        y = y * 3.0

    if progress_callback:
        progress_callback("Waveform ready", 100)

    return y.astype(np.float32)