from __future__ import annotations


COLORS = {
    "background": "#101419",
    "surface": "#151B21",
    "surface_raised": "#1B232B",
    "surface_hover": "#232D36",
    "accent_surface": "#203D57",
    "border": "#2B3540",
    "border_strong": "#3A4652",
    "text": "#EDF3F7",
    "text_muted": "#9AA7B2",
    "text_subtle": "#6D7A84",
    "accent": "#66A8E4",
    "accent_strong": "#8CC4F2",
    "favorite": "#E6A84C",
    "success": "#55B88A",
    "danger": "#E37B7B",
}


DARK_STYLESHEET = """
#mainWindow {
    background: #101419;
    color: #EDF3F7;
}
QWidget {
    color: #EDF3F7;
    font-family: "Segoe UI", "Microsoft YaHei UI", "Microsoft YaHei", sans-serif;
    font-size: 13px;
}
QToolTip {
    background: #232D36;
    color: #EDF3F7;
    border: 1px solid #3A4652;
    padding: 5px 8px;
}
#topBar, #controlBar, #persistentActionDock, #statusBar {
    background: #151B21;
}
#topBar {
    border-bottom: 1px solid #2B3540;
}
#controlBar {
    border-top: 1px solid #2B3540;
}
#persistentActionDock {
    background: #151B21;
    border-top: 1px solid #2B3540;
}
#primaryActionRow {
    background: transparent;
}
#settingsActionRow {
    background: #12181E;
    border: 1px solid #222B33;
    border-radius: 9px;
}
#statusBar {
    border-top: 1px solid #222B33;
}
#transcriptionStatus {
    background: #18242E;
    border-top: 1px solid #2B4E6B;
}
#transcriptionLabel {
    color: #CFE5F7;
    font-weight: 600;
}
#transcriptionCancel {
    min-height: 28px;
    padding: 0 9px;
}
#transcriptionProgress {
    min-height: 12px;
    max-height: 12px;
}
#playerPanel {
    background: #101419;
    border-right: 1px solid #2B3540;
}
#sentencePanel, #subtitleStage {
    background: #151B21;
}
#sentenceHeader {
    background: #151B21;
    border-bottom: 1px solid #2B3540;
}
#sentenceFooter {
    background: #151B21;
    border-top: 1px solid #2B3540;
}
#fileLabel {
    color: #EDF3F7;
    font-size: 15px;
    font-weight: 650;
}
#metaLabel, #sentenceHint, #statusLabel {
    color: #9AA7B2;
}
#playbackMetaLabel {
    color: #7F8E99;
    font-size: 11px;
}
#sentenceTitle {
    color: #EDF3F7;
    font-size: 16px;
    font-weight: 700;
}
#subtitleLabel {
    color: #EDF3F7;
    font-size: 23px;
    font-weight: 650;
    padding: 2px 8px;
}
#promptLabel {
    color: #55B88A;
    font-size: 15px;
    font-weight: 700;
}
#videoWidget {
    background: #0A0D10;
}
QPushButton {
    min-height: 34px;
    padding: 0 13px;
    background: #1B232B;
    color: #DCE6ED;
    border: 1px solid #3A4652;
    border-radius: 9px;
}
QPushButton:hover {
    background: #232D36;
    border-color: #536272;
}
QPushButton:pressed {
    background: #101419;
}
QPushButton:disabled {
    color: #6D7A84;
    background: #151B21;
    border-color: #2B3540;
}
#openButton {
    color: #101419;
    background: #66A8E4;
    border-color: #66A8E4;
    font-weight: 700;
}
#openButton:hover {
    background: #8CC4F2;
    border-color: #8CC4F2;
}
#toolsButton, #recentButton {
    min-width: 58px;
}
QMenu {
    color: #EDF3F7;
    background: #1B232B;
    border: 1px solid #3A4652;
    padding: 5px;
}
QMenu::item {
    min-width: 170px;
    padding: 8px 18px;
    border-radius: 6px;
}
QMenu::item:selected {
    background: #203D57;
}
#primaryPlayButton {
    min-width: 72px;
    min-height: 44px;
    color: #101419;
    background: #66A8E4;
    border: 1px solid #66A8E4;
    font-size: 14px;
    font-weight: 750;
}
#primaryPlayButton:hover {
    background: #8CC4F2;
    border-color: #8CC4F2;
}
QPushButton[dockAction="true"] {
    min-height: 36px;
    padding: 0 8px;
}
QPushButton[actionState="true"][active="true"] {
    color: #CFE8FA;
    background: #203D57;
    border-color: #4A83B5;
}
QPushButton[actionState="true"][active="true"]:hover {
    background: #294D6D;
    border-color: #66A8E4;
}
#favoriteAction[active="true"] {
    color: #F4C56E;
    background: #332A1D;
    border-color: #765A2E;
}
#favoriteAction[active="true"]:hover {
    background: #413421;
    border-color: #E6A84C;
}
#stepButton {
    min-width: 42px;
    max-width: 42px;
    padding: 0;
    font-size: 18px;
    font-weight: 700;
}
#transportButton {
    min-width: 36px;
    min-height: 40px;
    padding: 0;
    font-size: 17px;
}
#editorButton {
    min-height: 30px;
    padding: 0 10px;
    color: #B7C3CC;
    background: transparent;
    border-color: #2B3540;
}
#editorButton:hover {
    color: #EDF3F7;
    background: #232D36;
}
#reviewButton {
    color: #E6A84C;
    background: #1B232B;
    border-color: #5A4930;
}
QComboBox {
    min-height: 34px;
    padding: 0 18px 0 9px;
    color: #DCE6ED;
    background: #1B232B;
    border: 1px solid #3A4652;
    border-radius: 9px;
}
QComboBox:hover, QComboBox:focus {
    border-color: #66A8E4;
}
QComboBox::drop-down {
    width: 16px;
    border: none;
}
QComboBox::down-arrow {
    image: none;
    width: 0;
    height: 0;
}
QComboBox QAbstractItemView {
    color: #EDF3F7;
    background: #1B232B;
    border: 1px solid #3A4652;
    selection-color: #EDF3F7;
    selection-background-color: #203D57;
    outline: none;
    padding: 4px;
}
QCheckBox {
    min-height: 34px;
    padding: 0 11px;
    spacing: 7px;
    color: #DCE6ED;
    background: #1B232B;
    border: 1px solid #3A4652;
    border-radius: 9px;
}
QCheckBox:hover {
    border-color: #66A8E4;
}
QCheckBox::indicator {
    width: 14px;
    height: 14px;
    border: 1px solid #536272;
    border-radius: 4px;
    background: #101419;
}
QCheckBox::indicator:checked {
    background: #66A8E4;
    border-color: #66A8E4;
}
QTableView {
    color: #B7C3CC;
    background: #151B21;
    alternate-background-color: #181F26;
    border: none;
    gridline-color: #222B33;
    outline: none;
    selection-color: #EDF3F7;
    selection-background-color: #203D57;
}
QTableView::item {
    padding: 8px 7px;
    border-bottom: 1px solid #222B33;
}
QTableView::item:hover {
    background: #1D2B37;
}
QTableView::item:selected {
    color: #EDF3F7;
    background: #2A3540;
    border-bottom: 1px solid #3A4652;
}
QHeaderView::section {
    color: #9AA7B2;
    background: #151B21;
    border: none;
    border-bottom: 1px solid #2B3540;
    padding: 7px;
}
QSplitter::handle {
    background: #2B3540;
}
QScrollBar:vertical {
    width: 10px;
    margin: 0;
    background: #151B21;
}
QScrollBar::handle:vertical {
    min-height: 28px;
    margin: 2px;
    background: #3A4652;
    border-radius: 3px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QProgressDialog {
    background: #151B21;
}
QProgressBar {
    color: #EDF3F7;
    background: #101419;
    border: 1px solid #2B3540;
    border-radius: 6px;
    text-align: center;
}
QProgressBar::chunk {
    background: #66A8E4;
    border-radius: 5px;
}
#shortcutDialog {
    background: #151B21;
}
#dialogTitle {
    color: #EDF3F7;
    font-size: 20px;
    font-weight: 700;
}
#dialogDescription {
    color: #9AA7B2;
}
#shortcutCategory {
    color: #66A8E4;
    font-size: 12px;
    font-weight: 700;
    padding-top: 9px;
}
#shortcutDescription {
    color: #7F8E99;
    font-size: 11px;
}
#shortcutConflict {
    color: #F2A0A0;
    background: #2A1D20;
    border: 1px solid #6B353D;
    border-radius: 7px;
    padding: 8px 10px;
}
QKeySequenceEdit {
    min-height: 34px;
    padding: 0 9px;
    color: #EDF3F7;
    background: #101419;
    border: 1px solid #3A4652;
    border-radius: 7px;
}
QKeySequenceEdit:focus {
    border-color: #66A8E4;
}
QScrollArea, QScrollArea > QWidget > QWidget {
    background: transparent;
}
"""


def apply_dark_theme(window) -> None:
    window.setObjectName("mainWindow")
    window.setStyleSheet(DARK_STYLESHEET)
