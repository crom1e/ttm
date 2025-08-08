from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

import voluptuous as vol
from homeassistant.components.tts import (
    Provider,
    PLATFORM_SCHEMA as TTS_PLATFORM_SCHEMA,
)
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv

from pydub import AudioSegment
from pydub.generators import Sine

from .morse import text_to_morse

_LOGGER = logging.getLogger(__name__)

CONF_WPM = "wpm"
CONF_FREQ = "frequency"
CONF_VOLUME = "volume"
CONF_LANGUAGE = "language"

DEFAULT_WPM = 18
DEFAULT_FREQ = 700
DEFAULT_VOLUME = 1.0
DEFAULT_LANGUAGE = "en"  # uvesentlig her, men TTS-API forventer språk

PLATFORM_SCHEMA = TTS_PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME, default="Morse (ttm)"): cv.string,
        vol.Optional(CONF_WPM, default=DEFAULT_WPM): cv.positive_int,
        vol.Optional(CONF_FREQ, default=DEFAULT_FREQ): cv.positive_int,
        vol.Optional(CONF_VOLUME, default=DEFAULT_VOLUME): vol.All(
            vol.Coerce(float), vol.Range(min=0.0, max=1.0)
        ),
        vol.Optional(CONF_LANGUAGE, default=DEFAULT_LANGUAGE): cv.string,
    }
)

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

class MorseProvider(Provider):
    def __init__(self, name: str, wpm: int, freq: int, volume: float, language: str) -> None:
        self._name = name
        self._wpm = wpm
        self._freq = freq
        self._volume = volume
        self._language = language

    @property
    def default_language(self) -> str:
        return self._language

    @property
    def supported_languages(self) -> list[str]:
        return [self._language]

    @property
    def supported_options(self) -> list[str]:
        # could expose per-call overrides (e.g., wpm) via options; keep empty for simplicity
        return []

    @property
    def name(self) -> str:
        return self._name

    async def async_get_tts_audio(
        self, message: str, language: str, options: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, bytes]:
        # Build Morse WAV bytes
        morse = text_to_morse(message)
        u = unit_ms(self._wpm)
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
                    audio += _tone(dit, self._freq, self._volume)
                elif symbol == '-':
                    audio += _tone(dah, self._freq, self._volume)
                if i != len(token) - 1:
                    audio += _silence(intra_gap)
            audio += _silence(char_gap)

        audio = audio.set_frame_rate(44100).set_channels(1)
        wav_bytes = audio.export(format="wav").read()

        return ("wav", wav_bytes)

async def async_get_engine(hass: HomeAssistant, config: dict, discovery_info=None):
    name = config.get(CONF_NAME, "Morse (ttm)")
    wpm = config.get(CONF_WPM, DEFAULT_WPM)
    freq = config.get(CONF_FREQ, DEFAULT_FREQ)
    volume = config.get(CONF_VOLUME, DEFAULT_VOLUME)
    language = config.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)
    return MorseProvider(name=name, wpm=wpm, freq=freq, volume=volume, language=language)
