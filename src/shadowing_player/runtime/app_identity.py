from __future__ import annotations

import ctypes
import sys
from pathlib import Path

from PySide6.QtGui import QIcon

from shadowing_player.runtime.bundle_paths import (
    bundle_internal_dir,
    is_frozen,
    project_root,
)


APPLICATION_NAME = "ShadowingPlayer"
APPLICATION_DISPLAY_NAME = "儿童影子跟读播放器"
WINDOWS_APP_USER_MODEL_ID = "ShadowingPlayer.Desktop"


def set_windows_app_user_model_id() -> bool:
    if sys.platform != "win32":
        return False
    try:
        result = ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            WINDOWS_APP_USER_MODEL_ID
        )
    except (AttributeError, OSError):
        return False
    return result == 0


def application_icon_path() -> Path:
    base_dir = bundle_internal_dir() if is_frozen() else project_root()
    return base_dir / "assets" / "app-icon.ico"


def apply_application_identity(application) -> Path:
    icon_path = application_icon_path()
    if not icon_path.is_file():
        raise FileNotFoundError(f"找不到应用图标：{icon_path}")
    application.setApplicationName(APPLICATION_NAME)
    application.setApplicationDisplayName(APPLICATION_DISPLAY_NAME)
    application.setOrganizationName(APPLICATION_NAME)
    application.setWindowIcon(QIcon(str(icon_path)))
    return icon_path
