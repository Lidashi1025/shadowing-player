from __future__ import annotations

from collections.abc import Callable
from pathlib import Path


class ModelDownloadError(RuntimeError):
    pass


Downloader = Callable[..., str]


def _default_downloader(size: str, output_dir: str) -> str:
    try:
        from faster_whisper.utils import download_model
    except ImportError as exc:
        raise ModelDownloadError(
            "缺少 faster-whisper。请先执行：python -m pip install faster-whisper"
        ) from exc
    return str(download_model(size, output_dir=output_dir))


class ModelManager:
    def __init__(self, model_dir: Path, downloader: Downloader | None = None) -> None:
        self.model_dir = model_dir
        self._downloader = downloader or _default_downloader

    def is_available(self) -> bool:
        return (self.model_dir / "model.bin").is_file() and (
            self.model_dir / "config.json"
        ).is_file()

    def ensure_model(self) -> Path:
        if self.is_available():
            return self.model_dir
        self.model_dir.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._downloader("small", output_dir=str(self.model_dir))
        except Exception as exc:
            command = (
                "python -c \"from faster_whisper.utils import download_model; "
                f"download_model('small', output_dir=r'{self.model_dir}')\""
            )
            raise ModelDownloadError(
                "语音模型下载失败。\n"
                f"请检查网络，或手动放到：{self.model_dir}\n"
                f"手动下载命令：{command}"
            ) from exc
        if not self.is_available():
            raise ModelDownloadError(
                f"下载完成但模型文件不完整，请删除后重试：{self.model_dir}"
            )
        return self.model_dir
