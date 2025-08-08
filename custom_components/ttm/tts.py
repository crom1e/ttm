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

# User-facing options (no language)
CONF_WPM = "wpm"
CONF_FREQ = "frequency"
CONF_VOLUME = "volume"

DEFAULT_WPM = 18
DEFAULT_FREQ = 700
DEFAULT_VOLUME = 1.0

PLATFORM_SCHEMA = TTS_PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME, default="Morse (ttm)"): cv.string,
        vol.Optional(CONF_WPM, default=DEFAULT_WPM): cv.positive_int,
        vol.Optional(CONF_FREQ, default=DEFAULT_FREQ): cv.positive_int,
        vol.Optional(CONF_VOLUME, default=DEFAULT_VOLUME): vol.All(
            vol.Coerce(float), vol.Range(min=0.0, max=1.0)
        ),
        # Note: no language option exposed
    }
)


def unit_ms(wpm: int) -> int:
    """Length of one 'dit' in milliseconds (PARIS standard)."""
    return int(round(1200 / max(1, wpm)))


def _tone(duration_ms: int, freq: int, volume: float) -> AudioSegment:
    seg = Sine(freq).to_audio_segment(duration=duration_ms)
    if volume <= 0:
        return AudioSegment.silent(duration=duration_ms)
    gain_db = 20.0 * (volume - 1.0)  # simple linear→dB approx
    return seg.apply_gain(gain_db)


def _silence(duration_ms: int) -> AudioSegment:
    return AudioSegment.silent(duration=duration_ms)


class MorseProvider(Provider):
    """TTS provider that renders text as Morse code audio."""

    def __init__(self, name: str, wpm: int, freq: int, volume: float) -> None:
        self._name = name
        self._wpm = wpm
        self._freq = freq
        self._volume = volume

    # ---- Language API (kept minimal so HA hides the selector) ----
    @property
    def default_language(self) -> str:
        # Required by HA; fixed value so no UI selection is shown.
        return "en"

    @property
    def supported_languages(self) -> list[str]:
        # Single language → HA will not render a language dropdown.
        return ["en"]

    @property
    def supported_options(self) -> list[str]:
        # No per-call options exposed (keeps UI simple).
        return []

    @property
    def name(self) -> str:
        return self._name

    async def async_get_tts_audio(
        self, message: str, language: str, options: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, bytes]:
        # 'language' is passed by HA but ignored here on purpose.
        morse = text_to_morse(message)

        u = unit_ms(self._wpm)
        dit = u
        dah = 3 * u
        intra_gap = u
        char_gap = 3 * u
        word_gap = 7 * u

        audio = AudioSegment.silent(0)

        # Tokenize morse string into characters and word separators
        tokens = []
        for chunk in morse.split(" "):
            if chunk == "/":
                tokens.append(("/",))
            else:
                tokens.append(tuple(chunk))

        for token in tokens:
            if token == ("/",):
                audio += _silence(word_gap)
                continue

            for i, symbol in enumerate(token):
                if symbol == ".":
                    audio += _tone(dit, self._freq, self._volume)
                elif symbol == "-":
                    audio += _tone(dah, self._freq, self._volume)
                if i != len(token) - 1:
                    audio += _silence(intra_gap)

            audio += _silence(char_gap)

        audio = audio.set_frame_rate(44100).set_channels(1)
        wav_bytes = audio.export(format="wav").read()
        return ("wav", wav_bytes)


async def async_get_engine(hass: HomeAssistant, config: dict, discovery_info=None):
    name = config.get(CONF_NAME, "Morse (Text to Morse)")
    wpm = config.get(CONF_WPM, DEFAULT_WPM)
    freq = config.get(CONF_FREQ, DEFAULT_FREQ)
    volume = config.get(CONF_VOLUME, DEFAULT_VOLUME)

    return MorseProvider(name=name, wpm=wpm, freq=freq, volume=volume)
