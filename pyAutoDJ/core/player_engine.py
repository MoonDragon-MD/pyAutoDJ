import vlc
import sys
import os
import time

class PlayerEngine:

    def __init__(self, use_separate_vlc=False):
        """
        Args:
            use_separate_vlc: Se True, prova a creare 2 instanze VLC separate.
                             Se fallisce, usa 1 istanza con 2 player.
        """
        common_options = [
            '--quiet',
            '--no-stats', 
            '--no-video-title-show',
            '--no-xlib'
        ]
        
        self.use_separate_vlc = False
        
        if use_separate_vlc:
            print("📼 Tentativo modalità Dual Instance VLC...")
            try:
                self.instanceA = vlc.Instance(' '.join(common_options))
                self.instanceB = vlc.Instance(' '.join(common_options))
                
                if self.instanceA is None or self.instanceB is None:
                    raise RuntimeError("VLC instance creation failed")
                
                self.playerA = self.instanceA.media_player_new()
                self.playerB = self.instanceB.media_player_new()
                
                if self.playerA is None or self.playerB is None:
                    raise RuntimeError("Media player creation failed")
                
                self.use_separate_vlc = True
                print("✅ VLC Dual Instance: Successo!")
                
            except Exception as e:
                print(f"⚠️ Errore Dual Instance ({e}), fallback su Single Instance...")
                self._create_single_instance(common_options)
        else:
            self._create_single_instance(common_options)
        
        # =================== INIZIALIZZAZIONE CRITICA ===================
        self._current = "A"  # ← AGGIUNTO QUI: deve essere prima dei player
        # ================================================================
        
        self.playerA.set_video_title_display(False, 0)
        self.playerB.set_video_title_display(False, 0)

    def _create_single_instance(self, common_options):
        """Metodo helper per creare una singola istanza"""
        try:
            self.instance = vlc.Instance(' '.join(common_options))
            
            if self.instance is None:
                raise RuntimeError("Failed to create VLC instance")
            
            self.playerA = self.instance.media_player_new()
            self.playerB = self.instance.media_player_new()
            
            if self.playerA is None or self.playerB is None:
                raise RuntimeError("Failed to create media players")
                
            self.use_separate_vlc = False
            print("✅ VLC Single Instance: Successo!")
            
        except Exception as e:
            raise RuntimeError(
                f"❌ Impossibile inizializzare VLC: {e}\n"
                "   Assicurati di avere VLC installato:\n"
                "   Windows: Scarica dal sito ufficiale\n"
                "   Linux: sudo apt-get install vlc libvlc-dev python3-vlc\n"
                "   macOS: brew install vlc"
            )

    def active_player(self):
        return self.playerA if self._current == "A" else self.playerB  # ← Usa _current direttamente

    def inactive_player(self):
        return self.playerB if self._current == "A" else self.playerA  # ← Usa _current direttamente

    def switch(self):
        self._current = "B" if self._current == "A" else "A"  # ← Usa _current direttamente

    def is_ready(self, player):
        state = player.get_state()
        return state in (vlc.State.Playing, vlc.State.Opening, vlc.State.Buffering)
    
    def load(self, player, path):
        if self.use_separate_vlc:
            instance_to_use = self.instanceA if player == self.playerA else self.instanceB
        else:
            instance_to_use = self.instance
            
        media = instance_to_use.media_new(path)
        player.set_media(media)
        if not media:
            print(f"⚠️ Errore caricamento: {path}")

    def stop_all(self):
        self.playerA.stop()
        self.playerB.stop()

    def prepare(self, player, path, timeout_ms=3000):
        # FIX: l'equalizer persiste sul player anche dopo set_media:
        # smontiamo sempre un EQ rimasto appeso da un FX precedente
        if getattr(player, "equalizer", None) is not None:
            try:
                player.set_equalizer(None)
            except Exception:
                pass
            player.equalizer = None

        self.load(player, path)
        player.audio_set_volume(0)
        player.play()

        start = time.time()
        while time.time() - start < timeout_ms / 1000:
            if player.get_state() == vlc.State.Playing:
                # FIX WASAPI: su Windows il volume impostato prima del play
                # puo' essere ignorato dalla sessione audio. Lo ribadiamo
                # DOPO che lo stream e' effettivamente partito.
                player.audio_set_volume(0)
                return True
            time.sleep(0.05)
        player.audio_set_volume(0)
        return False