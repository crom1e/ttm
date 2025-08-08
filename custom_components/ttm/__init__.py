from __future__ import annotations

import datetime as dt
import os
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.typing import ConfigType
from homeassistant.components.media_player import DOMAIN as MP_DOMAIN

from .morse import text_to_morse
from pydub import AudioSegment
from pydub.generators import Sine

DOMAIN = "ttm"
DEFAULT_WPM = 18
DEFAULT_FREQ = 700
DEFAULT_VOLUME = 1.0

def unit_ms(wpm: int) -> int:
    return int(round(1200 / max(1, wpm)))

def _tone(duration_ms: int, freq: int, volume: float) -> AudioSegment:
    seg = Sine(freq).to_audio_segment(duration=duration_ms)
    if volume <= 0:
        return AudioSegment.silent(duration=duration_ms)
    gain_db = 20.0 * (volume - 1.0)
    return seg.apply_gain(gain_db)

def _silence(duration_ms: int) -> AudioSegment:
    return AudioSegment.silent(duration=duration_ms)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    async def handle_play(call: ServiceCall) -> None:
        text: str = call.data.get("text", "")
        entity_id: str = call.data.get("entity_id")
        wpm: int = int(call.data.get("wpm", DEFAULT_WPM))
        freq: int = int(call.data.get("frequency", DEFAULT_FREQ))
        volume: float = float(call.data.get("volume", DEFAULT_VOLUME))

        if not text or not entity_id:
            return

        morse = text_to_morse(text)
        u = unit_ms(wpm)

        def build_audio() -> str:
            dit = u
            dah = 3 * u
            intra_gap = u
            char_gap = 3 * u
            word_gap = 7 * u

            audio = AudioSegment.silent(0)

            tokens = []
            for chunk in morse.split(' '):
                if chunk == '/':
                    tokens.append(('/',))
                else:
                    tokens.append(tuple(chunk))

            for token in tokens:
                if token == ('/',):
                    audio += _silence(word_gap)
                    continue
                for i, symbol in enumerate(token):
                    if symbol == '.':
                        audio += _tone(dit, freq, volume)
                    elif symbol == '-':
                        audio += _tone(dah, freq, volume)
                    if i != len(token) - 1:
                        audio += _silence(intra_gap)
                audio += _silence(char_gap)

            outdir = hass.config.path("www", "ttm")
            os.makedirs(outdir, exist_ok=True)
            stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            path = os.path.join(outdir, f"ttm-{stamp}.wav")
            audio = audio.set_frame_rate(44100).set_channels(1)
            audio.export(path, format="wav")
            return path

        path = await hass.async_add_executor_job(build_audio)

        rel = os.path.relpath(path, hass.config.path("www"))
        url = f"/local/{rel.replace(os.sep, '/')}"
        await hass.services.async_call(MP_DOMAIN, "play_media", {
            "entity_id": entity_id,
            "media_content_id": url,
            "media_content_type": "music",
        }, blocking=False)

    hass.services.async_register(DOMAIN, "play", handle_play)
    return True
