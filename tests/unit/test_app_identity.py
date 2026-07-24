from pathlib import Path

from shadowing_player.runtime import app_identity


def test_application_icon_path_uses_source_assets(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(app_identity, "is_frozen", lambda: False)
    monkeypatch.setattr(app_identity, "project_root", lambda: tmp_path)

    assert app_identity.application_icon_path() == tmp_path / "assets" / "app-icon.ico"


def test_application_icon_path_uses_frozen_internal_assets(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(app_identity, "is_frozen", lambda: True)
    monkeypatch.setattr(app_identity, "bundle_internal_dir", lambda: tmp_path)

    assert app_identity.application_icon_path() == tmp_path / "assets" / "app-icon.ico"


def test_windows_taskbar_identity_is_set_explicitly(monkeypatch) -> None:
    calls: list[str] = []

    class FakeShell:
        def SetCurrentProcessExplicitAppUserModelID(self, value: str) -> int:
            calls.append(value)
            return 0

    monkeypatch.setattr(app_identity.sys, "platform", "win32")
    monkeypatch.setattr(
        app_identity.ctypes,
        "windll",
        type("FakeWindll", (), {"shell32": FakeShell()})(),
        raising=False,
    )

    assert app_identity.set_windows_app_user_model_id() is True
    assert calls == ["ShadowingPlayer.Desktop"]


def test_apply_application_identity_sets_names_and_runtime_icon(
    monkeypatch, tmp_path: Path
) -> None:
    icon_path = tmp_path / "app-icon.ico"
    icon_path.touch()
    monkeypatch.setattr(app_identity, "application_icon_path", lambda: icon_path)
    monkeypatch.setattr(app_identity, "QIcon", lambda value: ("icon", value))

    class FakeApplication:
        def __init__(self) -> None:
            self.name = ""
            self.display_name = ""
            self.organization = ""
            self.icon = None

        def setApplicationName(self, value: str) -> None:
            self.name = value

        def setApplicationDisplayName(self, value: str) -> None:
            self.display_name = value

        def setOrganizationName(self, value: str) -> None:
            self.organization = value

        def setWindowIcon(self, value) -> None:
            self.icon = value

    application = FakeApplication()
    result = app_identity.apply_application_identity(application)

    assert result == icon_path
    assert application.name == "ShadowingPlayer"
    assert application.display_name == "儿童影子跟读播放器"
    assert application.organization == "ShadowingPlayer"
    assert application.icon == ("icon", str(icon_path))
