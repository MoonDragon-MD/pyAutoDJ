import numpy as np
import random

class CrossFadeEngine:

    def __init__(self):
        self.duration = 8000  # ms

    def _load_chroma(self, track):
        if "chroma_file" in track and track["chroma_file"]:
            return np.load(track["chroma_file"])
        return np.array(track.get("chroma", []), dtype=np.float32)

    def get_best_phrase_match(self, current, next_track, current_time=0):
        """Usato per Manual Fade e Fade Next Match"""
        matches = self._find_best_matches(current, next_track, num_candidates=4)
        fallback = (
            int(current.get("end_trim", current["duration"]) * 1000) - 13500,
            int(next_track.get("start_trim", 0) * 1000)
        )

        if not matches:
            return fallback

        valid = [(out, inn, out - current_time) 
                for out, inn in matches 
                if out > current_time + 600 and (out - current_time) < 32000]

        if not valid:
            return fallback

        valid.sort(key=lambda x: x[2])   # più vicino nel tempo
        best = valid[0]
        return best[0], best[1]

    def get_auto_random_match(self, current, next_track, current_time=0):
        """Versione avanzata per Auto Random Fade"""
        matches = self._find_best_matches(current, next_track, num_candidates=6)
        fallback = (
            int(current.get("end_trim", current["duration"]) * 1000) - 13500,
            int(next_track.get("start_trim", 0) * 1000)
        )

        if not matches:
            return fallback

        valid = [(out, inn, out - current_time) 
                for out, inn in matches 
                if out > current_time + 600 and (out - current_time) < 32000]

        if not valid:
            return fallback

        valid.sort(key=lambda x: x[2])
        best_candidates = valid[:4]
        chosen = random.choice(best_candidates)

        print(f"Auto Random Fade scelto → tra {chosen[2]/1000:.1f}s (@ {chosen[0]/1000:.1f}s)")
        return chosen[0], chosen[1]

    def _find_best_matches(self, current, next_track, num_candidates=6):
        """Versione migliorata - cerca solo nelle ultime frasi reali"""
        curr_chroma = self._load_chroma(current)
        next_chroma = self._load_chroma(next_track)

        phrases = current.get("phrases", [])
        track_end_ms = int(current.get("end_trim", current["duration"]) * 1000)

        fallback = (track_end_ms - 13500, int(next_track.get("start_trim", 0) * 1000))

        if len(phrases) < 2 or curr_chroma.size == 0 or next_chroma.size == 0:
            return [fallback]

        candidates = []
        next_duration_ms = next_track["duration"] * 1000
        next_frames = next_chroma.shape[1]
        ms_per_frame = next_duration_ms / next_frames if next_frames > 0 else 1.0

        min_time_ms = track_end_ms - 65000   # ultime ~65 secondi

        for p in phrases[-22:]:
            out_ms = int(p * 1000)
            if out_ms < min_time_ms:
                continue

            frame = int((p / current["duration"]) * curr_chroma.shape[1])
            start = max(0, frame - 38)
            end = min(curr_chroma.shape[1], frame + 38)

            out_seg = np.mean(curr_chroma[:, start:end], axis=1)

            for i in range(0, 240, 5):
                in_seg = np.mean(next_chroma[:, i:i + 34], axis=1)

                harmonic_score = -np.linalg.norm(out_seg - in_seg)
                energy_bonus = -abs(current.get("energy", 0.5) - next_track.get("energy", 0.5)) * 14

                total_score = harmonic_score + energy_bonus
                in_ms = int(i * ms_per_frame)
                
                # Controllo sicurezza per NaN/Inf
                if not np.isfinite(total_score):
                    continue

                candidates.append((total_score, out_ms, in_ms))

        if not candidates:
            return [fallback]

        candidates.sort(reverse=True)
        best = candidates[:num_candidates * 2]

        result = [(out_ms, in_ms) for score, out_ms, in_ms in best]
        
        print(f" _find_best_matches → {len(result)} candidati | Best score: {best[0][0]:.1f}")
        return result