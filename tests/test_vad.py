from types import SimpleNamespace
import wave

import numpy as np
import pytest

from GameSentenceMiner import vad
from GameSentenceMiner.util.models.model import VADResult


def _make_config(vad_overrides=None, audio_overrides=None):
    """SimpleNamespace shaped like get_config() with the attrs the VAD pipeline reads."""
    vad_values = {
        "short_audio_min_seconds": vad.SHORT_AUDIO_MIN_SECONDS_DEFAULT,
        "short_audio_seconds_per_char": vad.SHORT_AUDIO_SECONDS_PER_CHAR_DEFAULT,
        "cut_and_splice_segments": False,
        "splice_padding": 0.1,
        "beginning_offset": 0.0,
        "trim_beginning": False,
    }
    if vad_overrides:
        vad_values.update(vad_overrides)
    audio_values = {"beginning_offset": 0.0, "end_offset": 0.0, "extension": "opus"}
    if audio_overrides:
        audio_values.update(audio_overrides)
    return SimpleNamespace(
        vad=SimpleNamespace(**vad_values),
        audio=SimpleNamespace(**audio_values),
    )


class _FakeGameLine:
    """Minimal stand-in for a game line; _validate_detection reads .text and .next_line()."""

    def __init__(self, text="", next_line=None):
        self.text = text
        self._next_line = next_line

    def next_line(self):
        return self._next_line


def _write_pcm16_wav(path, samples, sample_rate=16000, channels=1):
    samples = np.asarray(samples, dtype=np.int16)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(samples.tobytes())


def test_load_whisper_audio_from_wav_returns_normalized_float32(tmp_path):
    samples = np.array([-32768, -16384, 0, 16384, 32767], dtype=np.int16)
    wav_path = tmp_path / "speech.wav"
    _write_pcm16_wav(wav_path, samples)

    audio = vad._load_whisper_audio_from_wav(str(wav_path))

    assert audio.dtype == np.float32
    np.testing.assert_allclose(audio, samples.astype(np.float32) / 32768.0)


def test_load_whisper_audio_from_wav_rejects_wrong_sample_rate(tmp_path):
    wav_path = tmp_path / "speech.wav"
    _write_pcm16_wav(wav_path, [0, 1, 2], sample_rate=8000)

    with pytest.raises(RuntimeError, match="16 kHz"):
        vad._load_whisper_audio_from_wav(str(wav_path))


def test_whisper_vad_transcribes_decoded_audio_array(monkeypatch):
    decoded_audio = np.array([0.0, 0.5, -0.5], dtype=np.float32)

    class FakeTempWav:
        def __init__(self, input_audio):
            self.input_audio = input_audio

        def __enter__(self):
            return "temp.wav"

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeModel:
        def __init__(self):
            self.received_audio = None
            self.received_kwargs = None

        def transcribe(self, audio, **kwargs):
            self.received_audio = audio
            self.received_kwargs = kwargs
            # faster-whisper returns (segments_iterable, info)
            return iter([]), SimpleNamespace(language="ja")

    fake_model = FakeModel()
    processor = vad.WhisperVADProcessor()
    processor.vad_model = fake_model

    monkeypatch.setattr(vad, "TempWav", FakeTempWav)
    monkeypatch.setattr(vad, "_load_whisper_audio_from_wav", lambda path: decoded_audio)
    monkeypatch.setattr(
        vad,
        "get_config",
        lambda: SimpleNamespace(
            general=SimpleNamespace(target_language="ja"),
            vad=SimpleNamespace(use_vad_filter_for_whisper=True),
        ),
    )

    result = processor._detect_voice_activity("input.mp3", "")

    assert result.segments == []
    assert fake_model.received_audio is decoded_audio
    assert fake_model.received_kwargs["language"] == "ja"
    assert fake_model.received_kwargs["vad_filter"] is True
    assert fake_model.received_kwargs["word_timestamps"] is True


def test_silero_vad_converts_sample_indices_to_seconds(monkeypatch):
    class FakeTempWav:
        def __init__(self, input_audio):
            pass

        def __enter__(self):
            return "temp.wav"

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(vad, "TempWav", FakeTempWav)
    monkeypatch.setattr(vad, "_load_whisper_audio_from_wav", lambda path: np.zeros(16000, dtype=np.float32))

    import faster_whisper.vad as fw_vad

    # faster-whisper returns speech chunks as sample indices; the processor divides by 16 kHz.
    monkeypatch.setattr(
        fw_vad,
        "get_speech_timestamps",
        lambda audio, vad_options=None, sampling_rate=16000: [{"start": 8000, "end": 24000}],
    )

    processor = vad.SileroVADProcessor()
    processor.vad_model = object()  # skip the real ONNX model load in _ensure_model

    result = processor._detect_voice_activity("input.mp3", "")

    assert len(result.segments) == 1
    assert result.segments[0].start == 0.5
    assert result.segments[0].end == 1.5


# ---------------------------------------------------------------------------
# _validate_detection
# ---------------------------------------------------------------------------


def _make_processor():
    """A concrete VADProcessor subclass that bypasses the abstract method."""
    processor = vad.SileroVADProcessor()
    processor.vad_system_name = "test-model"
    return processor


def test_validate_detection_rejects_when_no_detection():
    processor = _make_processor()
    assert processor._validate_detection(None, None, "input.mp3") == "reject"


def test_validate_detection_rejects_when_no_segments():
    processor = _make_processor()
    detection = vad.DetectionResult(segments=[])
    assert processor._validate_detection(detection, None, "input.mp3") == "reject"


def test_validate_detection_returns_first_start_and_last_end():
    processor = _make_processor()
    detection = vad.DetectionResult(
        segments=[
            vad.Segment(start=0.5, end=1.0),
            vad.Segment(start=2.0, end=3.5),
        ]
    )
    # game_line=None means the short-audio and end-fix branches are skipped.
    result = processor._validate_detection(detection, None, "input.mp3")
    assert result == (0.5, 3.5)


def test_validate_detection_rejects_short_audio_for_long_text(monkeypatch):
    processor = _make_processor()
    monkeypatch.setattr(vad, "get_config", lambda: _make_config())
    # transcript is empty so the short-audio gate applies; long text needs more time.
    detection = vad.DetectionResult(segments=[vad.Segment(start=0.0, end=0.2)], transcript="")
    game_line = _FakeGameLine(text="あ" * 20, next_line=None)
    result = processor._validate_detection(detection, game_line, "input.mp3")
    assert result == "reject"


def test_validate_detection_accepts_sufficient_audio_for_text(monkeypatch):
    processor = _make_processor()
    monkeypatch.setattr(vad, "get_config", lambda: _make_config())
    # 2.0s of audio comfortably exceeds the expected minimum for 3 chars.
    detection = vad.DetectionResult(segments=[vad.Segment(start=0.0, end=2.0)], transcript="")
    game_line = _FakeGameLine(text="あいう", next_line=None)
    result = processor._validate_detection(detection, game_line, "input.mp3")
    assert result == (0.0, 2.0)


def test_validate_detection_skips_short_gate_when_transcript_present(monkeypatch):
    processor = _make_processor()
    monkeypatch.setattr(vad, "get_config", lambda: _make_config())
    # A non-empty transcript disables the short-audio gate even for a tiny clip.
    detection = vad.DetectionResult(segments=[vad.Segment(start=0.0, end=0.05)], transcript="something")
    game_line = _FakeGameLine(text="あ" * 50, next_line=None)
    result = processor._validate_detection(detection, game_line, "input.mp3")
    assert result == (0.0, 0.05)


def test_validate_detection_fixes_end_when_last_segment_past_audio(monkeypatch):
    processor = _make_processor()
    monkeypatch.setattr(vad, "get_config", lambda: _make_config())
    # audio is only 2.0s long but the last segment starts at 5.0s -> drop it, use segment[-2].end.
    monkeypatch.setattr(vad, "get_audio_length", lambda path: 2.0)
    detection = vad.DetectionResult(
        segments=[
            vad.Segment(start=0.0, end=1.0),
            vad.Segment(start=5.0, end=6.0),
        ],
        transcript="t",
    )
    game_line = _FakeGameLine(text="", next_line=_FakeGameLine())
    result = processor._validate_detection(detection, game_line, "input.mp3")
    assert result == (0.0, 1.0)


# ---------------------------------------------------------------------------
# _render_decision
# ---------------------------------------------------------------------------


def test_render_decision_reject_returns_failed_result():
    processor = _make_processor()
    detection = vad.DetectionResult(segments=[])
    result = processor._render_decision("reject", detection, "in.mp3", "out.mp3")
    assert isinstance(result, VADResult)
    assert result.success is False
    assert result.start == 0
    assert result.end == 0
    assert result.model == "test-model"


def test_render_decision_trims_audio_and_returns_offsets(monkeypatch):
    processor = _make_processor()
    monkeypatch.setattr(
        vad,
        "get_config",
        lambda: _make_config(
            vad_overrides={"beginning_offset": 0.2, "trim_beginning": True},
            audio_overrides={"end_offset": 0.3},
        ),
    )
    calls = {}

    def fake_trim_audio(input_audio, start, end, output_audio, **kwargs):
        calls["args"] = (input_audio, start, end, output_audio)
        calls["kwargs"] = kwargs

    monkeypatch.setattr(vad.ffmpeg, "trim_audio", fake_trim_audio)

    segments = [vad.Segment(start=1.0, end=2.0)]
    detection = vad.DetectionResult(segments=segments)
    result = processor._render_decision((1.0, 2.0), detection, "in.mp3", "out.mp3")

    # ffmpeg.trim_audio is invoked with the offset-adjusted bounds.
    assert calls["args"] == ("in.mp3", 1.0 + 0.2, 2.0 + 0.3, "out.mp3")
    assert calls["kwargs"]["trim_beginning"] is True

    assert result.success is True
    assert result.start == pytest.approx(1.2)
    assert result.end == pytest.approx(2.3)
    assert result.model == "test-model"
    assert result.segments == segments
    assert result.output_audio == "out.mp3"


def test_render_decision_clamps_negative_offsets_to_zero(monkeypatch):
    processor = _make_processor()
    monkeypatch.setattr(
        vad,
        "get_config",
        lambda: _make_config(vad_overrides={"beginning_offset": -5.0}),
    )
    monkeypatch.setattr(vad.ffmpeg, "trim_audio", lambda *a, **k: None)

    detection = vad.DetectionResult(segments=[vad.Segment(start=0.0, end=1.0)])
    result = processor._render_decision((0.0, 1.0), detection, "in.mp3", "out.mp3")

    # start would be -5.0 but VADResult start/end are clamped via max(0, ...).
    assert result.start == 0
    assert result.end == pytest.approx(1.0)


def test_render_decision_uses_cut_and_splice_when_enabled(monkeypatch):
    processor = _make_processor()
    monkeypatch.setattr(
        vad,
        "get_config",
        lambda: _make_config(vad_overrides={"cut_and_splice_segments": True, "splice_padding": 0.15}),
    )
    captured = {}

    def fake_extract(self, input_audio, segments, output_audio, padding=0.1, end_padding=0.0):
        captured["input_audio"] = input_audio
        captured["segments"] = segments
        captured["output_audio"] = output_audio
        captured["padding"] = padding
        captured["end_padding"] = end_padding

    monkeypatch.setattr(vad.VADProcessor, "extract_audio_and_combine_segments", fake_extract)

    segments = [vad.Segment(start=0.0, end=1.0)]
    detection = vad.DetectionResult(segments=segments)
    result = processor._render_decision((0.0, 1.0), detection, "in.mp3", "out.mp3")

    assert captured["input_audio"] == "in.mp3"
    assert captured["segments"] == segments
    assert captured["output_audio"] == "out.mp3"
    assert captured["padding"] == pytest.approx(0.15)
    assert result.success is True


# ---------------------------------------------------------------------------
# process_audio (orchestration)
# ---------------------------------------------------------------------------


def test_process_audio_chains_detect_validate_render(monkeypatch):
    processor = _make_processor()
    detection = vad.DetectionResult(segments=[vad.Segment(start=0.0, end=1.0)])

    monkeypatch.setattr(processor, "_detect_voice_activity", lambda input_audio, text_mined: detection)
    monkeypatch.setattr(
        processor,
        "_validate_detection",
        lambda det, game_line, input_audio: (0.0, 1.0),
    )

    sentinel = VADResult(True, 0.0, 1.0, "test-model")

    def fake_render(decision, det, input_audio, output_audio):
        assert decision == (0.0, 1.0)
        assert det is detection
        return sentinel

    monkeypatch.setattr(processor, "_render_decision", fake_render)

    result = processor.process_audio("in.mp3", "out.mp3", None, "mined")
    assert result is sentinel


def test_process_audio_returns_failure_on_reject(monkeypatch):
    processor = _make_processor()
    detection = vad.DetectionResult(segments=[])

    monkeypatch.setattr(processor, "_detect_voice_activity", lambda input_audio, text_mined: detection)
    monkeypatch.setattr(vad, "get_config", lambda: _make_config())

    result = processor.process_audio("in.mp3", "out.mp3", None, "mined")
    assert result.success is False
    assert result.model == "test-model"


# ---------------------------------------------------------------------------
# extract_audio_and_combine_segments (segment combination math)
# ---------------------------------------------------------------------------


def _patch_extract_boundaries(monkeypatch, tmp_path):
    """Patch the ffmpeg/thread/temp-file boundaries so the combination math runs in-process.

    Returns a list that records (start, end) passed to ffmpeg.trim_audio for each emitted segment.
    """
    trim_calls = []
    counter = {"n": 0}

    def fake_create_temp(extension):
        counter["n"] += 1
        path = tmp_path / f"seg_{counter['n']}{extension}"
        return str(path)

    def fake_trim_audio(input_audio, start, end, output_audio, trim_beginning=False):
        trim_calls.append((start, end))
        # Produce a non-empty file so it passes the valid-file filter.
        with open(output_audio, "wb") as handle:
            handle.write(b"x")

    def fake_run_new_thread(func):
        func()  # run synchronously
        return SimpleNamespace(join=lambda: None)

    monkeypatch.setattr(vad.VADProcessor, "_create_temp_audio_path", staticmethod(fake_create_temp))
    monkeypatch.setattr(vad.ffmpeg, "trim_audio", fake_trim_audio)
    monkeypatch.setattr(vad, "run_new_thread", fake_run_new_thread)
    monkeypatch.setattr(vad, "get_config", lambda: _make_config())
    return trim_calls


def test_extract_segments_single_segment_moved_to_output(monkeypatch, tmp_path):
    trim_calls = _patch_extract_boundaries(monkeypatch, tmp_path)
    moved = {}
    monkeypatch.setattr(vad.shutil, "move", lambda src, dst: moved.update(src=src, dst=dst))

    segments = [vad.Segment(start=1.0, end=2.0)]
    output = str(tmp_path / "out.opus")
    vad.VADProcessor.extract_audio_and_combine_segments("in.mp3", segments, output, padding=0.1)

    # One segment emitted; start = max(0, 1.0 - 2*padding), end = 2.0 + padding/2.
    assert len(trim_calls) == 1
    start, end = trim_calls[0]
    assert start == pytest.approx(0.8)
    assert end == pytest.approx(2.05)
    # A single valid file is moved (not combined) to the output.
    assert moved["dst"] == output


def test_extract_segments_clamps_negative_start_to_zero(monkeypatch, tmp_path):
    trim_calls = _patch_extract_boundaries(monkeypatch, tmp_path)
    monkeypatch.setattr(vad.shutil, "move", lambda src, dst: None)

    segments = [vad.Segment(start=0.05, end=1.0)]
    vad.VADProcessor.extract_audio_and_combine_segments("in.mp3", segments, str(tmp_path / "out.opus"), padding=0.1)

    start, _end = trim_calls[0]
    # 0.05 - 0.2 = -0.15 -> clamped to 0.
    assert start == 0


def test_extract_segments_merges_segments_within_padding(monkeypatch, tmp_path):
    trim_calls = _patch_extract_boundaries(monkeypatch, tmp_path)
    combined = {}
    monkeypatch.setattr(
        vad.ffmpeg,
        "combine_audio_files",
        lambda files, output: combined.update(files=list(files), output=output),
    )

    # gap between seg0.end(1.0) and seg1.start(1.1) is 0.1 < padding*2+padding/2 = 0.25 -> merge.
    segments = [
        vad.Segment(start=0.5, end=1.0),
        vad.Segment(start=1.1, end=2.0),
    ]
    output = str(tmp_path / "out.opus")
    vad.VADProcessor.extract_audio_and_combine_segments("in.mp3", segments, output, padding=0.1)

    # Merged into a single emitted segment spanning the first start to the last end.
    assert len(trim_calls) == 1
    start, end = trim_calls[0]
    assert start == pytest.approx(0.3)  # 0.5 - 0.2
    assert end == pytest.approx(2.05)  # 2.0 + 0.05
    # Single file -> moved, not combined.
    assert "files" not in combined


def test_extract_segments_combines_distinct_segments(monkeypatch, tmp_path):
    trim_calls = _patch_extract_boundaries(monkeypatch, tmp_path)
    combined = {}
    monkeypatch.setattr(
        vad.ffmpeg,
        "combine_audio_files",
        lambda files, output: combined.update(files=list(files), output=output),
    )

    # gap between 1.0 and 3.0 is 2.0 >> 0.25 -> two distinct segments, combined.
    segments = [
        vad.Segment(start=0.5, end=1.0),
        vad.Segment(start=3.0, end=4.0),
    ]
    output = str(tmp_path / "out.opus")
    vad.VADProcessor.extract_audio_and_combine_segments("in.mp3", segments, output, padding=0.1)

    assert len(trim_calls) == 2
    assert combined["output"] == output
    assert len(combined["files"]) == 2


def test_extract_segments_raises_when_no_valid_files(monkeypatch, tmp_path):
    counter = {"n": 0}

    def fake_create_temp(extension):
        counter["n"] += 1
        return str(tmp_path / f"seg_{counter['n']}{extension}")

    # trim_audio writes nothing, so no valid (non-empty) files exist.
    monkeypatch.setattr(vad.VADProcessor, "_create_temp_audio_path", staticmethod(fake_create_temp))
    monkeypatch.setattr(vad.ffmpeg, "trim_audio", lambda *a, **k: None)
    monkeypatch.setattr(vad, "run_new_thread", lambda func: (func(), SimpleNamespace(join=lambda: None))[1])
    monkeypatch.setattr(vad, "get_config", lambda: _make_config())

    segments = [vad.Segment(start=0.0, end=1.0)]
    with pytest.raises(RuntimeError, match="no valid segment files"):
        vad.VADProcessor.extract_audio_and_combine_segments("in.mp3", segments, str(tmp_path / "out.opus"), padding=0.1)
