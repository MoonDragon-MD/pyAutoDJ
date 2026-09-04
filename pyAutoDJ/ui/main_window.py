import os, sys
import threading
import math
import vlc
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFileDialog,
    QMessageBox
)
from PyQt5.QtCore import (
    QTimer,
    QThreadPool,
    QElapsedTimer,
    Qt
)
import numpy as np

from core.player_engine import PlayerEngine
from ui.debug_window import DebugWindow
from core.signals import SignalBus
from core.transitions import CrossFadeEngine
from workers.analyze_worker import AnalyzeWorker
from workers.waveform_worker import WaveformWorker
from workers.playlist_worker import PlaylistWorker
from ui.deck_widget import DeckWidget
from ui.playlist_widget import PlaylistWidget
from ui.controls_widget import ControlsWidget
from core.playlist_engine import harmonic_similarity
from collections import deque

class AutoDJWindow(QWidget):

    def __init__(self, use_separate_vlc=False):
        super().__init__()

        self.setWindowTitle("pyAutoDJ")
        self.resize(1700, 950)

        self.library = []
        self.playlist = []
        self.current_index = -1
        self.is_playing = False
        self.fade_running = False
        self.fade_pending_match = False
        self.auto_fade_enabled = False
        self.fx_enabled = False
        self.dtw_worker_started = False
        self.loading_total = 0
        self.loading_done = 0

        self.threadpool = QThreadPool.globalInstance()
        self.players = PlayerEngine(use_separate_vlc=use_separate_vlc)
        self.signals = SignalBus()

        self.setup_ui()
        self.connect_signals()

        self.monitor = QTimer()
        self.monitor.timeout.connect(self.monitor_playback)
        self.monitor.start(15)

        self.controls.dropLabel.filesDropped.connect(self.handle_dropped_files)
        
        self.pending_waveforms = 0
        
        self.next_auto_fade_check = 0
        self.last_fade_time = 0
        self.playlist_lock = threading.Lock()
        self.loop_playlist = False
        self._eq_release_started = False
        
        # Crea la finestra di debug (inizialmente nascosta)
        self.debug_window = DebugWindow(self)
        # 2. Collega il segnale della SignalBus alla finestra
        # Assicurati che SignalBus abbia emesso il segnale debugLog
        self.signals.debugLog.connect(self.debug_window.append_log)
        
        # REINDIRIZZAMENTO Questo fa sì che TUTTI i print(l) vadano anche nella finestra di debug in info
        # FIX: Redirection CON PROTEZIONE DA REENTRANCY
        from datetime import datetime
        
        class SafeStdoutRedirect:
            def __init__(self, signal):
                self.signal = signal
                self.lock = threading.Lock()
            
            def write(self, text):
                if text.strip() and self.lock.acquire(blocking=False):
                    try:
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        formatted = f"[{timestamp}] {text}"
                        self.signal.emit(formatted)
                    finally:
                        self.lock.release()
            
            def flush(self):
                pass
        
        sys.stdout = SafeStdoutRedirect(self.signals.debugLog)
        sys.stderr = SafeStdoutRedirect(self.signals.debugLog)

    # Durata del crossfade (prima era ~8s in teoria, ma il tick counter la accorciava di fatto)
    FADE_DURATION_MS = 6200   
	
    # Ramp dell'FX: 80ms x 25 step ≈ 2 secondi di crescendo dell'effetto.
    # Aumentare FX_RAMP_STEPS per un effetto piu' lungo e morbido.
    FX_RAMP_STEP_MS = 80
    FX_RAMP_STEPS = 25
	
    # Rilascio progressivo EQ: 100ms x 25 step ≈ 2.5s di sfumatura
    # dell'effetto negli ultimi secondi di vita del brano.
    EQ_RELEASE_STEP_MS = 100
    EQ_RELEASE_STEPS = 25
    EQ_RELEASE_BEFORE_MS = 25000   # start del rilascio a 25s dalla fine

    def setup_ui(self):
        self.setMinimumSize(960, 620)

        root = QVBoxLayout(self)

        decks = QHBoxLayout()
        self.deckA = DeckWidget("DECK A")
        self.deckB = DeckWidget("DECK B")
        decks.addWidget(self.deckA)
        decks.addWidget(self.deckB)
        root.addLayout(decks)

        bottom = QHBoxLayout()
        self.controls = ControlsWidget()
        self.playlistWidget = PlaylistWidget()
        bottom.addWidget(self.controls, 1)
        bottom.addWidget(self.playlistWidget, 2)
        root.addLayout(bottom)

    def connect_signals(self):
        self.controls.playPause.connect(self.toggle_play)
        self.controls.randomFade.connect(self.manual_random_fade)
        self.controls.fadeNextMatch.connect(self.fade_next_match)
        self.controls.autoFadeToggled.connect(self.set_auto_fade)
        self.controls.loadFiles.connect(self.load_files)
        self.controls.info.connect(self.show_info)
        self.controls.fxToggled.connect(self.toggle_fx)

        self.signals.trackAnalyzed.connect(self.track_ready)
        self.signals.waveformReady.connect(self.waveform_ready)
        self.signals.playlistReady.connect(self.playlist_ready)
        
        self.signals.taskUpdate.connect(self.update_task_status)

        self.deckA.waveform.seekRequested.connect(lambda f: self.seek_player("A", f))
        self.deckB.waveform.seekRequested.connect(lambda f: self.seek_player("B", f))

    def set_auto_fade(self, enabled: bool):
        self.auto_fade_enabled = enabled

    def toggle_fx(self, enabled: bool):
        self.fx_enabled = enabled

    def manual_random_fade(self):
        """Fade manuale"""
        if not self.playlist or self.current_index + 1 >= len(self.playlist):
            return
        self.random_fade(force=True)
        
    def _cancel_pending_match(self):
        """Annulla un fade-next-match in attesa (usato da fade alternativi e pausa)"""
        if getattr(self, "pending_match_timer", None) is not None:
            self.pending_match_timer.stop()
            self.pending_match_timer.deleteLater()
            self.pending_match_timer = None
        if self.fade_pending_match:
            self.fade_pending_match = False
            self.controls.set_match_waiting(False)

    def fade_next_match(self):
        """Fade al prossimo match phrase disponibile"""
        if self.fade_running or self.fade_pending_match:
            return

        if self.current_index + 1 >= len(self.playlist):
            return

        current = self.playlist[self.current_index]
        next_track = self.playlist[self.current_index + 1]
        current_time = self.players.active_player().get_time()

        engine = CrossFadeEngine()
        target_out, target_in = engine.get_best_phrase_match(
            current, next_track, current_time=current_time
        )

        self.pending_next_start = target_in

        now = self.players.active_player().get_time()
        wait = max(0, target_out - now)

        real_end = int(current.get("end_trim", current["duration"]) * 1000)
        remaining = real_end - now

        if wait > remaining + 500:
            print(f"⚠️ Fade Next Match annullato: attesa ({wait/1000:.1f}s) > rimanenza")
            return

        print(f"🎯 Fade Next Match programmato tra {wait/1000:.1f} secondi "
              f"(out @ {target_out/1000:.1f}s)")

        self.controls.set_match_waiting(True)
        self.fade_pending_match = True

        # IMPORTANTE: NON impostare fade_running qui! Il monitor deve
        # continuare a girare (playhead + pre-warm) fino al momento del fade.
        self.pending_match_timer = QTimer(self)
        self.pending_match_timer.setSingleShot(True)
        self.pending_match_timer.timeout.connect(self._execute_pending_match_fade)
        self.pending_match_timer.start(wait)

    def _execute_pending_match_fade(self):
        """Esegue il fade dopo l'attesa del match"""
        self._cancel_pending_match()

        # Se nel frattempo e' partito un altro fade o siamo in pausa, niente fade
        if self.fade_running or not self.is_playing:
            return

        self.random_fade(force=True)
		
    def _handle_playlist_end(self):
        """Fine playlist: loop automatico, domanda, o stop."""
        if getattr(self, "loop_playlist", False):
            print("🔁 LOOP: riparto da capo (modalità loop attiva)")
            self._restart_playlist()
            return

        self.monitor.stop()
        self.players.active_player().pause()

        box = QMessageBox(self)
        box.setWindowTitle("Playlist terminata")
        box.setText("La playlist è finita!\n\nVuoi riprendere da capo?")
        restart_btn = box.addButton("Ricomincia", QMessageBox.YesRole)
        loop_btn = box.addButton("Loop continuo", QMessageBox.ActionRole)
        stop_btn = box.addButton("Ferma", QMessageBox.RejectRole)
        box.exec_()

        clicked = box.clickedButton()
        if clicked is loop_btn:
            self.loop_playlist = True
            print("🔁 Loop continuo attivato")
            self._restart_playlist()
        elif clicked is restart_btn:
            self._restart_playlist()
        else:
            # Stop definitivo
            self.players.stop_all()
            self.is_playing = False
            self.controls.set_play_button_text(False)

    def _restart_playlist(self):
        """Riparte la playlist dalla prima traccia"""
        if not self.playlist:
            return

        self.current_index = 0
        self.is_playing = False             # forza il percorso PLAY
        self.prewarmed_path = None
        self.players.stop_all()

        self.monitor.start(15)
        self.toggle_play()

    def load_files(self):
        """Carica file con gestione della coda per evitare freeze"""
        dialog = QFileDialog(self)
        dialog.setWindowTitle("Seleziona file audio o cartelle")
        dialog.setFileMode(QFileDialog.ExistingFiles)
        dialog.setOption(QFileDialog.ShowDirsOnly, False)
        dialog.setNameFilter("Audio Files (*.mp3 *.wav *.flac *.ogg *.m4a *.aac)")
        dialog.setOption(QFileDialog.DontResolveSymlinks, True)

        if dialog.exec_() != QFileDialog.Accepted:
            return

        selected = dialog.selectedFiles()
        if not selected:
            return

        files_to_load = []
        for path in selected:
            if os.path.isdir(path):
                for root, _, filenames in os.walk(path):
                    for fname in filenames:
                        if fname.lower().endswith(('.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac')):
                            files_to_load.append(os.path.join(root, fname))
            else:
                files_to_load.append(path)

        files_to_load = list(dict.fromkeys(files_to_load))

        # Rimuovi i file già presenti in libreria
        known = {t["path"] for t in self.library}
        files_to_load = [f for f in files_to_load if f not in known]

        if not files_to_load:
            QMessageBox.information(self, "Nessun file", "Nessun nuovo file audio trovato.")
            return

        print(f"Trovati {len(files_to_load)} file audio da caricare")

        self.loading_total += len(files_to_load)
        self.loading_done = 0
        self.pending_waveforms = len(files_to_load)

        self.controls.progress.show()
        self.controls.taskLabel.setText(
            f"Aggiunte {len(files_to_load)} tracce (totale: {len(self.library)})...")

        # I worker vengono avviati SOLO dal timer (_process_next_file),
        # che ne tiene al massimo 5 attivi contemporaneamente.
        # NON avviare AnalyzeWorker direttamente qui: ogni file verrebbe
        # analizzato due volte e si reintrodurrebbe il freeze fullscreen.
        queue = deque(files_to_load)

        if hasattr(self, "process_queue_timer") and self.process_queue_timer.isActive():
            self.process_queue_timer.stop()

        self.process_queue_timer = QTimer()
        self.process_queue_timer.timeout.connect(lambda: self._process_next_file(queue))
        self.process_queue_timer.start(50)

    def _process_next_file(self, queue):
        """Gestisce la coda di caricamento in modo controllato"""
        active_count = self.threadpool.activeThreadCount()
        # Se ci sono meno di N thread attivi, ne avviamo uno nuovo
        if active_count < 5 and queue:
            filepath = queue.popleft()
            worker = AnalyzeWorker(filepath, self.signals, None)
            self.threadpool.start(worker)
            
            # Aggiorna barra progresso solo visivamente (non accurata al 100% finché non finisce)
            percent = int((self.loading_total - len(queue)) / self.loading_total * 100)
            self.controls.progress.setValue(percent)
        elif not queue and active_count == 0:
            # Tutti finiti
            self.process_queue_timer.stop()
            self.controls.progress.setValue(100)
            QTimer.singleShot(800, lambda: self.controls.progress.hide())
            self.controls.taskLabel.setText(f"Caricamento completato ({self.loading_total} tracce)")
            
    def sync_decks_ui(self):
        if self.players._current == "A":
            # ✅ Usa self.deckA.tonearm invece di self.deckA.vinyl
            self.deckA.tonearm.set_tonearm_active(True)
            self.deckB.tonearm.set_tonearm_active(False)

            self.deckA.vinyl.set_spinning(True)
            self.deckB.vinyl.set_spinning(False)

            self.deckA.set_active(True)
            self.deckB.set_active(False)

        else:
            # ✅ Usa self.deckB.tonearm invece di self.deckB.vinyl
            self.deckB.tonearm.set_tonearm_active(True)
            self.deckA.tonearm.set_tonearm_active(False)

            self.deckB.vinyl.set_spinning(True)
            self.deckA.vinyl.set_spinning(False)

            self.deckB.set_active(True)
            self.deckA.set_active(False)

    def track_ready(self, track, item):
        # FIX: analyze_track restituisce None se il file è corrotto/ illeggibile
        if track is None:
            self.loading_done += 1
            self.pending_waveforms = max(0, self.pending_waveforms - 1)
            print("⚠️ Traccia saltata (analisi fallita)")
            return

        self.library.append(track)

        if len(self.library) == 1:
            self.deckA.set_track(track)
        elif len(self.library) == 2:
            self.deckB.set_track(track)

        self.playlistWidget.add_track(track)

        wf = WaveformWorker(track, self.signals)
        self.threadpool.start(wf)

        self.loading_done += 1

        # Avvia il calcolo DTW solo a caricamento completato
        if self.loading_done >= self.loading_total and not self.dtw_worker_started:
            self.dtw_worker_started = True

            print(f"🎯 Inizio calcolo DTW con {len(self.library)} tracce totali")

            worker = PlaylistWorker(self.library, self.signals)
            self.threadpool.start(worker)
        else:
            print(f"⏳ Traccia {len(self.library)} analizzata... (DTW: {'✓' if self.dtw_worker_started else '✗'})")

    def waveform_ready(self, y, track, deck):

        if deck == "A":
            self.deckA.set_track(track)
            self.deckA.waveform.set_waveform(y)

        else:
            self.deckB.set_track(track)
            self.deckB.waveform.set_waveform(y)

        # Primo deck
        if len(self.library) == 1:

            self.deckA.set_track(track)
            self.deckA.waveform.set_waveform(y)
        elif len(self.library) == 2:
            self.deckB.set_track(track)
            self.deckB.waveform.set_waveform(y)
        else:
            if hasattr(self.deckA, "track") and self.deckA.track["path"] == track["path"]:
                self.deckA.set_track(track)
                self.deckA.waveform.set_waveform(y)
            if hasattr(self.deckB, "track") and self.deckB.track["path"] == track["path"]:
                self.deckB.set_track(track)
                self.deckB.waveform.set_waveform(y)
                
        self.pending_waveforms -= 1
        
        # === BARRA DI CARICAMENTO FINALE ===
        if self.loading_done >= self.loading_total and self.pending_waveforms <= 0:
            self.controls.progress.setValue(100)
            QTimer.singleShot(800, self.controls.progress.hide)   # nasconde dopo 800ms

        total_ops = self.loading_total + self.loading_total
        done_ops = self.loading_done + (
            self.loading_total - self.pending_waveforms
        )

        percent = int(done_ops / total_ops * 100)

        self.controls.progress.setValue(percent)

        if self.pending_waveforms <= 0:
            self.controls.progress.hide()

    def playlist_ready(self, playlist):
        self.playlist = playlist
        
        # Aggiorna la lista nella GUI con l'ordine DTW
        self.playlistWidget.clear()

        for track in playlist:
            self.playlistWidget.add_track(track)

        print(f"Playlist DTW caricata con {len(playlist)} tracce\n")
        
        # Messaggio di completamento nella GUI
        if hasattr(self.controls, 'taskLabel'):
            self.controls.taskLabel.setText(f"Playlist DTW pronta ({len(playlist)} tracce)")
            QTimer.singleShot(1500, self.clear_task_status)

    def toggle_play(self):
        # ✅ SE PLAYLIST VUOTA, MOSTRA UN MESSAGGIO
        if not self.playlist:
            if len(self.library) > 0:
                print("⚠️ Playlist in elaborazione... attendi il calcolo DTW")
                self.controls.taskLabel.setText("⏳ Calcolo playlist in corso...")
                self.controls.taskLabel.setStyleSheet("color:#ffaa00; font-size:13px; font-weight:bold;")
            else:
                print("❌ Nessuna traccia caricata! Carica prima dei file audio.")
                self.controls.taskLabel.setText("⚠️ Nessun file caricato!")
                self.controls.taskLabel.setStyleSheet("color:#ff5555; font-size:13px; font-weight:bold;")
                QTimer.singleShot(2000, self.clear_task_status)
            return

        player = self.players.active_player()

        if not self.is_playing:
            # ================== PLAY / RESUME ==================
            if self.current_index < 0:
                self.current_index = 0

            track = self.playlist[self.current_index]

            # Carica solo se non è già stato caricato
            if player.get_state() not in (vlc.State.Playing, vlc.State.Paused):
                self.players.load(player, track["path"])
                player.audio_set_volume(100)
                start_trim = int(track.get("start_trim", 0) * 1000)
                
                # Aggiorna la UI subito per evitare glitch
                QTimer.singleShot(50, lambda: player.set_time(start_trim))

            player.play()

            # Riavvia il timer di monitoraggio
            self.monitor.start(15)

            self.sync_decks_ui()

            # Mixer GUI
            if self.players._current == "A":
                self.deckA.fader.set_level(1.0)
                self.deckB.fader.set_level(0.0)
            else:
                self.deckB.fader.set_level(1.0)
                self.deckA.fader.set_level(0.0)

            # Precarico prossima traccia
            self._preload_next_track()

            # Forza traccia corrente sul deck attivo
            if self.players._current == "A":
                self.deckA.set_track(track)  # Deck A = traccia corrente
            else:
                self.deckB.set_track(track)  # Deck B = traccia corrente

            # Vinyl + Tonearm e stato deck
            if self.players._current == "A":
                self.deckA.set_active(True)
                self.deckB.set_active(False)
                self.deckA.vinyl.set_spinning(True)
                self.deckB.vinyl.set_spinning(False)
                self.deckA.tonearm.set_tonearm_active(True)
                self.deckB.tonearm.set_tonearm_active(False)
            else:
                self.deckB.set_active(True)
                self.deckA.set_active(False)
                self.deckB.vinyl.set_spinning(True)
                self.deckA.vinyl.set_spinning(False)
                self.deckB.tonearm.set_tonearm_active(True)
                self.deckA.tonearm.set_tonearm_active(False)

            # Assicurati di fermare qualsiasi fade pending
            self.fade_running = False
            self.fade_pending_match = False
            
            # Avvia tutto
            self.is_playing = True
            self.controls.set_play_button_text(True)
            self.monitor.start(15)

        else:
            # ================== PAUSE ==================
            # 1. FERMA SUBITO IL MONITORAGGIO PRIMA DI FARE ALTRO
            self.monitor.stop()
            
            # 2. Annulla eventuali fade in sospeso
            self.fade_running = False
            self._cancel_pending_match()
            self._stop_fx_ramp()          # ferma anche la rampa FX
            self.fade_pending_match = False
            self._eq_release_started = False
            self.controls.set_match_waiting(False)
            
            # 3. Ferma effetti
            if hasattr(self, 'fade_timer') and self.fade_timer is not None:
                self.fade_timer.stop()
                self.fade_timer.deleteLater()
                self.fade_timer = None

            player.pause()
            
            # Aggiorna UI
            if self.players._current == "A":
                self.deckA.vinyl.set_spinning(False)
                self.deckA.tonearm.set_tonearm_active(False)
            else:
                self.deckB.vinyl.set_spinning(False)
                self.deckB.tonearm.set_tonearm_active(False)

            self.is_playing = False
            self.controls.set_play_button_text(False)
            
    def update_task_status(self, text, percent):
        self.controls.taskLabel.setText(text)

        if percent >= 0:
            self.controls.progress.setValue(percent)

        # ==================== GESTIONE COLORI AVVISI ====================
        text_upper = text.upper()

        if "MATCH" in text_upper or "NEXT MATCH" in text_upper:
            self.controls.taskLabel.setStyleSheet("color:#ffaa00; font-size:13px; font-weight:bold;")

        elif "FADE" in text_upper:
            self.controls.taskLabel.setStyleSheet("color:#00ff88; font-size:13px; font-weight:bold;")

        elif "ERROR" in text_upper:
            self.controls.taskLabel.setStyleSheet("color:#ff5555; font-size:13px;")

        else:
            # Messaggi normali (Waveform ready, Playlist pronta, ecc.)
            self.controls.taskLabel.setStyleSheet("""
                color: #00ff88;
                font-size: 13px;
                font-weight: bold;
            """)

        # AUTO CLEAR per messaggi finali
        if percent == 100:
            QTimer.singleShot(1400, self.clear_task_status)

    def clear_task_status(self):
        self.controls.taskLabel.setText("")
        # Ripristina stile di default
        self.controls.taskLabel.setStyleSheet("""
            color: #00ff88;
            font-size: 13px;
        """)

    def random_fade(self, force=False):
        """Esegue il fade (sia manuale che automatico)"""
        if self.fade_running and not force:
            print("⚠️ Fade già in corso, ignorato")
            return

        if self.current_index + 1 >= len(self.playlist):
            self.fade_running = False
            return

        self.fade_running = True
        self._cancel_pending_match()          # Un solo padrone del fade
        self._fx_applied = False
        self.pending_next_start = 0

        current = self.playlist[self.current_index]
        next_track = self.playlist[self.current_index + 1]

        active = self.players.active_player()
        current_time = active.get_time()          # ← Tempo attuale del brano

        engine = CrossFadeEngine()

        # ===================== SCELTA DELLA MODALITÀ =====================
        if force:
            # Manual Fade o Fade Next Match → usa match più vicino
            target_out, target_in = engine.get_best_phrase_match(
                current, next_track, current_time=current_time
            )
            mode = "MANUAL / NEXT MATCH"
        else:
            # Auto Random Fade → comportamento più creativo
            target_out, target_in = engine.get_auto_random_match(
                current, next_track, current_time=current_time
            )
            mode = "AUTO RANDOM"

        self.pending_next_start = target_in

        # ===================== CALCOLO TEMPI =====================
        out_min = target_out // 60000
        out_sec = (target_out % 60000) / 1000
        
        in_min = target_in // 60000
        in_sec = (target_in % 60000) / 1000
        
        bpm_diff = abs(current["tempo"] - next_track["tempo"])

        # ===================== LOG DEBUG RIORGANIZZATO =====================
        print("\n" + "="*85 + "\n")
        print(f"🚀 {mode} FADE TRIGGERED\n")
        print("="*85 + "\n")
        print(f"FROM: {current['title']} | {current.get('musical_key', '?')} @ {int(current['tempo'])} BPM\n")
        print(f"OUT at: {out_min}:{out_sec:05.2f}s")
        print(f"TO:   {next_track['title']} | {next_track.get('musical_key', '?')} @ {int(next_track['tempo'])} BPM\n")
        print(f"IN at:  {in_min}:{in_sec:05.2f}s\n")
        print(f"BPM Δ: {bpm_diff:.1f}\n")
        print(f"FX: {'ON' if self.fx_enabled else 'OFF'} | Force: {force}\n")
        print("="*85 + "\n")

        # ===================== PREPARA TRACCIA SUCCESSIVA =====================
        inactive = self.players.inactive_player()

        if getattr(self, "prewarmed_path", None) != next_track["path"]:
            # Non preriscaldata (es. fade manuale a brano appena iniziato):
            # apre la sessione audio adesso
            self.players.prepare(inactive, next_track["path"])
            self.prewarmed_path = next_track["path"]
        else:
            # Già preriscaldata da monitor_playback: sessione già aperta,
            # ci si assicura solo che sia muta
            inactive.audio_set_volume(0)

        self.sync_decks_ui()

        # Imposta il punto di ingresso sulla prossima traccia
        trim_start = getattr(self, "pending_next_start", 
                           int(next_track.get("start_trim", 0) * 1000))

        # Player preriscaldato in pausa: si può settare il tempo da fermi
        try:
            inactive.set_time(trim_start) # da fermo: affidabile
        except Exception:
            pass

        # ===================== FX IN RAMPA SUL BRANO ENTRANTE =====================
        # L'FX viene agganciato quando il brano entrante è già udibile (~30% volume)
        # invece che a 150ms dall'inizio (dove è ancora quasi muto).
        # Il ritardo è proporzionale alla durata del fade.
        if self.fx_enabled:
            fx_delay = int(self.FADE_DURATION_MS * 0.15)  # ~930ms a 6200ms fade
            QTimer.singleShot(fx_delay, lambda: self.apply_random_fx(inactive))
			
        # Riattiva la riproduzione del deck entrante (era in pausa dal pre-warm):
        # partirà dal punto di ingresso, a volume 0
        try:
            inactive.play()
        except Exception:
            pass

        # ===================== AVVIA IL CROSSFADE =====================
        if getattr(self, "fade_timer", None) is not None:
            self.fade_timer.stop()
            self.fade_timer.deleteLater()  # evita accumulo di timer morti
        
        # Il fade parte da volume 0 (curva equal-power: sin(0) = 0)
        try:
            inactive.audio_set_volume(0)  # riparte da trim_start, volume 0
        except Exception:
            pass

        # Timer del fade
        self.fade_elapsed = QElapsedTimer()
        self.fade_elapsed.start()
        self._last_av = -1
        self._last_bv = -1
        self.fade_t = 0.0
        self.fade_timer = QTimer()
        self.fade_timer.timeout.connect(lambda: self._fade_step(active, inactive))
        self.fade_timer.start(20)

    def _load_next_waveform(self, track, deck):
        """Carica waveform del prossimo brano con delay"""
        wf = WaveformWorker(track, self.signals)
        wf.deck_target = deck
        self.threadpool.start(wf)

    def _fade_step(self, a, b):
        # fade_elapsed è già inizializzato in random_fade,
        t = min(1.0, self.fade_elapsed.elapsed() / self.FADE_DURATION_MS)

        # === CURVA EQUAL-POWER (mixer DJ) ===
        # out: cos(πt/2) scende dolcemente, in: sin(πt/2) sale,
        # la somma delle potenze resta ~costante durante il crossfade.
        angle = (math.pi / 2.0) * t
        av = int(round(100 * math.cos(angle)))
        bv = int(round(100 * math.sin(angle)))

        # === Mixer GUI (aggiornato ogni 2 tick, basta e avanza) ===
        self._gui_tick = getattr(self, "_gui_tick", 0) + 1
        if self._gui_tick % 2 == 0:
            if self.players._current == "A":
                self.deckA.fader.set_level(av / 100.0)
                self.deckB.fader.set_level(bv / 100.0)
                ln = a.get_length()
                if ln > 0:
                    self.deckA.waveform.set_position(max(0.0, min(1.0, a.get_time() / ln)))
            else:
                self.deckB.fader.set_level(av / 100.0)
                self.deckA.fader.set_level(bv / 100.0)
                ln = a.get_length()
                if ln > 0:
                    self.deckB.waveform.set_position(max(0.0, min(1.0, a.get_time() / ln)))

        # === Volumi reali: chiama VLC SOLO se il valore è cambiato ===
        if av != getattr(self, "_last_av", -1):
            a.audio_set_volume(av)
            self._last_av = av

        if bv != getattr(self, "_last_bv", -1):
            b.audio_set_volume(bv)
            self._last_bv = bv

        # ===================== FINE FADE =====================
        if t >= 1.0:
            self.fade_timer.stop()

            # Pulizia timer
            if hasattr(self, "fade_timer"):
                self.fade_timer.deleteLater()
                self.fade_timer = None

            if hasattr(self, "fade_elapsed"):
                del self.fade_elapsed
            self._last_av = -1
            self._last_bv = -1

            self.controls.set_match_waiting(False)

            # FIX FX MUTED: 1) stop della traccia uscente PRIMA di smontare l'EQ.
            # Rimuovere l'equalizer mentre l'altro player suona sulla stessa
            # istanza ricostruisce l'aout e puo' lasciare il nuovo player muto.
            a.stop()
            a.audio_set_volume(0)

            if hasattr(a, "equalizer") and a.equalizer is not None:
                a.set_equalizer(None)
                a.equalizer = None

            # === AVANZA TRACCIA ===
            self.current_index += 1
            self.players.switch()

            # Aggiorna GUI
            self._update_inactive_deck_preview()
            self.sync_decks_ui()

            # Volume pieno sul nuovo attivo, ribadito dopo il settle dell'aout
            b.audio_set_volume(100)
            QTimer.singleShot(250, lambda: b.audio_set_volume(100))

            # Reset stati
            self.fade_running = False
            self._fx_applied = False
            self.pending_next_start = 0
            self.prewarmed_path = None
            self._stop_fx_ramp()
            self._eq_release_started = False
            self._stop_eq_release()

            # Precarica la traccia successiva
            QTimer.singleShot(350, self._preload_next_track)
            print("\n!! Fade completato !!\n")
            #self.log_debug("Fade completato", separator=True)
        
    def _preload_next_track(self):

        """
        Precarica SEMPRE la prossima traccia
        sul deck inattivo + aggiorna GUI.
        """

        if self.current_index + 1 >= len(self.playlist):
            return

        next_track = self.playlist[self.current_index + 1]

        inactive = self.players.inactive_player()

        # sicurezza:
        # evita stessa traccia sui due deck
        active_track = self.playlist[self.current_index]

        if next_track["path"] == active_track["path"]:
            return

        self.players.load(
            inactive,
            next_track["path"]
        )

        inactive.audio_set_volume(0)

        # AGGIORNA GUI IMMEDIATAMENTE
        self._update_inactive_deck_preview()
        
    def _update_inactive_deck_preview(self):

        """
        Mostra SEMPRE sul deck inattivo
        la prossima traccia già precaricata.
        """

        if self.current_index + 1 >= len(self.playlist):
            return

        next_track = self.playlist[self.current_index + 1]

        if self.players._current == "A":

            # deck B = prossimo brano
            self.deckB.set_track(next_track)

            wf = WaveformWorker(
                next_track,
                self.signals
            )

            wf.deck_target = "B"

            self.threadpool.start(wf)

        else:

            # deck A = prossimo brano
            self.deckA.set_track(next_track)

            wf = WaveformWorker(
                next_track,
                self.signals
            )

            wf.deck_target = "A"

            self.threadpool.start(wf)

    def apply_random_fx(self, player):

        if not self.fx_enabled:
            return

        # Controllo extra: assicurati che il fade sia ancora in corso
        if not self.fade_running:
            return

        try:

            player.equalizer = vlc.libvlc_audio_equalizer_new()
            eq = player.equalizer

            effect = np.random.choice([
                'reverb',
                'echo',
                'bass',
                'lowpass',
                'highpass',
                'treble',
                'boost'
            ])

            print(f"FX → {effect.upper()} (ramp progressivo)")

            # ================= TARGET DEL PRESET =================
            # Valori FINALI di banda (indice → dB) e preamp.
            # Vengono raggiunti gradualmente dal ramp, non a scatto.
            bands = {i: 0.0 for i in range(10)}
            preamp = 0.0

            if effect == 'reverb':
                preamp = 7.5
                bands[8] = 8.5
                bands[9] = 9.5

            elif effect == 'echo':
                preamp = -5.0
                bands[0] = -8.0
                bands[1] = -6.0

            elif effect == 'bass':
                preamp = 5.0
                bands[0] = 14.0
                bands[1] = 10.0

            elif effect == 'lowpass':
                for i in range(5, 10):
                    bands[i] = -13.0

            elif effect == 'highpass':
                for i in range(0, 4):
                    bands[i] = -13.0

            elif effect == 'boost':
                preamp = 8.5

            else:  # treble
                preamp = 4.0
                bands[8] = 12.0
                bands[9] = 11.0

            # Registra lo stato e avvia la rampa
            self._fx_eq = eq
            self._fx_player = player
            self._fx_bands = bands
            self._fx_preamp = preamp
            self._fx_effect_name = effect
            self._fx_idx = 0

            # Memorizza i target anche sul player, per il rilascio a fine brano
            player._fx_bands = dict(bands)
            player._fx_preamp = preamp

            if getattr(self, "fx_ramp_timer", None) is not None:
                self.fx_ramp_timer.stop()
                self.fx_ramp_timer.deleteLater()

            # ========== MODIFICA: RAMP DURATA COME FADE ==========
            # La rampa dell'FX dura esattamente quanto il fade,
            # così l'effetto cresce insieme al volume del brano entrante.
            self.fx_ramp_timer = QTimer(self)
            self.fx_ramp_timer.timeout.connect(self._fx_ramp_step)
            self.FX_RAMP_STEPS = self.FADE_DURATION_MS // self.FX_RAMP_STEP_MS
            self.fx_ramp_timer.start(self.FX_RAMP_STEP_MS)
            # ====================================================

        except Exception as e:
            print("FX Error:", e)
            if hasattr(player, "equalizer"):
                player.set_equalizer(None)
                player.equalizer = None

    def _fx_ramp_step(self):
        """Applica le bande EQ in crescendo: niente salti di loudness"""
        if not self.fade_running or not getattr(self, "_fx_eq", None):
            self._stop_fx_ramp()
            return

        self._fx_idx = getattr(self, "_fx_idx", 0) + 1
        scale = min(1.0, self._fx_idx / float(self.FX_RAMP_STEPS))

        eq = self._fx_eq
        for i in range(10):
            vlc.libvlc_audio_equalizer_set_amp_at_index(
                eq,
                self._fx_bands[i] * scale,
                i
            )
        vlc.libvlc_audio_equalizer_set_preamp(
            eq,
            self._fx_preamp * scale
        )

        # Re-apply: VLC copia i valori nell'aout a ogni set_equalizer
        try:
            self._fx_player.set_equalizer(eq)
        except Exception as e:
            print("FX ramp error:", e)
            self._stop_fx_ramp()
            return

        if self._fx_idx >= self.FX_RAMP_STEPS:
            print(f"FX ramp completata → {self._fx_effect_name.upper()}")
            self._stop_fx_ramp()

    def _stop_fx_ramp(self):
        if getattr(self, "fx_ramp_timer", None) is not None:
            self.fx_ramp_timer.stop()
            self.fx_ramp_timer.deleteLater()
            self.fx_ramp_timer = None
			
    def _release_active_eq(self):
        """Rilascio progressivo dell'EQ sul player attivo: l'effetto
        sfuma con il brano invece di essere smontato di colpo."""
        player = self.players.active_player()
        if getattr(player, "equalizer", None) is None:
            return

        eq = player.equalizer

        bands = getattr(player, "_fx_bands", None)
        if bands is None:
            # Nessun target noto (traccia senza FX): smonta e basta
            try:
                player.set_equalizer(None)
            except Exception:
                pass
            player.equalizer = None
            return

        self._rel_eq = eq
        self._rel_player = player
        self._rel_bands = bands
        self._rel_preamp = getattr(player, "_fx_preamp", 0.0)
        self._rel_idx = 0

        if getattr(self, "eq_release_timer", None) is not None:
            self.eq_release_timer.stop()
            self.eq_release_timer.deleteLater()

        self.eq_release_timer = QTimer(self)
        self.eq_release_timer.timeout.connect(self._eq_release_step)
        self.eq_release_timer.start(self.EQ_RELEASE_STEP_MS)

    def _eq_release_step(self):
        idx = self._rel_idx + 1
        self._rel_idx = idx
        scale = max(0.0, 1.0 - idx / float(self.EQ_RELEASE_STEPS))

        eq = self._rel_eq
        for i in range(10):
            vlc.libvlc_audio_equalizer_set_amp_at_index(
                eq, self._rel_bands[i] * scale, i
            )
        vlc.libvlc_audio_equalizer_set_preamp(eq, self._rel_preamp * scale)

        try:
            self._rel_player.set_equalizer(eq)
        except Exception:
            self._stop_eq_release()
            return

        if idx >= self.EQ_RELEASE_STEPS:
            print("EQ release completata (effetto sfumato col brano)")
            self._stop_eq_release()

    def _stop_eq_release(self):
        if getattr(self, "eq_release_timer", None) is not None:
            self.eq_release_timer.stop()
            self.eq_release_timer.deleteLater()
            self.eq_release_timer = None
        
    def should_start_smart_fade(self, current, next_track, current_time, remaining):
        if not self.auto_fade_enabled or self.fade_running:
            return False

        if remaining > 40000:
            return False

        if current_time - getattr(self, 'last_fade_time', 0) < 10000:
            return False

        bpm_diff = abs(current["tempo"] - next_track["tempo"])
        energy_diff = abs(current.get("energy", 0.5) - next_track.get("energy", 0.5))

        if bpm_diff > 15 or energy_diff > 0.25:
            return False

        engine = CrossFadeEngine()
        
        # ✅ Correzione importante
        target_out, target_in = engine.get_best_phrase_match(
            current, next_track, current_time=current_time
        )

        self.pending_next_start = target_in
        distance = target_out - current_time

        if 800 < distance < 14500:
            print(f"SMART FADE TRIGGERED (tra {distance/1000:.1f}s)")
            self.last_fade_time = current_time
            return True

        return False
    
    def monitor_playback(self):
        """
        Timer che corre ogni 15ms per monitorare lo stato della riproduzione.
        Gestisce:
        1. Aggiornamento visuale della waveform (playhead).
        2. Calcolo del tempo restante.
        3. Trigger automatici per il fade (Smart Fade, Safety Fade, ecc.).
        """
        
        # 1. Controllo base: se non stiamo suonando o c'è già un fade in corso, esci subito
        if not self.is_playing or self.fade_running:
            return

        # 2. Accesso sicuro alla playlist (lock thread)
        with self.playlist_lock:
            # Verifica che l'indice corrente sia valido
            if self.current_index < 0 or self.current_index >= len(self.playlist):
                return
            
            track = self.playlist[self.current_index]
            # Ottieni la traccia successiva se esiste
            next_track = self.playlist[self.current_index + 1] if self.current_index + 1 < len(self.playlist) else None

        # 3. Gestione fine playlist
        if not next_track:
            self._handle_playlist_end()
            return
        
        # 4. Recupera il player attivo e i tempi
        player = self.players.active_player()
        current_time = player.get_time()
        length = player.get_length()

        # 5. SICUREZZA: Evita divisione per zero o valori negativi prima di aggiornare la UI
        # Se la lunghezza è 0 o negativa (es. file corrotto o caricamento fallito), esci
        if length <= 0:
            return

        # 6. Calcolo frazione per la waveform
        fraction = current_time / length
        
        # Clamp la frazione tra 0.0 e 1.0 per evitare errori di visualizzazione
        if fraction > 1.0:
            fraction = 1.0
        if fraction < 0.0:
            fraction = 0.0

        # 7. Aggiornamento visuale del playhead (Linea rossa)
        # Questo aggiornamento è ora sicuro grazie ai controlli precedenti sulla 'length' e 'fraction'
        try:
            if self.players._current == "A":
                self.deckA.waveform.set_position(fraction)
            else:
                self.deckB.waveform.set_position(fraction)
        except Exception as e:
            # In caso di errore raro nel widget waveform, stampa ma continua
            # print(f"⚠️ Errore aggiornamenti playhead: {e}")
            pass
		
        # === GUARDIA VOLUME ===
        # Fuori dal fade il player attivo deve essere a volume pieno.
        # Se un EQ/aout ricostruito lo ha lasciato muto, lo recuperiamo.
        try:
            if player.audio_get_volume() < 100:
                player.audio_set_volume(100)
        except Exception:
            pass

        # === GUARDIA VOLUME PRE-WARM (FIX WINDOWS) ===
        # Tra il pre-warm e l'inizio del fade, il player inattivo deve restare muto
        if getattr(self, "prewarmed_path", None) is not None:
            try:
                inactive = self.players.inactive_player()
                if inactive.audio_get_volume() != 0:
                    inactive.audio_set_volume(0)
            except Exception:
                pass
		
        # --- LOGICA AUTOMATICA DI FADE ---
        # Calcolo del tempo rimanente reale basato sui trim (end_trim)
        # Usiamo end_trim perché rappresenta la fine dell'audio utile, escludendo il silenzio finale
        real_end_ms = int(track.get("end_trim", track["duration"]) * 1000)
        remaining = real_end_ms - current_time

        # Assicurati che 'remaining' non diventi negativo per errori di calcolo
        if remaining < 0:
            remaining = 0
			
        # === RILASCIO PROGRESSIVO FX ===
        # Negli ultimi ~25s l'effetto sfuma invece di essere smontato
        # bruscamente da prepare() al momento del pre-warm successivo.
        if (
            self.fx_enabled
            and remaining <= self.EQ_RELEASE_BEFORE_MS
            and not self._eq_release_started
        ):
            self._eq_release_started = True
            self._release_active_eq()
            
        # === PRE-WARM AUDIO (FIX WINDOWS) ===
        # Apre in anticipo lo stream audio della prossima traccia (muta):
        # se la sessione WASAPI viene creata durante il fade, il driver
        # puo' interrompere per un attimo lo stream in riproduzione.
        if next_track and 2000 < remaining < 45000:
            if getattr(self, "prewarmed_path", None) != next_track["path"]:
                self.players.prepare(
                    self.players.inactive_player(),
                    next_track["path"]
                )
                self.prewarmed_path = next_track["path"]

        if self.auto_fade_enabled:
            
            # 🔥 SAFETY NET PRINCIPALE (Ultimi 3 secondi)
            # Se mancano meno di 3 secondi, FORZA un fade immediato.
            # Questo garantisce il passaggio anche se i calcoli precedenti (smart match) sono falliti.
            if remaining <= 3000 and remaining > 0:
                print(f"⚡ SAFETY FADE: Solo {remaining/1000:.1f}s rimasti! Fade immediato.")
                if not self.fade_running:
                    self.random_fade(force=True)
                return # Esci dopo aver attivato il fade

            # Fallback a 6 secondi (seconda linea di difesa)
            if remaining <= 6000:
                 print(f"⚡ AUTO FADE: 6s threshold - Fade Now")
                 if not self.fade_running:
                     self.random_fade(force=True)
                 return

            # Logica "Fade Next Match" (tra 10s e 16s)
            # Cerca un punto di transizione armonico disponibile entro breve
            if remaining <= 16000 and remaining > 10000:
                if not self.fade_running and not getattr(self, 'fade_pending_match', False):
                    print(f"🕒 AUTO FADE: 16s threshold - Avvio Fade Next Match")
                    self.fade_next_match()
                    return

            # Logica "Smart Fade" (cerca il match perfetto in qualsiasi momento precedente)
            # Questa funzione controlla BPM, Key e armonia per trovare il punto ideale
            if self.should_start_smart_fade(track, next_track, current_time, remaining):
                # should_start_smart_fade gestisce i propri log interni
                self.random_fade(force=True)

        else:
            # Opzionale: Se Auto Fade è DISATTIVATO, passa al successivo all'ultimo secondo
            # anche senza spuntare la checkbox "Auto Random Fade".
            if remaining <= 1000 and not self.fade_running:
                print("⏳ Fine brano, passaggio manuale forzato...")
                self.random_fade(force=True)

    def seek_player(self, deck, fraction):
        player = self.players.playerA if deck == "A" else self.players.playerB
        length = player.get_length()
        if length > 0:
            if deck == "A":
                track = getattr(self.deckA, "track", None)
            else:
                track = getattr(self.deckB, "track", None)

            if not track:
                return

            start = int(track["start_trim"] * 1000)
            end = int(track["end_trim"] * 1000)

            real_length = end - start

            player.set_time(start + int(real_length * fraction))

    def show_info(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("pyAutoDJ")
        
        # HTML con il link e il nuovo bottone per aprire la finestra Debug
        html_text = """
        <h2 style='text-align:center;'>pyAutoDJ</h2>
        <p style='text-align:center;'>
            <b>Version:</b> 1.1 rev.7<br><br>
            <b>Author:</b> MoonDragon<br><br><br>
            <p>• Vinyl Simulation</p>
            <p>• Waveform Seek</p>
            <p>• Manual Fade Now</p>
            <p>• Semi-Manual Fade Next Match (Smart Transition)</p>
            <p>• Auto Random Fade (Smart Transition)</p>
            <p>• FX during transition</p>
            <p>• Debug window</p><br><br>
            Site: <a href='https://github.com/MoonDragon-MD/pyAutoDJ'>https://github.com/MoonDragon-MD/pyAutoDJ</a>
        </p>
        """
        
        msg.setText(html_text)
        msg.setTextFormat(Qt.RichText) # Abilita i link HTML
        
        # Aggiungiamo un pulsante personalizzato per il Debug
        debug_btn = msg.addButton("Open Debug Console", QMessageBox.ActionRole)
        
        msg.setStandardButtons(QMessageBox.Ok)
        msg.setModal(False)
        
        # Mostra la finestra
        msg.show()

        def handle_button_click():
            clicked_btn = msg.clickedButton()
            if clicked_btn == debug_btn:
                self.debug_window.show()
                # Chiudiamo la finestra di info
                msg.close()
        
        msg.buttonClicked.connect(lambda btn: self._handle_info_button(btn, debug_btn))

    def _handle_info_button(self, btn, debug_btn):
        """Gestisce il click sui pulsanti della finestra Info"""
        if btn == debug_btn:
            self.debug_window.show()
            # Chiudi la finestra Info dopo aver aperto il debug
            self.sender().close() 
            
    def log_debug(self, message, separator=False):
        """Invia un messaggio alla console di debug con timestamp"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        formatted_msg = f"[{timestamp}] {message}"
        
        if separator:
            # Aggiunge una riga vuota prima e dopo
            self.signals.debugLog.emit("\n")      # Righe vuota prima
            self.signals.debugLog.emit(formatted_msg + "\n") # Messaggio + a capo
            self.signals.debugLog.emit("\n")      # Righe vuota dopo
        else:
            # Messaggio normale con a capo alla fine
            self.signals.debugLog.emit(formatted_msg + "\n")
        

    def handle_dropped_files(self, files):
        if not files:
            return

        # Dedup interno + rimozione dei file già in libreria
        known = {t["path"] for t in self.library}
        files_to_load = [f for f in dict.fromkeys(files) if f not in known]

        if not files_to_load:
            QMessageBox.information(self, "Nessun file", "Nessun nuovo file audio trovato.")
            return

        print(f"Trovati {len(files_to_load)} file audio da caricare")

        self.loading_total += len(files_to_load)
        self.loading_done = 0
        self.pending_waveforms = len(files_to_load)

        self.controls.progress.show()
        self.controls.taskLabel.setText(
            f"Aggiunte {len(files_to_load)} tracce (totale: {len(self.library)})...")

        # Stessa coda limitata di load_files: max 5 worker attivi,
        # nessun avvio massivo nel loop → niente freeze in fullscreen.
        queue = deque(files_to_load)

        if hasattr(self, "process_queue_timer") and self.process_queue_timer.isActive():
            self.process_queue_timer.stop()

        self.process_queue_timer = QTimer()
        self.process_queue_timer.timeout.connect(lambda: self._process_next_file(queue))
        self.process_queue_timer.start(50)

    def closeEvent(self, event):
        self._cancel_pending_match()
        self._stop_fx_ramp()
        self._stop_eq_release()
        self.players.stop_all()
        self.monitor.stop()
        event.accept()
