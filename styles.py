# -*- coding: utf-8 -*-
"""Modern graphite theme shared by the application and debug tools."""

APP_BG = "#0B0D12"
PANEL_BG = "#11141B"
SURFACE_2 = "#171B24"
SURFACE_3 = "#1D222C"
HOST_BG = "#090B0F"
CELL_BG = "#101319"
CELL_BORDER = "#272C37"
HEADER_IDLE = "#12161D"
HEADER_ACTIVE = "#171C25"
BADGE_BG = "#232936"
ACCENT = "#4C8DFF"
ACCENT_HOVER = "#67A0FF"
SUCCESS = "#38B978"
DANGER = "#E45A64"
TEXT = "#F1F3F7"
TEXT_MUTED = "#9AA3B2"
TEXT_DIM = "#6F7888"
DROP_BG = "#111C30"

# 兼容旧代码中的常量名。
GOLD = TEXT_MUTED

STYLE = r"""
* {
    font-family: "Segoe UI Variable Text", "Segoe UI", sans-serif;
    font-size: 13px;
    outline: none;
}

QMainWindow,
QDialog,
QWidget#appRoot {
    background: #0B0D12;
    color: #F1F3F7;
}

QWidget {
    color: #E8EBF1;
}

QLabel {
    background: transparent;
    color: #D7DCE5;
}

/* ---------- Main application bar ---------- */

QWidget#appBar {
    background: #11141B;
    border-bottom: 1px solid #252A35;
}

QWidget#brandBlock {
    background: transparent;
}

QLabel#brandMark {
    background: #4C8DFF;
    color: #FFFFFF;
    border-radius: 8px;
    font-size: 15px;
    font-weight: 700;
}

QLabel#brandTitle {
    color: #F5F7FA;
    font-size: 15px;
    font-weight: 650;
}

QLabel#brandCaption {
    color: #7F8999;
    font-size: 11px;
}

QLabel#fieldLabel {
    color: #8F98A8;
    font-size: 12px;
}

QLabel#versionPill {
    color: #7E8796;
    background: #171B24;
    border: 1px solid #272C37;
    border-radius: 10px;
    padding: 2px 8px;
    font-size: 11px;
}

/* ---------- Status bar ---------- */

QWidget#statusBar {
    background: #0F1218;
    border-top: 1px solid #202530;
}

QLabel#statusSummary {
    color: #AAB2BF;
    font-size: 11px;
}

QLabel#statusHint {
    color: #687180;
    font-size: 11px;
}

/* ---------- Buttons ---------- */

QPushButton {
    min-height: 32px;
    padding: 0 13px;
    border: 1px solid #303642;
    border-radius: 7px;
    background: #1A1F29;
    color: #E5E9F0;
    font-weight: 500;
}

QPushButton:hover {
    background: #242A35;
    border-color: #3A4250;
}

QPushButton:pressed {
    background: #151A22;
}

QPushButton:disabled {
    color: #59616E;
    background: #141820;
    border-color: #222731;
}

QPushButton#primaryButton {
    background: #4C8DFF;
    color: #FFFFFF;
    border-color: #4C8DFF;
    font-weight: 600;
    padding: 0 16px;
}

QPushButton#primaryButton:hover {
    background: #67A0FF;
    border-color: #67A0FF;
}

QPushButton#dangerButton {
    color: #FFB7BD;
    background: #26171B;
    border-color: #4A252C;
}

QPushButton#dangerButton:hover {
    background: #351B21;
    border-color: #6B303A;
}

QPushButton#textButton {
    min-height: 30px;
    padding: 0 10px;
    background: transparent;
    border-color: transparent;
    color: #AEB6C4;
}

QPushButton#textButton:hover {
    background: #1A1F29;
    color: #F0F3F8;
}

QToolButton {
    width: 32px;
    height: 32px;
    border: 1px solid transparent;
    border-radius: 7px;
    background: transparent;
    color: #AAB3C2;
}

QToolButton:hover {
    background: #1D222C;
    border-color: #2D3440;
    color: #F1F3F7;
}

QToolButton:pressed {
    background: #151A21;
}

QToolButton#cellMenuButton {
    width: 28px;
    height: 28px;
    border-radius: 6px;
}

/* ---------- Inputs ---------- */

QComboBox,
QSpinBox,
QLineEdit {
    min-height: 32px;
    background: #0E1117;
    color: #E7EAF0;
    border: 1px solid #303642;
    border-radius: 7px;
    padding: 0 10px;
    selection-background-color: #4C8DFF;
}

QComboBox:hover,
QSpinBox:hover,
QLineEdit:hover {
    border-color: #465061;
}

QComboBox:focus,
QSpinBox:focus,
QLineEdit:focus {
    border-color: #4C8DFF;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox QAbstractItemView {
    background: #171B24;
    color: #E8EBF1;
    border: 1px solid #303642;
    border-radius: 7px;
    padding: 5px;
    selection-background-color: #263A5D;
    selection-color: #FFFFFF;
}

QSpinBox::up-button,
QSpinBox::down-button {
    width: 20px;
    border: none;
    background: transparent;
}

/* ---------- Checkboxes ---------- */

QCheckBox {
    spacing: 9px;
    color: #D8DCE4;
}

QCheckBox::indicator {
    width: 17px;
    height: 17px;
    border: 1px solid #3B4350;
    border-radius: 5px;
    background: #0E1117;
}

QCheckBox::indicator:hover {
    border-color: #5A6575;
}

QCheckBox::indicator:checked {
    background: #4C8DFF;
    border-color: #4C8DFF;
}

/* ---------- Workspace cells ---------- */

QFrame#embedCell {
    background: #101319;
    border: 1px solid #272C37;
    border-radius: 9px;
}

QFrame#embedCell[occupied="true"] {
    border-color: #303744;
}

QFrame#embedCell[dropActive="true"] {
    background: #111C30;
    border: 1px solid #4C8DFF;
}

QWidget#dragHeader {
    background: #12161D;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    border-bottom: 1px solid #222833;
}

QWidget#dragHeader[active="true"] {
    background: #171C25;
}

QLabel#windowBadge {
    background: #232936;
    color: #AEB7C6;
    border-radius: 8px;
    font-size: 10px;
    font-weight: 650;
}

QLabel#windowGlyph {
    color: #7F8998;
}

QLabel#windowTitle {
    color: #DCE1E9;
    font-weight: 550;
}

QLabel#windowState {
    color: #38B978;
    font-size: 9px;
}

QWidget#emptyState {
    background: #0D1015;
    border: 1px dashed #2A303B;
    border-radius: 7px;
}

QLabel#emptyIcon {
    color: #657084;
    font-size: 25px;
}

QLabel#emptyTitle {
    color: #B6BECA;
    font-size: 13px;
    font-weight: 600;
}

QLabel#emptyHint {
    color: #697383;
    font-size: 11px;
}

/* ---------- Splitters ---------- */

QSplitter::handle {
    background: #141820;
}

QSplitter::handle:hover {
    background: #4C8DFF;
}

QSplitter::handle:horizontal {
    width: 7px;
    margin: 6px 2px;
    border-radius: 2px;
}

QSplitter::handle:vertical {
    height: 7px;
    margin: 2px 6px;
    border-radius: 2px;
}

QSplitter::handle:disabled {
    background: #11141A;
}

/* ---------- Settings ---------- */

QDialog#settingsDialog {
    background: #0B0D12;
}

QFrame#settingsSidebar {
    background: #101319;
    border-right: 1px solid #252A35;
}

QLabel#settingsTitle {
    color: #F4F6FA;
    font-size: 17px;
    font-weight: 650;
}

QLabel#settingsSubtitle {
    color: #737D8C;
    font-size: 11px;
}

QListWidget#settingsNav {
    background: transparent;
    border: none;
    padding: 0;
}

QListWidget#settingsNav::item {
    min-height: 38px;
    padding: 0 12px;
    margin: 2px 0;
    border-radius: 7px;
    color: #929CAB;
}

QListWidget#settingsNav::item:hover {
    background: #171C24;
    color: #D8DDE5;
}

QListWidget#settingsNav::item:selected {
    background: #1D2A40;
    color: #EAF1FF;
}

QFrame#settingsContent {
    background: #0B0D12;
}

QLabel#pageTitle {
    color: #F3F5F8;
    font-size: 20px;
    font-weight: 650;
}

QLabel#pageDescription {
    color: #818B9A;
    font-size: 12px;
}

QFrame#settingsCard {
    background: #11141B;
    border: 1px solid #272C37;
    border-radius: 9px;
}

QLabel#cardTitle {
    color: #E9ECF2;
    font-size: 14px;
    font-weight: 600;
}

QLabel#cardDescription {
    color: #778190;
    font-size: 11px;
}

QFrame#windowRow {
    background: #141820;
    border: 1px solid #282E39;
    border-radius: 8px;
}

QFrame#windowRow:hover {
    border-color: #353D49;
    background: #171C24;
}

QLabel#aboutMark {
    background: #4C8DFF;
    color: #FFFFFF;
    border-radius: 12px;
    font-size: 21px;
    font-weight: 700;
}

/* ---------- Menus and dialogs ---------- */

QMenu {
    background: #171B24;
    color: #E6E9EF;
    border: 1px solid #303642;
    border-radius: 8px;
    padding: 5px;
}

QMenu::item {
    min-height: 30px;
    padding: 0 28px 0 10px;
    border-radius: 5px;
}

QMenu::item:selected {
    background: #26334A;
    color: #FFFFFF;
}

QMenu::separator {
    height: 1px;
    background: #2A303B;
    margin: 5px 7px;
}

QToolTip {
    background: #1C212A;
    color: #E7EAF0;
    border: 1px solid #343C48;
    border-radius: 5px;
    padding: 5px 7px;
}

QMessageBox {
    background: #11141B;
}

QPlainTextEdit {
    background: #0E1117;
    color: #D5DAE3;
    border: 1px solid #2A303B;
    border-radius: 7px;
    font-family: "Cascadia Mono", "Consolas", monospace;
}

/* ---------- Scrollbars ---------- */

QScrollBar:vertical {
    background: transparent;
    width: 12px;
    margin: 0;
}

QScrollBar:horizontal {
    background: transparent;
    height: 12px;
    margin: 0;
}

QScrollBar::handle:vertical,
QScrollBar::handle:horizontal {
    background: #3A414D;
    border: 3px solid transparent;
    border-radius: 6px;
    background-clip: padding;
    min-height: 28px;
    min-width: 28px;
}

QScrollBar::handle:vertical:hover,
QScrollBar::handle:horizontal:hover {
    background: #596272;
    border: 3px solid transparent;
    background-clip: padding;
}

QScrollBar::add-line,
QScrollBar::sub-line,
QScrollBar::add-page,
QScrollBar::sub-page {
    width: 0;
    height: 0;
    background: transparent;
    border: none;
}
"""
