import numpy as np
from librosa.sequence import dtw


def safe_normalize(x):

    x = np.nan_to_num(x)

    norm = np.linalg.norm(x, axis=0, keepdims=True)

    norm[norm == 0] = 1e-8

    return x / norm


def harmonic_similarity(a, b):

    try:
        # Carica dal file .npy se esiste, altrimenti usa quello nel dict (fallback)
        if "chroma_file" in a:
            c1 = np.load(a["chroma_file"])
        else:
            c1 = np.array(a.get("chroma", []), dtype=np.float32)
            
        if "chroma_file" in b:
            c2 = np.load(b["chroma_file"])
        else:
            c2 = np.array(b.get("chroma", []), dtype=np.float32)

        # =========================
        # VALIDAZIONE
        # =========================
        if c1.ndim != 2 or c2.ndim != 2:
            return 9999

        if c1.shape[1] < 32 or c2.shape[1] < 32:
            return 9999

        # =========================
        # SOLO FINE / INIZIO
        # =========================
        tail = c1[:, -512:]
        head = c2[:, :512]

        # =========================
        # NORMALIZE
        # =========================
        tail = np.nan_to_num(tail)
        head = np.nan_to_num(head)

        tail_norm = np.linalg.norm(
            tail,
            axis=0,
            keepdims=True
        )

        head_norm = np.linalg.norm(
            head,
            axis=0,
            keepdims=True
        )

        tail_norm[tail_norm < 1e-8] = 1e-8
        head_norm[head_norm < 1e-8] = 1e-8

        tail = tail / tail_norm
        head = head / head_norm

        # sicurezza finale
        if np.isnan(tail).any():
            return 9999

        if np.isnan(head).any():
            return 9999

        # =========================
        # DTW
        # =========================
        D, _ = dtw(
            X=tail,
            Y=head,
            metric="euclidean"
        )

        if D.size == 0:
            return 9999

        score = float(D[-1, -1])

        if np.isnan(score):
            return 9999

        if np.isinf(score):
            return 9999

        return score

    except Exception as e:

        print("DTW ERROR:", e)

        return 9999
	
_FIFTH_POS = {}
for _sem, _name in [("C", 0), ("G", 1), ("D", 2), ("A", 3),
                    ("E", 4), ("B", 5), ("F#", 6), ("C#", 7),
                    ("G#", 8), ("D#", 9), ("A#", 10), ("F", 11)]:
    _FIFTH_POS[_name] = _sem

def key_distance(key_a, key_b):
    """Distanza minima sul circolo delle quinte (0-6)."""
    pa = _FIFTH_POS.get(key_a)
    pb = _FIFTH_POS.get(key_b)
    if pa is None or pb is None:
        return 99
    d = abs(pa - pb)
    return min(d, 12 - d)

def key_affinity_bonus(a, b):
    """
    Bonus/penalità armonica in base alla distanza sul circolo delle quinte:
    -6  stessa tonalità
    -5  quarta/quinta (C→G, C→F, relative...)
    -2  due passi (anch'essa usabile in mixing)
     0  lontane (semitono, tritono, ecc.)
    """
    ka = a.get("musical_key")
    kb = b.get("musical_key")
    if not ka or not kb:
        return 0

    d = key_distance(ka, kb)

    if d == 0:
        return -6
    elif d == 1:
        return -5
    elif d == 2:
        return -2
    return 0


def track_distance(a, b):

    harmonic_distance = harmonic_similarity(a, b)
    harmonic_distance = np.log1p(harmonic_distance)

    bpm_diff = abs(
        a["tempo"] - b["tempo"]
    )

    energy_diff = abs(
        a["energy"] - b["energy"]
    )

    # Nuovo: bonus graduale in base alla ruota armonica
    # (prima era binario: -5 se identica, 0 altrimenti)
    key_bonus = key_affinity_bonus(a, b)

    return (
        harmonic_distance * 4.0
        + bpm_diff * 0.25
        + energy_diff * 0.4
        + key_bonus
    )


def build_playlist(library, progress_callback=None):

    if not library:
        if progress_callback:
            progress_callback("Playlist vuota", 100)
        return []

    # Rimuovi duplicati per path
    unique = {}
    for t in library:
        unique[t["path"]] = t

    library = list(unique.values())

    if len(library) <= 1:
        if progress_callback:
            progress_callback("Playlist pronta", 100)
        return library

    playlist = [library[0]]
    remaining = library[1:].copy()
    total = len(library)

    while remaining:
        done = total - len(remaining)
        percent = int(done / total * 100)

        if progress_callback:
            progress_callback(
                f"Sorting playlist DTW... ({done}/{total})",
                percent
            )

        best = min(
            remaining,
            key=lambda x: track_distance(playlist[-1], x)
        )

        playlist.append(best)
        remaining.remove(best)

    # === COMPLETATO ===
    if progress_callback:
        progress_callback("Playlist ordinata con successo!", 100)

    return playlist
