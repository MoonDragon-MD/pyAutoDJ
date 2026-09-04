# pyAutoDJ

Automatic Digital Audio Workstation for DJing with intelligent transitions based on harmonic analysis (DTW chroma), BPM synchronization, and real-time FX.

### Dependencies

Python 3.6+ (tested on Windows and Ubuntu with versions 3.6, 3.8, 3.10, 3.12, 3.14)

**Python Dependencies:**
```bash
pip install PyQt5 vlc librosa numpy mutagen soundfile pyqtgraph
```

**System Dependencies:**
- **Windows:** VLC Media Player from the official website + pip
    ```bash
  python -m pip install python-vlc
  ```
- **Linux (Debian/Ubuntu):**
  ```bash
  sudo apt-get install vlc libvlc-dev python3-vlc
  ```

### Usage

**Standard Launch (Linux):**
```bash
python3 main.py
```

**Standard Launch (Windows):**
```bash
python main.py
```

**Dual-instance VLC Mode (Linux only):**
```bash
python3 main.py --dual-vc
```
*Note: On Windows, the dual-instance option is automatically ignored to prevent crackling during crossfade (WASAPI).*

**Startup Scripts:**
- **Windows:** `Start-win.bat`
- **Linux:** `Start.sh` (standard) or `Start_2vlc.sh` (dual instance)

**Installer for linux menu:**

place inside the pyAutoDJ folder and run

```bash
./installer.sh
```
This will copy the folder to a fixed place and create the launcher for the Linux menu

### Features

| Feature | Description |
|---------|-------------|
| **Vinyl Simulation** | Realistic rotating vinyl graphics synchronized with audio |
| **Waveform Seek** | Click/drag on waveform to seek positions in the track |
| **Manual Fade Now** | Immediate fade to the next track |
| **Fade Next Match** | Semi-manual fade to the next available harmonic match (smart transition) |
| **Auto Random Fade** | Creative automatic fade with intelligent random selection of entry points |
| **Smart Transitions** | DTW chromatic + BPM + energy analysis to find optimal matching points between tracks |
| **Progressive FX** | Reverb, echo, bass, lowpass, highpass, treble, boost with smooth ramp synced to fade |
| **Progressive FX Release** | Effects fade out naturally in the last 25 seconds of the track |
| **Loop Playlist** | Dialog at end of playlist to restart or enable continuous loop |
| **Pre-warm Audio** | Pre-opened WASAPI session to avoid dropout at fade start |
| **Equal-power Crossfade** | Sinusoidal curve maintaining constant perceived power |
| **Harmonic Mixing** | Circle of Fifths for harmonic bonus in playlist calculation |
| **Debug Window** | Integrated log window to monitor events and debug |
| **Cover Art** | Automatic extraction of album covers from MP3/FLAC metadata |
| **Drag & Drop** | File and folder loading via drag-and-drop |
| **audio Auto-Cut** | Cuts the silences at the beginning and end of the song |
| **VLC Portable Ready** | Only-Windows: Just uncomment to get vlc portable and copy the required files |
| **Python Portable Ready** | Only-Windows: Just download python embed and launch the appropriate bat |

### Screenshot

![pyAutoDJ Main Interface](https://github.com/MoonDragon-MD/pyAutoDJ/blob/main/img/Schermata1.jpg?raw=true)

![pyAutoDJ Playlist View](https://github.com/MoonDragon-MD/pyAutoDJ/blob/main/img/Schermata2.jpg?raw=true)

![pyAutoDJ FX & Controls](https://github.com/MoonDragon-MD/pyAutoDJ/blob/main/img/Schermata3.jpg?raw=true)

### Known Limitations

- Python < 3.6 not supported (f-strings)
- Dual-instance VLC on Windows causes crackling (automatically disabled)
- Initial file analysis takes time (librosa + chroma + DTW) [It runs faster on Linux]
