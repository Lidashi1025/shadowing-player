from __future__ import annotations

import wave
from pathlib import Path

from PySide6.QtCore import QIODevice, QObject, QTimer, Signal
from PySide6.QtMultimedia import QAudioFormat, QAudioSource, QMediaDevices


class SentenceRecorder(QObject):
    """Record mono PCM from the default microphone into a WAV file."""

    started = Signal()
    stopped = Signal(object)  # Path
    failed = Signal(str)

    SAMPLE_RATE = 16_000
    CHANNELS = 1
    SAMPLE_WIDTH = 2  # int16

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._source: QAudioSource | None = None
        self._device = None
        self._path: Path | None = None
        self._buffer = bytearray()
        self._timer: QTimer | None = None
        self._max_ms = 15_000

    @property
    def is_recording(self) -> bool:
        return self._source is not None

    def start(self, path: Path, max_ms: int = 15_000) -> None:
        if self._source is not None:
            self.stop()
        device = QMediaDevices.defaultAudioInput()
        if device.isNull():
            self.failed.emit("未找到麦克风，请在系统设置中允许录音设备。")
            return
        audio_format = QAudioFormat()
        audio_format.setSampleRate(self.SAMPLE_RATE)
        audio_format.setChannelCount(self.CHANNELS)
        audio_format.setSampleFormat(QAudioFormat.SampleFormat.Int16)
        if not device.isFormatSupported(audio_format):
            audio_format = device.preferredFormat()
        try:
            source = QAudioSource(device, audio_format, self)
            io = source.start()
        except Exception as exc:  # pragma: no cover - depends on OS audio stack
            self.failed.emit(f"无法启动录音：{exc}")
            return
        if io is None:
            self.failed.emit("无法打开麦克风输入流。")
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        self._path = path
        self._buffer = bytearray()
        self._source = source
        self._device = io
        self._max_ms = max(1_000, int(max_ms))
        io.readyRead.connect(self._on_ready_read)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.stop)
        self._timer.start(self._max_ms)
        self.started.emit()

    def stop(self) -> None:
        if self._source is None or self._path is None:
            return
        path = self._path
        if self._timer is not None:
            self._timer.stop()
            self._timer.deleteLater()
            self._timer = None
        source = self._source
        device = self._device
        self._source = None
        self._device = None
        self._path = None
        try:
            if device is not None:
                remaining = device.readAll()
                if remaining:
                    self._buffer.extend(bytes(remaining))
            source.stop()
            source.deleteLater()
        except Exception:
            pass
        try:
            self._write_wav(path, bytes(self._buffer), source_format=source)
        except Exception as exc:
            self.failed.emit(f"保存录音失败：{exc}")
            return
        self.stopped.emit(path)

    def _on_ready_read(self) -> None:
        if self._device is None:
            return
        data = self._device.readAll()
        if data:
            self._buffer.extend(bytes(data))

    def _write_wav(self, path: Path, pcm: bytes, source_format=None) -> None:
        sample_rate = self.SAMPLE_RATE
        channels = self.CHANNELS
        sample_width = self.SAMPLE_WIDTH
        if source_format is not None:
            try:
                fmt = source_format.format()
                sample_rate = int(fmt.sampleRate()) or sample_rate
                channels = int(fmt.channelCount()) or channels
                # Int16 → 2 bytes
                sample_width = 2
            except Exception:
                pass
        with wave.open(str(path), "wb") as handle:
            handle.setnchannels(channels)
            handle.setsampwidth(sample_width)
            handle.setframerate(sample_rate)
            handle.writeframes(pcm)


class WavPlayer(QObject):
    """Play a short WAV file via QAudioSink (no extra dependencies)."""

    finished = Signal()
    failed = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._sink = None
        self._buffer = None
        self._io = None

    def play(self, path: Path) -> None:
        self.stop()
        try:
            with wave.open(str(path), "rb") as handle:
                channels = handle.getnchannels()
                sample_width = handle.getsampwidth()
                sample_rate = handle.getframerate()
                frames = handle.readframes(handle.getnframes())
        except Exception as exc:
            self.failed.emit(f"无法读取录音：{exc}")
            return
        if sample_width != 2:
            self.failed.emit("仅支持 16-bit PCM 录音回放。")
            return
        from PySide6.QtMultimedia import QAudioFormat, QAudioSink, QMediaDevices
        from PySide6.QtCore import QBuffer, QByteArray

        fmt = QAudioFormat()
        fmt.setSampleRate(sample_rate)
        fmt.setChannelCount(channels)
        fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)
        device = QMediaDevices.defaultAudioOutput()
        if device.isNull():
            self.failed.emit("未找到扬声器/耳机输出设备。")
            return
        try:
            sink = QAudioSink(device, fmt, self)
            data = QByteArray(frames)
            buffer = QBuffer(data, self)
            buffer.open(QIODevice.OpenModeFlag.ReadOnly)
            sink.start(buffer)
        except Exception as exc:
            self.failed.emit(f"无法播放录音：{exc}")
            return
        self._sink = sink
        self._buffer = buffer
        # Approximate finish timer
        duration_ms = max(200, int(len(frames) / (sample_rate * channels * sample_width) * 1000))
        QTimer.singleShot(duration_ms + 50, self._on_finished)

    def stop(self) -> None:
        if self._sink is not None:
            try:
                self._sink.stop()
                self._sink.deleteLater()
            except Exception:
                pass
        self._sink = None
        self._buffer = None
        self._io = None

    def _on_finished(self) -> None:
        self.stop()
        self.finished.emit()


def recording_path_for(
    data_dir: Path,
    video_path: Path | None,
    start_ms: int,
    end_ms: int,
) -> Path:
    stem = "unknown"
    if video_path is not None:
        stem = video_path.stem[:40]
    name = f"{stem}_{start_ms}_{end_ms}.wav"
    safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in name)
    return data_dir / "recordings" / safe
