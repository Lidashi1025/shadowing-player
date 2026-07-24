from __future__ import annotations

import locale
import logging
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

from shadowing_player.runtime.libmpv_loader import configure_libmpv_path
from shadowing_player.runtime.bundle_paths import (
    bundled_binary_dir,
    bundled_model_dir,
    is_frozen,
)
from shadowing_player.runtime.package_self_test import verify_frozen_bundle
from shadowing_player.runtime.app_identity import (
    apply_application_identity,
    set_windows_app_user_model_id,
)


def _smoke_test_requested(arguments: list[str]) -> bool:
    return "--smoke-test" in arguments


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    locale.setlocale(locale.LC_NUMERIC, "C")
    set_windows_app_user_model_id()
    application = QApplication.instance() or QApplication(sys.argv)
    icon_path = apply_application_identity(application)
    logging.getLogger(__name__).info("应用图标：%s", icon_path)

    try:
        dll_path = configure_libmpv_path()
        logging.getLogger(__name__).info("libmpv：%s", dll_path)
        from shadowing_player.ui.main_window import MainWindow

        if _smoke_test_requested(sys.argv) and is_frozen():
            verify_frozen_bundle(bundled_model_dir(), bundled_binary_dir())
        window = MainWindow()
        window.setWindowIcon(application.windowIcon())
    except Exception as exc:
        logging.getLogger(__name__).exception("播放器启动失败")
        QMessageBox.critical(None, "播放器启动失败", str(exc))
        return 1

    window.show()
    if _smoke_test_requested(sys.argv):
        QTimer.singleShot(800, window.close)
        QTimer.singleShot(1_200, application.quit)
    return application.exec()
