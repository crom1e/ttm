
# Text to Morse (ttm) — Home Assistant Custom Component

A Home Assistant integration that converts any text into **Morse code audio** and plays it on any `media_player` entity.

This integration works in **two ways**:

1. **TTS Engine** — appears in the media player "more-info" panel alongside other TTS providers (e.g., Google TTS).  
2. **Service Call** — `ttm.play` can be called directly from automations, scripts, or Developer Tools.

---

## Features
- Convert arbitrary text into Morse code audio.
- Adjustable:
  - **Transmission speed** (Words Per Minute / WPM)
  - **Tone frequency** in Hz
  - **Output volume** (0.0–1.0)
- Outputs **WAV audio** for maximum compatibility.
- Fully integrated with Home Assistant's **Text-to-Speech (TTS)** UI.
- Works on all media players that support WAV playback over HTTP.
- No `ffmpeg` dependency — works with pure Python audio generation.
- Simple to extend or customize.

---

## Installation

### Option 1 — HACS (Recommended)
1. Go to **HACS → Integrations → Menu (⋮) → Custom repositories**.
2. Add your GitHub repository URL.
3. Select category **Integration**.
4. Install **Text to Morse (ttm)**.
5. Restart Home Assistant.

### Option 2 — Manual
1. Download or clone this repository.
2. Copy the `custom_components/ttm` folder into:
   ```
   config/custom_components/ttm
   ```
3. Restart Home Assistant.

---

## Setup

### 1. Enable as TTS Engine (recommended for UI use)
Add this to your `configuration.yaml`:
```yaml
tts:
  - platform: ttm
    name: Text-to-Morse
    wpm: 18        # Optional, default 18
    frequency: 700 # Hz, optional
    volume: 1.0    # 0.0–1.0, optional
```

Restart Home Assistant.  
Now you will see **Text-to-Morse (ttm)** in the **TTS** dropdown of the media player’s more-info panel.

---

### 2. Use as a Service
This works even without adding the `tts:` entry above.

Call the service `ttm.play`:

```yaml
service: ttm.play
data:
  text: "SOS Testing 123"
  entity_id: media_player.living_room
  wpm: 18          # Optional
  frequency: 700   # Hz, optional
  volume: 0.8      # Optional
```

You can call it:
- From **Developer Tools → Services**
- From **Automations**
- From **Scripts**

---

## Example Automation
This automation plays "ALERT" in Morse code whenever a specific sensor triggers:

```yaml
alias: Alert in Morse
trigger:
  - platform: state
    entity_id: binary_sensor.door_sensor
    to: "on"
action:
  - service: ttm.play
    data:
      text: "ALERT"
      entity_id: media_player.kitchen
      wpm: 20
      frequency: 750
      volume: 1.0
mode: single
```

---

## How it works
- Text is mapped to Morse symbols (`.` for dits, `-` for dahs) using `morse.py`.
- Timing is calculated according to the **PARIS standard**:
  - 1 unit = dit length = `1200 / WPM` milliseconds
  - dah = 3 units
  - intra-character gap = 1 unit
  - inter-character gap = 3 units
  - word gap = 7 units
- Audio is generated using `pydub` with a sine wave generator.
- In **TTS mode**, the WAV bytes are streamed directly to the media player through HA’s TTS system.
- In **service mode**, the WAV file is saved in `/config/www/ttm` and played via `/local/ttm/<filename>.wav`.

---

## Requirements
- Home Assistant 2023.8.0 or newer.
- `pydub` (installed automatically via manifest).
- A media player that supports WAV playback via HTTP (most do).

---

## Advanced Customization
You can fork this repo and:
- Change the default tone frequency.
- Change audio format (WAV → MP3, OGG, etc.).
- Add extra service fields (e.g., adjustable tone length).
- Localize the Morse mapping for non-English alphabets.

---


## Developer Notes

### Local development / reloading
- Place the integration under `config/custom_components/ttm`.
- Use **Settings → Developer Tools → YAML → Restart** to reload.
- Watch logs under **Settings → System → Logs**.

### Versioning
- Update `version` in `manifest.json` for every release so HACS detects updates.

### Optional: Script blueprint
Consider adding a script blueprint under `blueprints/script/ttm/play_morse.yaml` so users can create a ready‑made script with a form UI without copying YAML.

---

## License
MIT License — see LICENSE file for details.

---

## Credits
- pydub for audio generation.
- Morse code timing based on the PARIS standard.
