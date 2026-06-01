"""
First GUI — PySide6 版
Author: Spade-sec | https://github.com/Spade-sec/First
"""
import asyncio
import json
import multiprocessing
import os
import queue
import subprocess
import sys
import threading

from PySide6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, Property, QRect,
    Signal, QPoint, QUrl,
)
from PySide6.QtGui import QPainter, QColor, QFont, QIcon, QPixmap, QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QFrame, QPushButton, QScrollArea, QTextEdit,
    QTreeWidget, QTreeWidgetItem, QProgressBar, QStackedWidget,
    QMenu, QHeaderView, QAbstractItemView, QFileDialog, QInputDialog,
    QTabWidget, QTableWidget, QTableWidgetItem, QDialog, QSizePolicy,
    QCheckBox,
)

from src.cli import CliOptions, CDP_PORT
from src.logger import Logger
from src.engine import DebugEngine
from src.navigator import MiniProgramNavigator
from src.cloud_audit import CloudAuditor
from src.wxapi_audit import WxApiAuditor

# ══════════════════════════════════════════
#  配色
# ══════════════════════════════════════════
_D = dict(
    bg="#1c1c24",       card="#262632",     input="#181820",
    sidebar="#111118",  sb_hover="#1c1c28", sb_active="#222232",
    border="#303040",   border2="#3a3a4c",
    text1="#e8e8f0",    text2="#8888a0",    text3="#5c5c6c",   text4="#3c3c4c",
    accent="#4ade80",   accent2="#22c55e",
    success="#4ade80",  error="#f87171",    warning="#fbbf24",
)
_L = dict(
    bg="#f2f2f6",       card="#ffffff",     input="#eeeef2",
    sidebar="#ffffff",  sb_hover="#f2f2f6", sb_active="#e6e6ea",
    border="#d8d8dc",   border2="#c8c8cc",
    text1="#1a1a22",    text2="#6e6e78",    text3="#9e9ea8",   text4="#c0c0c8",
    accent="#16a34a",   accent2="#15803d",
    success="#16a34a",  error="#dc2626",    warning="#ca8a04",
)
_TH = {"dark": _D, "light": _L}
# Platform-aware default fonts (overridable via gui_config.json: font_ui / font_mono)
if sys.platform == "darwin":
    _FN = "PingFang SC"
    _FM = "Menlo"
else:
    _FN = "Microsoft YaHei UI"
    _FM = "Consolas"
_MENU = [
    ("control",   "◉", "控制台"),
    ("navigator", "⬡", "路由导航"),
    ("hook",      "◈", "Hook"),
    ("targets",   "◎", "服务目标"),
    ("cloud",     "☁", "云扫描"),
    ("wxapi",     "⬢", "WxAPI捕获"),
    ("extract",   "◆", "敏感信息提取"),
    ("vconsole",  "◇", "调试开关"),
    ("logs",      "≡", "运行日志"),
]

# ══════════════════════════════════════════
#  配置持久化
# ══════════════════════════════════════════
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if getattr(sys, 'frozen', False):
    _BASE_DIR = os.path.dirname(sys.executable)
_CFG_FILE = os.path.join(_BASE_DIR, "gui_config.json")

os.makedirs(os.path.join(_BASE_DIR, "hook_scripts"), exist_ok=True)


def _load_cfg():
    try:
        with open(_CFG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_cfg(data):
    try:
        with open(_CFG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


# Apply font overrides from config.
# Editable fields in gui_config.json:
#   font_ui        — UI font family name
#   font_ui_size   — UI base font size (int, default 9)
#   font_mono      — monospace font family name
#   font_mono_size — monospace font size (int, default 9)
_early_cfg = _load_cfg()
if _early_cfg.get("font_ui"):
    _FN = _early_cfg["font_ui"]
if _early_cfg.get("font_mono"):
    _FM = _early_cfg["font_mono"]
_FN_SIZE: int = int(_early_cfg.get("font_ui_size", 9))
_FM_SIZE: int = int(_early_cfg.get("font_mono_size", 9))

# Write defaults back so the fields appear in gui_config.json on first launch
_init_cfg = dict(_early_cfg)
_cfg_dirty = False
for _k, _v in [("font_ui", _FN), ("font_ui_size", _FN_SIZE),
                ("font_mono", _FM), ("font_mono_size", _FM_SIZE)]:
    if _k not in _init_cfg:
        _init_cfg[_k] = _v
        _cfg_dirty = True
if _cfg_dirty:
    _save_cfg(_init_cfg)
del _init_cfg, _cfg_dirty


def _qfn(offset: int = 0, weight=None):
    """Return QFont for UI font with size relative to _FN_SIZE."""
    f = QFont(_FN, max(6, _FN_SIZE + offset))
    if weight is not None:
        f.setWeight(weight)
    return f


def _qfm(offset: int = 0, weight=None):
    """Return QFont for mono font with size relative to _FM_SIZE."""
    f = QFont(_FM, max(6, _FM_SIZE + offset))
    if weight is not None:
        f.setWeight(weight)
    return f


# ══════════════════════════════════════════
#  QSS 主题
# ══════════════════════════════════════════

def build_qss(tn):
    c = _TH[tn]
    sel_bg = "#1e3a2a" if tn == "dark" else "#d4edda"
    sel_fg = "#a0f0c0" if tn == "dark" else "#155724"
    hdr_bg = "#222230" if tn == "dark" else "#e8e8ec"
    row_bg = c["input"]
    return f"""
    /* ── 全局 ── */
    QMainWindow, QWidget#central {{
        background: {c['bg']};
    }}

    /* ── 侧栏 ── */
    QFrame#sidebar {{
        background: {c['sidebar']};
    }}
    QFrame#sidebar QLabel {{
        background: transparent;
    }}
    QFrame#sb_head {{
        background: {c['sidebar']};
    }}
    QLabel#sb_logo {{
        color: {c['text1']};
        font-size: 13px; font-weight: bold;
        background: transparent;
    }}
    QFrame#sb_hline {{
        background: {c['border']};
        max-height: 1px; min-height: 1px;
    }}
    QLabel#sb_theme {{
        color: {c['text3']};
        background: transparent;
        padding: 4px 12px;
    }}
    QLabel#sb_theme:hover {{
        color: {c['text1']};
    }}

    /* ── 菜单项 ── */
    QFrame.sb_item {{
        background: {c['sidebar']};
        border-radius: 8px;
        padding: 8px 10px;
    }}
    QFrame.sb_item:hover {{
        background: {c['sb_hover']};
    }}
    QFrame.sb_item_active {{
        background: {c['sb_active']};
        border-radius: 8px;
        padding: 8px 10px;
    }}
    QFrame.sb_item QLabel.sb_icon {{
        color: {c['text3']};
        background: transparent;
    }}
    QFrame.sb_item QLabel.sb_name {{
        color: {c['text2']};
        background: transparent;
    }}
    QFrame.sb_item_active QLabel.sb_icon {{
        color: {c['accent']};
        background: transparent;
    }}
    QFrame.sb_item_active QLabel.sb_name {{
        color: {c['text1']};
        background: transparent;
    }}

    /* ── 分割线 ── */
    QFrame#vline {{
        background: {c['border']};
        max-width: 1px; min-width: 1px;
    }}
    QFrame#hdr_line {{
        background: {c['border']};
        max-height: 1px; min-height: 1px;
    }}

    /* ── 标题 ── */
    QLabel#page_title {{
        color: {c['text1']};
        font-size: 17px; font-weight: bold;
        padding-left: 24px;
        background: transparent;
    }}

    /* ── 圆角卡片 ── */
    QFrame.card {{
        background: {c['card']};
        border-radius: 12px;
        border: none;
    }}
    QFrame.card QLabel {{
        background: transparent;
    }}
    QFrame.card QLabel.title {{
        color: {c['text1']};
        font-weight: bold;
        font-size: 11px;
    }}
    QFrame.card QLabel.subtitle {{
        color: {c['text2']};
        font-size: 9px;
    }}

    /* ── 通用 Label ── */
    QLabel {{
        color: {c['text2']};
        background: transparent;
    }}
    QLabel.bold {{
        color: {c['text1']};
        font-weight: bold;
    }}
    QLabel.muted {{
        color: {c['text3']};
    }}
    QLabel.accent {{
        color: {c['accent']};
    }}

    /* ── 按钮 ── */
    QPushButton {{
        background: {c['accent']};
        color: #111118;
        border: none;
        border-radius: 8px;
        padding: 5px 16px;
        font-size: 10px;
    }}
    QPushButton:hover {{
        background: {c['accent2']};
    }}
    QPushButton:disabled {{
        background: {"#1a3a2a" if tn == "dark" else "#b0dfc0"};
        color: {"#3a6a4a" if tn == "dark" else "#5a8a6a"};
    }}
    /* 表格内按钮 — 清除全局样式，由 inline setStyleSheet 控制 */
    QTableWidget QPushButton {{
        background: transparent;
        color: {c['text2']};
        border: none;
        border-radius: 6px;
        padding: 4px 12px;
        font-size: 12px;
    }}
    QTableWidget QPushButton:hover {{
        background: transparent;
    }}

    /* ── 输入框 ── */
    QLineEdit {{
        background: {c['input']};
        color: {c['text1']};
        border: none;
        border-radius: 10px;
        padding: 6px 12px;
        font-size: 10px;
        selection-background-color: {c['accent']};
        selection-color: #111118;
    }}
    QLineEdit:focus {{
        border: 1px solid {c['accent']};
    }}

    /* ── 文本框 ── */
    QTextEdit {{
        background: {c['input']};
        color: {c['accent']};
        border: none;
        border-radius: 8px;
        padding: 10px 14px;
        font-family: {_FM};
        font-size: 10px;
        selection-background-color: {c['accent']};
        selection-color: #111118;
    }}

    /* ── 树形控件 ── */
    QTreeWidget {{
        background: {c['card']};
        color: {c['text2']};
        border: none;
        font-size: 10px;
        outline: 0;
    }}
    QTreeWidget::item {{
        padding: 4px 8px;
        border: none;
        text-align: left;
    }}
    QTreeWidget::item:selected {{
        background: {sel_bg};
        color: {sel_fg};
    }}
    QTreeWidget::item:hover {{
        background: {c['sb_hover']};
    }}
    QHeaderView::section {{
        background: {hdr_bg};
        color: {c['text1']};
        border: none;
        padding: 4px 8px;
        font-weight: bold;
        font-size: 10px;
        text-align: left;
    }}

    /* ── 进度条 ── */
    QProgressBar {{
        background: {c['border']};
        border: none;
        border-radius: 4px;
        height: 6px;
        text-align: center;
    }}
    QProgressBar::chunk {{
        background: {c['accent']};
        border-radius: 4px;
    }}

    /* ── 滚动条 ── */
    QScrollBar:vertical {{
        background: transparent;
        width: 6px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {"#3a6a4a" if tn == "dark" else "#8fc4a0"};
        border-radius: 3px;
        min-height: 20px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: transparent;
    }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 6px;
    }}
    QScrollBar::handle:horizontal {{
        background: {"#3a6a4a" if tn == "dark" else "#8fc4a0"};
        border-radius: 3px;
        min-width: 20px;
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0;
    }}
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
        background: transparent;
    }}

    /* ── 表格控件 ── */
    QTableWidget {{
        background: {c['card']};
        color: {c['text2']};
        border: none;
        font-size: 12px;
        outline: 0;
        gridline-color: {c['border']};
    }}
    QTableWidget::item {{
        padding: 6px 10px;
        border: none;
        background: {c['card']};
        color: {c['text2']};
    }}
    QTableWidget::item:selected {{
        background: {sel_bg};
        color: {sel_fg};
    }}
    QTableWidget QHeaderView::section {{
        background: {hdr_bg};
        color: {c['text1']};
        border: none;
        padding: 6px 10px;
        font-weight: bold;
        font-size: 12px;
    }}

    /* ── 滚动区域 ── */
    QScrollArea {{
        background: transparent;
        border: none;
    }}
    QScrollArea > QWidget > QWidget {{
        background: transparent;
    }}

    /* ── 右键菜单 ── */
    QMenu {{
        background: {c['card']};
        color: {c['text1']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 4px;
    }}
    QMenu::item {{
        padding: 6px 20px;
        border-radius: 4px;
    }}
    QMenu::item:selected {{
        background: {c['accent']};
        color: #ffffff;
    }}
    QMenu::separator {{
        height: 1px;
        background: {c['border']};
        margin: 4px 8px;
    }}

    /* ── QCheckBox ── */
    QCheckBox {{
        color: {c['text1']};
        background: transparent;
        spacing: 5px;
    }}
    QCheckBox::indicator {{
        width: 14px;
        height: 14px;
        border-radius: 3px;
        border: 1px solid {c['border2']};
        background: {c['input']};
    }}
    QCheckBox::indicator:checked {{
        background: {c['accent']};
        border-color: {c['accent']};
        image: none;
    }}
    QCheckBox::indicator:hover {{
        border-color: {c['accent']};
    }}

    /* ── Hook 行 ── */
    QFrame.hook_row {{
        background: {row_bg};
        border-radius: 8px;
    }}
    QFrame.hook_row QLabel {{
        background: transparent;
    }}
    QLabel.js_badge {{
        background: {c['accent']};
        color: {"#ffffff" if tn == "dark" else "#111118"};
        font-weight: bold;
        font-size: 9px;
        padding: 2px 6px;
        border-radius: 4px;
    }}

    /* ── Completer popup ── */
    QListView {{
        background: {c['input']};
        color: {c['text1']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        outline: 0;
    }}
    QListView::item:selected {{
        background: {c['accent']};
        color: #111118;
    }}
    """


# ══════════════════════════════════════════
#  自定义控件
# ══════════════════════════════════════════

class ToggleSwitch(QWidget):
    toggled = Signal(bool)

    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self._checked = checked
        self._thumb_pos = 1.0 if checked else 0.0
        self._on_color = QColor("#4ade80")
        self._off_color = QColor("#3c3c4c")
        self._thumb_color = QColor("#ffffff")
        self.setFixedSize(44, 24)
        self.setCursor(Qt.PointingHandCursor)

        self._anim = QPropertyAnimation(self, b"thumbPos")
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

    def isChecked(self):
        return self._checked

    def setChecked(self, v):
        if self._checked == v:
            return
        self._checked = v
        self._anim.stop()
        self._anim.setStartValue(self._thumb_pos)
        self._anim.setEndValue(1.0 if v else 0.0)
        self._anim.start()
        self.toggled.emit(v)

    def _get_thumb_pos(self):
        return self._thumb_pos

    def _set_thumb_pos(self, v):
        self._thumb_pos = v
        self.update()

    thumbPos = Property(float, _get_thumb_pos, _set_thumb_pos)

    def mousePressEvent(self, e):
        self.setChecked(not self._checked)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        r = h / 2

        # track
        track_color = QColor(self._on_color) if self._checked else QColor(self._off_color)
        p.setPen(Qt.NoPen)
        p.setBrush(track_color)
        p.drawRoundedRect(0, 0, w, h, r, r)

        # thumb
        tr = r - 3
        cx = r + self._thumb_pos * (w - 2 * r)
        p.setBrush(self._thumb_color)
        p.drawEllipse(QPoint(int(cx), int(r)), int(tr), int(tr))

    def set_colors(self, on, off):
        self._on_color = QColor(on)
        self._off_color = QColor(off)
        self.update()


class AnimatedStackedWidget(QStackedWidget):
    """Page switch with a lightweight vertical slide animation.

    Uses QPropertyAnimation on widget geometry instead of
    QGraphicsOpacityEffect, which forces expensive off-screen
    compositing of the entire subtree (causing visible lag on
    heavy pages like the cloud-scan QTreeWidget).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._anim = None

    def setCurrentIndexAnimated(self, idx):
        if idx == self.currentIndex():
            return
        old_idx = self.currentIndex()
        old_widget = self.currentWidget()
        new_widget = self.widget(idx)
        if new_widget is None:
            self.setCurrentIndex(idx)
            return

        # Determine slide direction: down when going forward, up when back
        h = self.height()
        offset = h // 4  # slide only a quarter of the height for subtlety
        start_y = offset if idx > old_idx else -offset

        # Immediately switch the page (no off-screen compositing)
        self.setCurrentIndex(idx)

        # Animate just the position of the new page
        final_rect = new_widget.geometry()
        start_rect = QRect(final_rect)
        start_rect.moveTop(final_rect.top() + start_y)

        anim = QPropertyAnimation(new_widget, b"geometry")
        anim.setDuration(150)
        anim.setStartValue(start_rect)
        anim.setEndValue(final_rect)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim = anim          # prevent GC
        anim.start()


class StatusDot(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(10, 10)
        self._color = QColor("#3c3c4c")

    def set_color(self, color):
        self._color = QColor(color)
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(self._color)
        p.drawEllipse(1, 1, 8, 8)


# ══════════════════════════════════════════
#  辅助函数
# ══════════════════════════════════════════

def _make_card():
    f = QFrame()
    f.setProperty("class", "card")
    return f


def _make_label(text, bold=False, muted=False, mono=False):
    l = QLabel(text)
    if bold:
        l.setProperty("class", "bold")
    elif muted:
        l.setProperty("class", "muted")
    if mono:
        l.setFont(_qfm(1))
    return l


def _make_btn(text, callback=None):
    b = QPushButton(text)
    if callback:
        b.clicked.connect(callback)
    return b


def _make_entry(placeholder="", width=None):
    e = QLineEdit()
    e.setPlaceholderText(placeholder)
    if width:
        e.setFixedWidth(width)
    return e



# ══════════════════════════════════════════
#  主窗口
# ══════════════════════════════════════════

class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self._os_tag = "macOS" if sys.platform == "darwin" else "Windows"
        self.setWindowTitle(f"First-{self._os_tag}")
        _ico = os.path.join(_BASE_DIR, "icon.png")
        if os.path.exists(_ico):
            self.setWindowIcon(QIcon(_ico))
        self.resize(1060, 660)
        self.setMinimumSize(900, 540)

        self._cfg = _load_cfg()
        self._tn = self._cfg.get("theme", "dark")
        self._pg = "control"
        self._running = False
        self._loop = self._loop_th = self._engine = self._navigator = self._auditor = None
        self._cloud_call_history = {}
        self._cloud_all_items = []
        self._cloud_row_results = {}
        self._cloud_live_items = []  # 动态捕获完整 call 对象列表
        self._wxapi_auditor = None
        self._wxapi_items = []
        self._wxapi_active = False
        self._wxapi_poll_timer = None
        self._wxapi_selected_idx = -1
        self._cancel_ev = None
        self._route_poll_id = None
        self._all_routes = []
        self._flat_routes = []  # tree visual order for prev/next
        self._cloud_scan_active = False
        self._cloud_scan_poll_timer = None
        self._redirect_guard_on = False
        self._hook_injected = set()
        self._global_hook_scripts = set(self._cfg.get("global_hook_scripts", []))
        self._global_inject_gen = 0
        self._blocked_seen = 0
        self._miniapp_connected = False
        self._sb_fetch_gen = 0
        self._vc_stable_gen = 0
        self._log_q = queue.Queue()
        self._sts_q = queue.Queue()
        self._rte_q = queue.Queue()
        self._cld_q = queue.Queue()
        self._wxapi_q = queue.Queue()
        self._tgt_q = queue.Queue()
        self._nav_route_idx = -1

        self._sb_items = {}
        self._page_map = {}

        # 敏感信息提取 状态
        self._ext_proc = None
        self._ext_thread = None
        self._ext_q = queue.Queue()
        self._ext_custom_patterns = dict(self._cfg.get("extract_custom_patterns", {}))
        self._ext_app_states = {}   # {appid: {"decompiled": bool, "scanned": bool, ...}}
        self._ext_app_widgets = {}  # {appid: row widget ref}
        self._ext_current_op = None  # ("decompile"/"scan", appid) or None

        self._build()
        self.setStyleSheet(build_qss(self._tn))
        self._show("control")

        self._tick_timer = QTimer()
        self._tick_timer.timeout.connect(self._tick)
        self._tick_timer.start(80)

    # ──────────────────────────────────
    #  布局
    # ──────────────────────────────────

    def _build(self):
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        root_h = QHBoxLayout(central)
        root_h.setContentsMargins(0, 0, 0, 0)
        root_h.setSpacing(0)

        # ── 侧栏 ──
        self._sb = QFrame()
        self._sb.setObjectName("sidebar")
        self._sb.setFixedWidth(180)
        sb_lay = QVBoxLayout(self._sb)
        sb_lay.setContentsMargins(0, 0, 0, 0)
        sb_lay.setSpacing(0)

        sb_head = QFrame()
        sb_head.setObjectName("sb_head")
        sb_head.setFixedHeight(90)
        sb_head_lay = QVBoxLayout(sb_head)
        sb_head_lay.addStretch()

        logo_row = QHBoxLayout()
        logo_row.setContentsMargins(0, 0, 0, 0)
        logo_row.setSpacing(6)
        logo_row.addStretch()
        _ico_path = os.path.join(_BASE_DIR, "icon.png")
        if os.path.exists(_ico_path):
            _ico_lbl = QLabel()
            _pix = QPixmap(_ico_path).scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            _ico_lbl.setPixmap(_pix)
            _ico_lbl.setFixedSize(20, 20)
            logo_row.addWidget(_ico_lbl)
        self._sb_logo = QLabel(f"First-{self._os_tag}")
        self._sb_logo.setObjectName("sb_logo")
        logo_row.addWidget(self._sb_logo)
        logo_row.addStretch()
        sb_head_lay.addLayout(logo_row)

        sb_head_lay.addStretch()
        sb_lay.addWidget(sb_head)

        hline = QFrame()
        hline.setObjectName("sb_hline")
        hline.setFixedHeight(1)
        sb_lay.addWidget(hline, 0, Qt.AlignTop)

        sb_nav = QWidget()
        sb_nav_lay = QVBoxLayout(sb_nav)
        sb_nav_lay.setContentsMargins(8, 10, 8, 10)
        sb_nav_lay.setSpacing(2)
        for pid, icon, name in _MENU:
            row = QFrame()
            row.setCursor(Qt.PointingHandCursor)
            row.setProperty("class", "sb_item")
            row_lay = QHBoxLayout(row)
            row_lay.setContentsMargins(10, 0, 8, 0)
            row_lay.setSpacing(6)
            ic = QLabel(icon)
            ic.setProperty("class", "sb_icon")
            ic.setFont(_qfn(4))
            nm = QLabel(name)
            nm.setProperty("class", "sb_name")
            nm.setFont(_qfn(1))
            row_lay.addWidget(ic)
            row_lay.addWidget(nm, 1)
            sb_nav_lay.addWidget(row)
            row.mousePressEvent = lambda e, p=pid: self._show(p)
            self._sb_items[pid] = (row, ic, nm)
        sb_nav_lay.addStretch()
        sb_lay.addWidget(sb_nav, 1)

        # 侧栏小程序信息卡片
        sb_app_card = QFrame()
        sb_app_card.setStyleSheet(
            "QFrame { background: rgba(128,128,128,0.08); border-radius: 8px; }"
            "QLabel { background: transparent; }")
        sb_app_card_lay = QVBoxLayout(sb_app_card)
        sb_app_card_lay.setContentsMargins(8, 6, 8, 6)
        sb_app_card_lay.setSpacing(1)
        self._sb_app_name = QLabel("未连接")
        self._sb_app_name.setAlignment(Qt.AlignCenter)
        self._sb_app_name.setFont(_qfn(-1))
        self._sb_app_name.setStyleSheet("color: #5c5c6c;")
        self._sb_app_name.setWordWrap(True)
        sb_app_card_lay.addWidget(self._sb_app_name)
        self._sb_app_id = QLabel("")
        self._sb_app_id.setAlignment(Qt.AlignCenter)
        self._sb_app_id.setFont(_qfn(-1))
        self._sb_app_id.setStyleSheet("color: #9e9ea8;")
        self._sb_app_id.setVisible(False)
        self._sb_app_id.setWordWrap(True)
        sb_app_card_lay.addWidget(self._sb_app_id)
        sb_lay.addWidget(sb_app_card)
        sb_lay.addSpacing(4)

        self._sb_theme = QLabel()
        self._sb_theme.setObjectName("sb_theme")
        self._sb_theme.setAlignment(Qt.AlignCenter)
        self._sb_theme.setCursor(Qt.PointingHandCursor)
        self._sb_theme.setFont(_qfn())
        self._sb_theme.mousePressEvent = lambda e: self._toggle_theme()
        sb_lay.addWidget(self._sb_theme)

        sb_author = QLabel("by vs-olitus")
        sb_author.setObjectName("sb_theme")
        sb_author.setAlignment(Qt.AlignCenter)
        sb_author.setFont(_qfn(-1))
        sb_lay.addWidget(sb_author)
        sb_gh = QLabel("github.com/Spade-sec/First")
        sb_gh.setObjectName("sb_theme")
        sb_gh.setAlignment(Qt.AlignCenter)
        sb_gh.setFont(_qfn(-2))
        sb_gh.setCursor(Qt.PointingHandCursor)
        sb_gh.mousePressEvent = lambda e: (
            QDesktopServices.openUrl(QUrl("https://github.com/Spade-sec/First")),
            self._log_add("info", "[gui] 已打开 GitHub 页面"))
        sb_lay.addWidget(sb_gh)
        sb_ver = QLabel("v1.0.9")
        sb_ver.setObjectName("sb_theme")
        sb_ver.setAlignment(Qt.AlignCenter)
        sb_ver.setFont(_qfn(-2))
        sb_lay.addWidget(sb_ver)
        sb_lay.addSpacing(12)
        self._update_theme_label()

        root_h.addWidget(self._sb)

        vline = QFrame()
        vline.setObjectName("vline")
        vline.setFixedWidth(1)
        root_h.addWidget(vline)

        # ── 右侧 ──
        right = QWidget()
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.setSpacing(0)

        hdr_frame = QWidget()
        hdr_frame.setFixedHeight(60)
        hdr_lay = QHBoxLayout(hdr_frame)
        hdr_lay.setContentsMargins(0, 0, 0, 0)
        self._hdr_title = QLabel("")
        self._hdr_title.setObjectName("page_title")
        hdr_lay.addWidget(self._hdr_title)
        hdr_lay.addStretch()
        right_lay.addWidget(hdr_frame)

        hdr_line = QFrame()
        hdr_line.setObjectName("hdr_line")
        hdr_line.setFixedHeight(1)
        right_lay.addWidget(hdr_line)

        self._stack = AnimatedStackedWidget()
        right_lay.addWidget(self._stack, 1)
        root_h.addWidget(right, 1)

        self._build_control()
        self._build_navigator()
        self._build_hook()
        self._build_targets()
        self._build_cloud()
        self._build_wxapi()
        self._build_extract()
        self._build_vconsole()
        self._build_logs()

    # ── 控制台 ──

    def _build_control(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(24, 8, 24, 8)
        lay.setSpacing(6)
        lay.setAlignment(Qt.AlignTop)

        # Card 1: 连接设置
        c1 = _make_card()
        c1_lay = QVBoxLayout(c1)
        c1_lay.setContentsMargins(16, 10, 16, 10)
        c1_lay.setSpacing(6)
        c1_lay.addWidget(_make_label("连接设置", bold=True))

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("CDP 端口"))
        self._cp_ent = _make_entry(width=100)
        self._cp_ent.setText(str(self._cfg.get("cdp_port", CDP_PORT)))
        self._cp_ent.textChanged.connect(lambda: self._auto_save())
        row1.addWidget(self._cp_ent)
        row1.addStretch()
        c1_lay.addLayout(row1)

        lay.addWidget(c1)

        # Action row
        ar = QHBoxLayout()
        self._btn_start = _make_btn("▶  启动调试", self._do_start)
        self._btn_start.setFont(_qfn(1, QFont.Bold))
        ar.addWidget(self._btn_start)
        self._btn_stop = _make_btn("■  停止", self._do_stop)
        self._btn_stop.setFont(_qfn(1, QFont.Bold))
        self._btn_stop.setEnabled(False)
        ar.addWidget(self._btn_stop)
        ar.addStretch()
        lay.addLayout(ar)

        # DevTools URL
        dt_row = QHBoxLayout()
        self._devtools_lbl = QLabel("")
        self._devtools_lbl.setProperty("class", "accent")
        self._devtools_lbl.setFont(_qfm(-1))
        self._devtools_lbl.setCursor(Qt.PointingHandCursor)
        self._devtools_lbl.mousePressEvent = lambda e: self._copy_devtools_url()
        dt_row.addWidget(self._devtools_lbl)
        self._devtools_copy_hint = QLabel("")
        self._devtools_copy_hint.setProperty("class", "muted")
        self._devtools_copy_hint.setFont(_qfn(-1))
        dt_row.addWidget(self._devtools_copy_hint)
        dt_row.addStretch()
        lay.addLayout(dt_row)

        # Card 3: 运行状态
        c3 = _make_card()
        c3_lay = QVBoxLayout(c3)
        c3_lay.setContentsMargins(16, 10, 16, 10)
        c3_lay.setSpacing(2)
        c3_lay.addWidget(_make_label("运行状态", bold=True))
        self._dots = {}
        for key, name in [("frida", "Frida"), ("miniapp", "小程序"), ("devtools", "DevTools")]:
            dr = QHBoxLayout()
            dot = StatusDot()
            dr.addWidget(dot)
            lb = QLabel(f"{name}: 未连接")
            dr.addWidget(lb)
            dr.addStretch()
            c3_lay.addLayout(dr)
            self._dots[key] = (dot, lb, name)
        self._app_lbl = QLabel("应用: --")
        self._app_lbl.setProperty("class", "muted")
        c3_lay.addWidget(self._app_lbl)
        self._appname_lbl = QLabel("")
        self._appname_lbl.setProperty("class", "muted")
        self._appname_lbl.setVisible(False)
        c3_lay.addWidget(self._appname_lbl)
        lay.addWidget(c3)

        self._stack.addWidget(page)
        self._page_map["control"] = self._stack.count() - 1

        # Card 4: 常见问题解决方案
        c4 = _make_card()
        c4_lay = QVBoxLayout(c4)
        c4_lay.setContentsMargins(16, 10, 16, 10)
        c4_lay.setSpacing(8)
        c4_lay.addWidget(_make_label("常见问题解决方案", bold=True))

        faq_items = [
            ("Frida 连接失败", "请确认当前版本是否在WMPF版本区间内,如无法解决建议安装建议版本。"),
            ("DevTools 打开内容为空", "点击启动调试前请勿打开小程序, 启动调试打开后再次启动小程序即可。"),
            (r"Frida 已显示连接，但小程序端显示未连接或步骤确认没问题且无法断点", r"若操作顺序无误，建议先彻底卸载微信并重启电脑-·如有重要聊天记录请提前备份·-。删除路径C:\Users\用户名\AppData\Roaming\Tencent\xwechat\XPlugin\Plugins\RadiumWMPF下所有以数字命名的文件夹,再次重启电脑后,安装微信 4.1.0.30 版本。安装完成后检查上述路径，确认文件夹编号为 16389。"),
        ]

        for title, solution in faq_items:
            item_lbl = QLabel(f"• {title}\n   {solution}")
            item_lbl.setWordWrap(True)
            item_lbl.setStyleSheet("color: #FFC107;")
            c4_lay.addWidget(item_lbl)

        c4_lay.addStretch()
        lay.addWidget(c4)

    # ── 路由导航 ──

    def _build_navigator(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(24, 12, 24, 16)
        lay.setSpacing(10)

        # 搜索栏
        sf = QHBoxLayout()
        sf.addWidget(QLabel("搜索"))
        self._srch_ent = _make_entry("输入路由关键字搜索...")
        self._srch_ent.textChanged.connect(self._do_filter)
        sf.addWidget(self._srch_ent, 1)
        lay.addLayout(sf)

        # 路由树
        tc = _make_card()
        tc_lay = QVBoxLayout(tc)
        tc_lay.setContentsMargins(0, 0, 0, 0)
        self._tree = QTreeWidget()
        self._tree.setFont(_qfn())
        self._tree.setHeaderHidden(True)
        self._tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self._tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._nav_context_menu)
        tc_lay.addWidget(self._tree)
        lay.addWidget(tc, 1)

        # 手动输入跳转
        mi = QHBoxLayout()
        mi.addWidget(QLabel("手动跳转"))
        self._nav_input = _make_entry("输入路由路径，回车跳转...")
        self._nav_input.returnPressed.connect(self._do_manual_go)
        mi.addWidget(self._nav_input, 1)
        self._btn_manual_go = _make_btn("跳转", self._do_manual_go)
        mi.addWidget(self._btn_manual_go)
        self._btn_copy_route = _make_btn("复制路由", self._do_copy_route)
        self._btn_copy_route.setEnabled(False)
        mi.addWidget(self._btn_copy_route)
        lay.addLayout(mi)

        # 导航按钮行 1
        b1 = QHBoxLayout()
        self._btn_go = _make_btn("跳转", self._do_go)
        self._btn_go.setEnabled(False)
        b1.addWidget(self._btn_go)
        self._btn_relaunch = _make_btn("重启到页面", self._do_relaunch)
        self._btn_relaunch.setEnabled(False)
        b1.addWidget(self._btn_relaunch)
        self._btn_back = _make_btn("返回上页", self._do_back)
        self._btn_back.setEnabled(False)
        b1.addWidget(self._btn_back)
        self._btn_refresh = _make_btn("刷新页面", self._do_refresh)
        self._btn_refresh.setEnabled(False)
        b1.addWidget(self._btn_refresh)
        b1.addStretch()
        self._btn_fetch = _make_btn("获取路由", self._do_fetch)
        self._btn_fetch.setEnabled(False)
        b1.addWidget(self._btn_fetch)
        lay.addLayout(b1)

        # 导航按钮行 2: 上一个/下一个 + 遍历 + 防跳转
        b2 = QHBoxLayout()
        self._btn_prev = _make_btn("◀ 上一个", self._do_prev)
        self._btn_prev.setEnabled(False)
        b2.addWidget(self._btn_prev)
        self._btn_next = _make_btn("下一个 ▶", self._do_next)
        self._btn_next.setEnabled(False)
        b2.addWidget(self._btn_next)
        b2.addSpacing(12)
        self._btn_auto = _make_btn("自动遍历", self._do_autovis)
        self._btn_auto.setEnabled(False)
        b2.addWidget(self._btn_auto)
        self._btn_autostop = _make_btn("停止遍历", self._do_autostop)
        self._btn_autostop.setEnabled(False)
        b2.addWidget(self._btn_autostop)
        b2.addSpacing(12)
        self._guard_switch = ToggleSwitch(False)
        self._guard_switch.setFixedSize(36, 18)
        self._guard_switch.setEnabled(False)
        self._guard_switch.toggled.connect(self._do_toggle_guard_switch)
        b2.addWidget(self._guard_switch)
        self._guard_label = QLabel("防跳转: 关闭")
        b2.addWidget(self._guard_label)
        b2.addStretch()
        lay.addLayout(b2)

        self._prog = QProgressBar()
        self._prog.setMaximum(100)
        self._prog.setValue(0)
        self._prog.setTextVisible(False)
        self._prog.setFixedHeight(6)
        lay.addWidget(self._prog)
        self._route_lbl = QLabel("当前路由: --")
        self._route_lbl.setFixedHeight(22)
        self._route_lbl.setProperty("class", "bold")
        lay.addWidget(self._route_lbl)

        self._stack.addWidget(page)
        self._page_map["navigator"] = self._stack.count() - 1

    # ── Hook 页面 ──

    def _build_hook(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(24, 12, 24, 16)
        lay.setSpacing(10)

        tip_row = QHBoxLayout()
        self._hook_tip = QLabel("将 .js 文件放入 hook_scripts/ 目录，点击「注入」即时执行")
        self._hook_tip.setProperty("class", "muted")
        tip_row.addWidget(self._hook_tip)
        tip_row.addStretch()
        self._btn_hook_refresh = _make_btn("刷新列表", self._hook_refresh)
        tip_row.addWidget(self._btn_hook_refresh)
        lay.addLayout(tip_row)

        c1 = _make_card()
        c1_lay = QVBoxLayout(c1)
        c1_lay.setContentsMargins(12, 12, 12, 12)
        c1_lay.setSpacing(6)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._hook_inner = QWidget()
        self._hook_inner_lay = QVBoxLayout(self._hook_inner)
        self._hook_inner_lay.setContentsMargins(0, 0, 0, 0)
        self._hook_inner_lay.setSpacing(6)
        self._hook_inner_lay.addStretch()
        scroll.setWidget(self._hook_inner)
        c1_lay.addWidget(scroll)
        lay.addWidget(c1, 1)

        self._hook_status_lbls = {}
        self._hook_refresh()

        self._stack.addWidget(page)
        self._page_map["hook"] = self._stack.count() - 1

    def _hook_refresh(self):
        while self._hook_inner_lay.count() > 1:
            item = self._hook_inner_lay.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._hook_status_lbls = {}

        hook_dir = os.path.join(_BASE_DIR, "hook_scripts")
        js_files = sorted(f for f in os.listdir(hook_dir) if f.endswith(".js")) if os.path.isdir(hook_dir) else []

        if not js_files:
            lbl = QLabel("hook_scripts/ 目录下无 .js 文件")
            lbl.setAlignment(Qt.AlignCenter)
            self._hook_inner_lay.insertWidget(0, lbl)
            return

        for fn in js_files:
            row = QFrame()
            row.setProperty("class", "hook_row")
            row.setFixedHeight(52)
            row_lay = QHBoxLayout(row)
            row_lay.setContentsMargins(12, 0, 12, 0)
            row_lay.setSpacing(8)

            icon_lbl = QLabel("JS")
            icon_lbl.setProperty("class", "js_badge")
            icon_lbl.setFont(_qfm(-1, QFont.Bold))
            icon_lbl.setFixedWidth(30)
            icon_lbl.setAlignment(Qt.AlignCenter)
            row_lay.addWidget(icon_lbl)

            name_lbl = QLabel(fn)
            name_lbl.setFont(_qfn(1))
            row_lay.addWidget(name_lbl, 1)

            is_global = fn in self._global_hook_scripts
            injected = fn in self._hook_injected
            if is_global and injected:
                status_text = "全局 ● 已注入"
            elif is_global:
                status_text = "全局 ○ 待注入"
            elif injected:
                status_text = "● 已注入"
            else:
                status_text = "○ 未注入"
            status_lbl = QLabel(status_text)
            c = _TH[self._tn]
            status_lbl.setStyleSheet(f"color: {c['success'] if injected else c['text3']};")
            row_lay.addWidget(status_lbl)
            self._hook_status_lbls[fn] = status_lbl

            global_cb = QCheckBox("全局")
            global_cb.setChecked(is_global)
            global_cb.toggled.connect(lambda checked, f=fn: self._hook_global_toggle(f, checked))
            row_lay.addWidget(global_cb)

            inject_btn = _make_btn("注入", lambda checked=False, f=fn: self._hook_inject(f))
            row_lay.addWidget(inject_btn)
            clear_btn = _make_btn("清除", lambda checked=False, f=fn: self._hook_clear(f))
            row_lay.addWidget(clear_btn)

            self._hook_inner_lay.insertWidget(self._hook_inner_lay.count() - 1, row)

    def _hook_inject(self, filename):
        if not self._engine or not self._loop or not self._loop.is_running():
            self._log_add("error", "[Hook] 请先启动调试")
            return
        hook_dir = os.path.join(_BASE_DIR, "hook_scripts")
        filepath = os.path.join(hook_dir, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                source = f.read()
        except Exception as e:
            self._log_add("error", f"[Hook] 读取文件失败: {e}")
            return
        asyncio.run_coroutine_threadsafe(
            self._ahook_inject(filename, source), self._loop)

    async def _ahook_inject(self, filename, source):
        try:
            await self._engine.evaluate_js(source, timeout=5.0)
            self._hook_injected.add(filename)
            self._log_q.put(("info", f"[Hook] 已注入: {filename}"))
            self._log_q.put(("__hook_status__", filename, True))
        except Exception as e:
            self._log_q.put(("error", f"[Hook] 注入失败 {filename}: {e}"))

    def _hook_clear(self, filename):
        self._hook_injected.discard(filename)
        self._hook_update_status(filename, False)
        self._log_add("info", f"[Hook] 已清除标记: {filename}（注意: JS 注入后无法真正撤销，需刷新页面）")

    def _hook_update_status(self, filename, injected):
        c = _TH[self._tn]
        lbl = self._hook_status_lbls.get(filename)
        if lbl:
            is_global = filename in self._global_hook_scripts
            if is_global and injected:
                lbl.setText("全局 ● 已注入")
                lbl.setStyleSheet(f"color: {c['success']};")
            elif is_global:
                lbl.setText("全局 ○ 待注入")
                lbl.setStyleSheet(f"color: {c['text3']};")
            elif injected:
                lbl.setText("● 已注入")
                lbl.setStyleSheet(f"color: {c['success']};")
            else:
                lbl.setText("○ 未注入")
                lbl.setStyleSheet(f"color: {c['text3']};")

    def _hook_global_toggle(self, filename, checked):
        if checked:
            self._global_hook_scripts.add(filename)
        else:
            self._global_hook_scripts.discard(filename)
        injected = filename in self._hook_injected
        self._hook_update_status(filename, injected)
        self._auto_save()

    def _hook_auto_inject_globals(self):
        """Auto-inject all global hook scripts (called when miniapp stabilizes)."""
        if not self._engine or not self._loop or not self._loop.is_running():
            return
        hook_dir = os.path.join(_BASE_DIR, "hook_scripts")
        for fn in list(self._global_hook_scripts):
            if fn in self._hook_injected:
                continue
            filepath = os.path.join(hook_dir, fn)
            if not os.path.isfile(filepath):
                continue
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    source = f.read()
            except Exception:
                continue
            asyncio.run_coroutine_threadsafe(
                self._ahook_inject(fn, source), self._loop)

    def _do_global_inject(self, gen):
        """独立的全局注入定时回调，只在小程序连接变化时触发，不受 CDP 等影响。"""
        if gen != self._global_inject_gen:
            return
        if not self._miniapp_connected:
            return
        if self._global_hook_scripts:
            self._hook_auto_inject_globals()
            self._log_add("info", "[Hook] 自动注入全局脚本")

    # ── 页面目标 ──

    def _build_targets(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(24, 12, 24, 16)
        lay.setSpacing(10)

        tip_row = QHBoxLayout()
        tip = QLabel("列出当前调试会话可见的微信内置浏览器 / 小程序 / webview 服务")
        tip.setProperty("class", "muted")
        tip_row.addWidget(tip)
        tip_row.addStretch()
        self._btn_tgt_refresh = _make_btn("刷新目标", self._do_targets_refresh)
        self._btn_tgt_refresh.setEnabled(False)
        tip_row.addWidget(self._btn_tgt_refresh)
        self._btn_tgt_attach = _make_btn("附加到选中目标", self._do_targets_attach)
        self._btn_tgt_attach.setEnabled(False)
        tip_row.addWidget(self._btn_tgt_attach)
        self._btn_tgt_copy = _make_btn("复制 TargetId", self._do_targets_copy)
        self._btn_tgt_copy.setEnabled(False)
        tip_row.addWidget(self._btn_tgt_copy)
        lay.addLayout(tip_row)

        tc = _make_card()
        tc_lay = QVBoxLayout(tc)
        tc_lay.setContentsMargins(0, 0, 0, 0)
        self._targets_tree = QTreeWidget()
        self._targets_tree.setFont(_qfn())
        self._targets_tree.header().setFont(_qfn())
        self._targets_tree.setRootIsDecorated(False)
        self._targets_tree.setIndentation(0)
        self._targets_tree.setHeaderLabels(["类型", "标题", "URL", "TargetId"])
        self._targets_tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self._targets_tree.itemSelectionChanged.connect(self._targets_on_select)
        self._targets_tree.itemDoubleClicked.connect(lambda *_: self._do_targets_attach())
        hdr = self._targets_tree.header()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.Interactive)
        hdr.setSectionResizeMode(2, QHeaderView.Stretch)
        hdr.setSectionResizeMode(3, QHeaderView.Interactive)
        hdr.setMinimumSectionSize(50)
        self._targets_tree.setColumnWidth(1, 200)
        self._targets_tree.setColumnWidth(3, 290)
        tc_lay.addWidget(self._targets_tree)
        lay.addWidget(tc, 1)

        self._targets_status_lbl = QLabel("状态: 未连接小程序")
        self._targets_status_lbl.setProperty("class", "muted")
        lay.addWidget(self._targets_status_lbl)

        self._stack.addWidget(page)
        self._page_map["targets"] = self._stack.count() - 1

    def _targets_btns(self, on):
        if not hasattr(self, "_btn_tgt_refresh"):
            return
        self._btn_tgt_refresh.setEnabled(on)
        has_sel = bool(on and self._targets_tree.selectedItems())
        self._btn_tgt_attach.setEnabled(has_sel)
        self._btn_tgt_copy.setEnabled(has_sel)

    def _targets_on_select(self):
        self._targets_btns(bool(self._engine and self._miniapp_connected))

    def _selected_target(self):
        items = self._targets_tree.selectedItems()
        if not items:
            self._log_add("error", "[页面目标] 请先选择一个目标")
            return None
        return items[0].data(0, Qt.UserRole) or {}

    def _do_targets_refresh(self):
        if not self._engine or not self._loop or not self._loop.is_running():
            self._log_add("error", "[页面目标] 请先启动调试并连接小程序")
            return
        self._btn_tgt_refresh.setEnabled(False)
        self._targets_status_lbl.setText("状态: 正在刷新...")
        asyncio.run_coroutine_threadsafe(self._atargets_refresh(), self._loop)

    async def _atargets_refresh(self):
        try:
            resp = await self._engine.send_cdp_command("Target.getTargets", timeout=8.0)
            infos = resp.get("result", {}).get("targetInfos", [])
            self._tgt_q.put(("targets", infos))
        except Exception as e:
            self._tgt_q.put(("error", f"刷新失败: {e}"))

    def _do_targets_attach(self):
        target = self._selected_target()
        if not target or not self._engine or not self._loop or not self._loop.is_running():
            return
        target_id = target.get("targetId", "")
        if not target_id:
            self._log_add("error", "[页面目标] 选中项没有 TargetId")
            return
        self._btn_tgt_attach.setEnabled(False)
        self._targets_status_lbl.setText("状态: 正在附加...")
        asyncio.run_coroutine_threadsafe(self._atargets_attach(target_id), self._loop)

    async def _atargets_attach(self, target_id):
        try:
            resp = await self._engine.send_cdp_command(
                "Target.attachToTarget", {"targetId": target_id}, timeout=8.0)
            self._tgt_q.put(("attached", target_id, resp))
        except Exception as e:
            self._tgt_q.put(("error", f"附加失败: {e}"))

    def _do_targets_copy(self):
        target = self._selected_target()
        if not target:
            return
        target_id = target.get("targetId", "")
        if target_id:
            QApplication.clipboard().setText(target_id)
            self._targets_status_lbl.setText("状态: TargetId 已复制")
            self._log_add("info", f"[页面目标] 已复制 TargetId: {target_id}")

    def _handle_tgt(self, item):
        kind = item[0]
        c = _TH[self._tn]
        if kind == "targets":
            targets = item[1]
            self._targets_tree.clear()
            for target in targets:
                target_id = target.get("targetId", "")
                title = target.get("title", "") or "--"
                url = target.get("url", "") or "--"
                typ = target.get("type", "") or "--"
                row = QTreeWidgetItem([typ, title, url, target_id])
                row.setData(0, Qt.UserRole, target)
                if target.get("attached"):
                    for col in range(4):
                        row.setForeground(col, QColor(c["success"]))
                self._targets_tree.addTopLevelItem(row)
            self._targets_status_lbl.setText(f"状态: 发现 {len(targets)} 个目标")
            self._targets_status_lbl.setStyleSheet(f"color: {c['success']};")
            self._log_add("info", f"[页面目标] 发现 {len(targets)} 个可选目标")
            self._targets_btns(bool(self._miniapp_connected))
        elif kind == "attached":
            _, target_id, resp = item
            session_id = resp.get("result", {}).get("sessionId", "")
            suffix = f", sessionId={session_id}" if session_id else ""
            self._targets_status_lbl.setText(f"状态: 已附加 {target_id}{suffix}")
            self._targets_status_lbl.setStyleSheet(f"color: {c['success']};")
            self._log_add("info", f"[页面目标] 已附加到目标: {target_id}{suffix}")
            self._targets_btns(bool(self._miniapp_connected))
        elif kind == "error":
            msg = item[1]
            self._targets_status_lbl.setText(f"状态: {msg}")
            self._targets_status_lbl.setStyleSheet(f"color: {c['error']};")
            self._log_add("error", f"[页面目标] {msg}")
            self._targets_btns(bool(self._miniapp_connected))

    # ── 云扫描 ──

    def _build_cloud(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # 内嵌 QStackedWidget: 主视图(0) + 动态捕获视图(1)
        self._cloud_stack = QStackedWidget()
        lay.addWidget(self._cloud_stack)

        # ── 主视图 (index 0) ──
        main_page = QWidget()
        main_lay = QVBoxLayout(main_page)
        main_lay.setContentsMargins(24, 12, 24, 16)
        main_lay.setSpacing(10)

        ctrl = QHBoxLayout()
        self._btn_cloud_live = _make_btn("动态捕获", self._cloud_show_live)
        ctrl.addWidget(self._btn_cloud_live)
        self._btn_cloud_static = _make_btn("静态扫描", self._cloud_do_static_scan)
        ctrl.addWidget(self._btn_cloud_static)
        self._btn_cloud_clear = _make_btn("清空记录", self._cloud_do_clear)
        ctrl.addWidget(self._btn_cloud_clear)
        self._cloud_scan_lbl = QLabel("")
        ctrl.addWidget(self._cloud_scan_lbl)
        ctrl.addStretch()
        self._btn_cloud_export = _make_btn("导出报告", self._cloud_do_export)
        ctrl.addWidget(self._btn_cloud_export)
        main_lay.addLayout(ctrl)

        tc = _make_card()
        tc_lay = QVBoxLayout(tc)
        tc_lay.setContentsMargins(12, 8, 12, 8)
        tc_lay.setSpacing(4)

        title_row = QHBoxLayout()
        title_row.addWidget(_make_label("云函数捕获记录", bold=True))
        self._cloud_env_lbl = QLabel("全局捕获（默认开启）")
        title_row.addWidget(self._cloud_env_lbl)
        title_row.addStretch()
        title_row.addWidget(QLabel("搜索"))
        self._cloud_search_ent = _make_entry(width=180)
        self._cloud_search_ent.textChanged.connect(self._cloud_filter)
        title_row.addWidget(self._cloud_search_ent)
        tc_lay.addLayout(title_row)

        self._cloud_tree = QTreeWidget()
        self._cloud_tree.setFont(_qfn())
        self._cloud_tree.header().setFont(_qfn())
        self._cloud_tree.setRootIsDecorated(False)
        self._cloud_tree.setIndentation(0)
        self._cloud_tree.setHeaderLabels(["AppID", "类型", "名称", "参数", "状态", "时间"])
        header = self._cloud_tree.header()
        header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Interactive)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Interactive)
        header.setSectionResizeMode(5, QHeaderView.Interactive)
        self._cloud_tree.setColumnWidth(0, 100)
        self._cloud_tree.setColumnWidth(1, 70)
        self._cloud_tree.setColumnWidth(2, 140)
        self._cloud_tree.setColumnWidth(4, 50)
        self._cloud_tree.setColumnWidth(5, 70)
        self._cloud_tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self._cloud_tree.itemClicked.connect(self._cloud_on_select)
        self._cloud_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self._cloud_tree.customContextMenuRequested.connect(self._cloud_tree_context_menu)
        tc_lay.addWidget(self._cloud_tree)
        main_lay.addWidget(tc, 1)

        call_row = QHBoxLayout()
        call_row.addWidget(QLabel("手动调用"))
        self._cloud_name_ent = _make_entry(width=140)
        call_row.addWidget(self._cloud_name_ent)
        call_row.addWidget(QLabel("参数"))
        self._cloud_data_ent = _make_entry()
        self._cloud_data_ent.setText("{}")
        call_row.addWidget(self._cloud_data_ent, 1)
        self._btn_cloud_call = _make_btn("调用", self._cloud_do_call)
        call_row.addWidget(self._btn_cloud_call)
        main_lay.addLayout(call_row)

        self._cloud_result = QTextEdit()
        self._cloud_result.setReadOnly(True)
        self._cloud_result.setFixedHeight(120)
        self._cloud_result.setFont(_qfm())
        main_lay.addWidget(self._cloud_result)

        bot = QHBoxLayout()
        self._cloud_status_lbl = QLabel("捕获: 0 条")
        bot.addWidget(self._cloud_status_lbl)
        bot.addStretch()
        main_lay.addLayout(bot)

        self._cloud_stack.addWidget(main_page)  # index 0: 主视图

        # ── 动态捕获视图 (index 1) ──
        self._build_cloud_live_page()

        self._stack.addWidget(page)
        self._page_map["cloud"] = self._stack.count() - 1

    def _build_cloud_live_page(self):
        """构建动态捕获子页面 (cloud_stack index 1)"""
        live_page = QWidget()
        live_lay = QVBoxLayout(live_page)
        live_lay.setContentsMargins(24, 12, 24, 16)
        live_lay.setSpacing(10)

        # 顶部控制栏
        top_bar = QHBoxLayout()
        self._btn_cloud_live_back = _make_btn("← 返回", self._cloud_live_back)
        top_bar.addWidget(self._btn_cloud_live_back)
        top_bar.addWidget(_make_label("动态捕获", bold=True))
        self._cloud_live_status_lbl = QLabel("捕获中...")
        top_bar.addWidget(self._cloud_live_status_lbl)
        top_bar.addStretch()
        self._cloud_live_search_ent = _make_entry(width=160)
        self._cloud_live_search_ent.setPlaceholderText("搜索...")
        self._cloud_live_search_ent.textChanged.connect(self._cloud_live_filter)
        top_bar.addWidget(self._cloud_live_search_ent)
        self._btn_cloud_live_clear = _make_btn("清空", self._cloud_live_clear)
        top_bar.addWidget(self._btn_cloud_live_clear)
        live_lay.addLayout(top_bar)

        # 左右分栏
        splitter = QHBoxLayout()

        # 左侧: 捕获列表
        left_card = _make_card()
        left_lay = QVBoxLayout(left_card)
        left_lay.setContentsMargins(8, 8, 8, 8)
        left_lay.setSpacing(4)
        self._cloud_live_tree = QTreeWidget()
        self._cloud_live_tree.setFont(_qfn())
        self._cloud_live_tree.header().setFont(_qfn())
        self._cloud_live_tree.setRootIsDecorated(False)
        self._cloud_live_tree.setIndentation(0)
        self._cloud_live_tree.setHeaderLabels(["类型", "名称", "状态", "时间"])
        lh = self._cloud_live_tree.header()
        lh.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        lh.setStretchLastSection(False)
        lh.setSectionResizeMode(0, QHeaderView.Interactive)
        lh.setSectionResizeMode(1, QHeaderView.Stretch)
        lh.setSectionResizeMode(2, QHeaderView.Interactive)
        lh.setSectionResizeMode(3, QHeaderView.Interactive)
        self._cloud_live_tree.setColumnWidth(0, 70)
        self._cloud_live_tree.setColumnWidth(2, 50)
        self._cloud_live_tree.setColumnWidth(3, 70)
        self._cloud_live_tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self._cloud_live_tree.itemClicked.connect(self._cloud_live_select)
        left_lay.addWidget(self._cloud_live_tree)
        splitter.addWidget(left_card, 2)

        # 右侧: 详情面板
        right_card = _make_card()
        right_lay = QVBoxLayout(right_card)
        right_lay.setContentsMargins(12, 8, 12, 8)
        right_lay.setSpacing(6)

        right_lay.addWidget(_make_label("请求参数", bold=True))
        self._cloud_live_req = QTextEdit()
        self._cloud_live_req.setReadOnly(True)
        self._cloud_live_req.setFont(_qfm())
        self._cloud_live_req.setPlaceholderText("选择左侧记录查看请求参数")
        right_lay.addWidget(self._cloud_live_req, 1)

        right_lay.addWidget(_make_label("返回结果", bold=True))
        self._cloud_live_resp = QTextEdit()
        self._cloud_live_resp.setReadOnly(True)
        self._cloud_live_resp.setFont(_qfm())
        self._cloud_live_resp.setPlaceholderText("选择左侧记录查看返回结果")
        right_lay.addWidget(self._cloud_live_resp, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._btn_cloud_live_replay = _make_btn("一键重放", self._cloud_live_replay)
        self._btn_cloud_live_replay.setEnabled(False)
        btn_row.addWidget(self._btn_cloud_live_replay)
        right_lay.addLayout(btn_row)

        splitter.addWidget(right_card, 3)
        live_lay.addLayout(splitter, 1)

        self._cloud_stack.addWidget(live_page)  # index 1: 动态捕获视图
        self._cloud_live_selected_idx = -1

    # ── WxAPI 捕获 ──

    def _build_wxapi(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(24, 12, 24, 16)
        lay.setSpacing(10)

        # 顶部控制栏
        top_bar = QHBoxLayout()
        top_bar.addWidget(_make_label("WxAPI 捕获", bold=True))
        self._btn_wxapi_toggle = _make_btn("开启捕获", self._wxapi_toggle)
        top_bar.addWidget(self._btn_wxapi_toggle)
        self._wxapi_status_lbl = QLabel("已关闭")
        top_bar.addWidget(self._wxapi_status_lbl)
        top_bar.addStretch()
        # 原生桥接开关（默认关闭）
        self._wxapi_bridge_cb = QCheckBox("原生桥接")
        self._wxapi_bridge_cb.setChecked(False)
        self._wxapi_bridge_cb.setToolTip("捕获 WeixinJSBridge 底层调用（会产生大量噪音）")
        top_bar.addWidget(self._wxapi_bridge_cb)
        # wx.request 开关（默认关闭）
        self._wxapi_request_cb = QCheckBox("wx.request")
        self._wxapi_request_cb.setChecked(False)
        self._wxapi_request_cb.setToolTip("捕获 wx.request 网络请求（数量较多）")
        top_bar.addWidget(self._wxapi_request_cb)
        # wx.storage 开关（默认关闭）
        self._wxapi_storage_cb = QCheckBox("缓存")
        self._wxapi_storage_cb.setChecked(False)
        self._wxapi_storage_cb.setToolTip("捕获 wx.setStorage/getStorage 等缓存操作")
        top_bar.addWidget(self._wxapi_storage_cb)
        self._wxapi_search_ent = _make_entry(width=160)
        self._wxapi_search_ent.setPlaceholderText("搜索...")
        self._wxapi_search_ent.textChanged.connect(self._wxapi_filter)
        top_bar.addWidget(self._wxapi_search_ent)
        self._btn_wxapi_clear = _make_btn("清空", self._wxapi_clear)
        top_bar.addWidget(self._btn_wxapi_clear)
        lay.addLayout(top_bar)

        # 左右分栏
        splitter = QHBoxLayout()

        # 左侧: 捕获列表
        left_card = _make_card()
        left_lay = QVBoxLayout(left_card)
        left_lay.setContentsMargins(8, 8, 8, 8)
        left_lay.setSpacing(4)
        self._wxapi_tree = QTreeWidget()
        self._wxapi_tree.setFont(_qfn())
        self._wxapi_tree.header().setFont(_qfn())
        self._wxapi_tree.setRootIsDecorated(False)
        self._wxapi_tree.setIndentation(0)
        self._wxapi_tree.setHeaderLabels(["类型", "名称", "状态", "时间"])
        wh = self._wxapi_tree.header()
        wh.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        wh.setStretchLastSection(False)
        wh.setSectionResizeMode(0, QHeaderView.Interactive)
        wh.setSectionResizeMode(1, QHeaderView.Stretch)
        wh.setSectionResizeMode(2, QHeaderView.Interactive)
        wh.setSectionResizeMode(3, QHeaderView.Interactive)
        self._wxapi_tree.setColumnWidth(0, 90)
        self._wxapi_tree.setColumnWidth(2, 60)
        self._wxapi_tree.setColumnWidth(3, 80)
        self._wxapi_tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self._wxapi_tree.itemClicked.connect(self._wxapi_select)
        left_lay.addWidget(self._wxapi_tree)
        splitter.addWidget(left_card, 2)

        # 右侧: 详情面板
        right_card = _make_card()
        right_lay = QVBoxLayout(right_card)
        right_lay.setContentsMargins(12, 8, 12, 8)
        right_lay.setSpacing(6)

        # 类型 + 名称标题
        self._wxapi_detail_title = _make_label("", bold=True)
        self._wxapi_detail_title.setWordWrap(True)
        right_lay.addWidget(self._wxapi_detail_title)

        right_lay.addWidget(_make_label("请求参数", bold=False))
        self._wxapi_req = QTextEdit()
        self._wxapi_req.setReadOnly(True)
        self._wxapi_req.setFont(_qfm())
        self._wxapi_req.setPlaceholderText("选择左侧记录查看请求参数")
        self._wxapi_req.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        right_lay.addWidget(self._wxapi_req, 1)

        right_lay.addWidget(_make_label("返回结果", bold=False))
        self._wxapi_resp = QTextEdit()
        self._wxapi_resp.setReadOnly(True)
        self._wxapi_resp.setFont(_qfm())
        self._wxapi_resp.setPlaceholderText("选择左侧记录查看返回结果")
        self._wxapi_resp.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        right_lay.addWidget(self._wxapi_resp, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._btn_wxapi_replay = _make_btn("一键重放", self._wxapi_replay)
        self._btn_wxapi_replay.setEnabled(False)
        btn_row.addWidget(self._btn_wxapi_replay)
        right_lay.addLayout(btn_row)

        splitter.addWidget(right_card, 3)
        lay.addLayout(splitter, 1)

        self._stack.addWidget(page)
        self._page_map["wxapi"] = self._stack.count() - 1

    # ── 敏感信息提取 ──

    def _build_extract(self):
        # 外层使用 QStackedWidget 实现子页面切换
        self._ext_stack = QStackedWidget()

        # =================== 主页面 ===================
        main_page = QWidget()
        main_lay = QVBoxLayout(main_page)
        main_lay.setContentsMargins(24, 8, 24, 8)
        main_lay.setSpacing(8)

        # --- Row 1: Applet目录 ---
        c1 = _make_card()
        c1_lay = QVBoxLayout(c1)
        c1_lay.setContentsMargins(16, 10, 16, 10)
        c1_lay.setSpacing(6)

        path_row = QHBoxLayout()
        path_row.addWidget(_make_label("Applet目录", bold=True))
        self._ext_path_ent = _make_entry("wxapkg 包目录路径...")
        # 自动检测默认路径
        from src.wxapkg import get_default_packages_dir
        default_pkg = get_default_packages_dir() or ""
        saved_path = self._cfg.get("extract_packages_dir", "")
        if saved_path:
            self._ext_path_ent.setText(saved_path)
        elif default_pkg:
            self._ext_path_ent.setText(default_pkg)
        # 先连接信号，然后手动刷新一次（setText 不会重复触发因为信号在之后连接）
        # 注意: setText 在信号连接前调用，所以不会触发重复刷新
        self._ext_path_ent.textChanged.connect(self._ext_on_path_changed)
        path_row.addWidget(self._ext_path_ent, 1)
        btn_auto = _make_btn("自动选择", self._ext_auto_detect)
        path_row.addWidget(btn_auto)
        btn_browse = _make_btn("选择", self._ext_browse)
        path_row.addWidget(btn_browse)
        c1_lay.addLayout(path_row)
        main_lay.addWidget(c1)

        # --- Row 2: 功能区 ---
        func_row = QHBoxLayout()
        self._btn_ext_regex = _make_btn("正则配置", self._ext_goto_regex)
        func_row.addWidget(self._btn_ext_regex)
        self._btn_ext_clear_decompiled = _make_btn("清空解包文件", self._ext_clear_decompiled)
        func_row.addWidget(self._btn_ext_clear_decompiled)
        self._btn_ext_clear_applet = _make_btn("清空Applet目录", self._ext_clear_applet)
        func_row.addWidget(self._btn_ext_clear_applet)
        func_row.addStretch()
        # 自动反编译 & 自动提取 开关
        func_row.addWidget(_make_label("自动反编译"))
        self._tog_auto_dec = ToggleSwitch(self._cfg.get("auto_decompile", False))
        self._tog_auto_dec.toggled.connect(lambda v: self._auto_save())
        func_row.addWidget(self._tog_auto_dec)
        func_row.addWidget(_make_label("自动提取"))
        self._tog_auto_scan = ToggleSwitch(self._cfg.get("auto_scan", False))
        self._tog_auto_scan.toggled.connect(lambda v: self._auto_save())
        func_row.addWidget(self._tog_auto_scan)
        main_lay.addLayout(func_row)

        # --- 进度 + 状态 ---
        self._ext_prog = QProgressBar()
        self._ext_prog.setMaximum(100)
        self._ext_prog.setValue(0)
        self._ext_prog.setTextVisible(False)
        self._ext_prog.setFixedHeight(6)
        main_lay.addWidget(self._ext_prog)
        self._ext_status_lbl = QLabel("就绪")
        self._ext_status_lbl.setProperty("class", "muted")
        main_lay.addWidget(self._ext_status_lbl)

        # --- Row 3: 小程序列表 ---
        list_card = _make_card()
        list_lay = QVBoxLayout(list_card)
        list_lay.setContentsMargins(0, 6, 0, 6)
        list_lay.setSpacing(0)

        # 表头
        hdr = QHBoxLayout()
        hdr.setContentsMargins(16, 4, 16, 4)
        hdr_appid = _make_label("AppID", bold=True)
        hdr_appid.setFixedWidth(180)
        hdr.addWidget(hdr_appid)
        hdr_name = _make_label("名称", bold=True)
        hdr_name.setMinimumWidth(100)
        hdr.addWidget(hdr_name, 1)
        hdr_ops = _make_label("操作", bold=True)
        hdr.addWidget(hdr_ops)
        list_lay.addLayout(hdr)

        # 分割线
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: rgba(128,128,128,0.2);")
        list_lay.addWidget(sep)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._ext_list_inner = QWidget()
        self._ext_list_layout = QVBoxLayout(self._ext_list_inner)
        self._ext_list_layout.setContentsMargins(8, 4, 8, 4)
        self._ext_list_layout.setSpacing(4)
        self._ext_list_layout.addStretch()
        scroll.setWidget(self._ext_list_inner)
        list_lay.addWidget(scroll, 1)

        main_lay.addWidget(list_card, 1)

        # 日志区
        self._ext_logbox = QTextEdit()
        self._ext_logbox.setReadOnly(True)
        self._ext_logbox.setFont(_qfm())
        self._ext_logbox.setMaximumHeight(120)
        main_lay.addWidget(self._ext_logbox)

        self._ext_stack.addWidget(main_page)  # index 0

        # =================== 正则配置子页面 ===================
        regex_page = QWidget()
        regex_lay = QVBoxLayout(regex_page)
        regex_lay.setContentsMargins(24, 8, 24, 8)
        regex_lay.setSpacing(8)

        # 返回按钮行
        regex_top = QHBoxLayout()
        btn_back_regex = _make_btn("← 返回", lambda: self._ext_stack.setCurrentIndex(0))
        regex_top.addWidget(btn_back_regex)
        regex_top.addWidget(_make_label("正则配置", bold=True))
        regex_top.addStretch()
        regex_lay.addLayout(regex_top)

        # 自定义正则卡片
        custom_card = _make_card()
        cc_lay = QVBoxLayout(custom_card)
        cc_lay.setContentsMargins(16, 10, 16, 10)
        cc_lay.setSpacing(6)
        cc_hdr = QHBoxLayout()
        cc_hdr.addWidget(_make_label("自定义正则", bold=True))
        cc_hdr.addWidget(_make_label("(提取时会与内置规则合并使用)", muted=True))
        cc_hdr.addStretch()
        btn_add = _make_btn("新建", self._ext_add_pattern)
        cc_hdr.addWidget(btn_add)
        cc_lay.addLayout(cc_hdr)

        # 表头行
        cc_hdr_row = QHBoxLayout()
        cc_hdr_row.setContentsMargins(12, 4, 12, 4)
        h1 = _make_label("栏目", bold=True); h1.setFixedWidth(120)
        cc_hdr_row.addWidget(h1)
        h2 = _make_label("正则表达式", bold=True)
        cc_hdr_row.addWidget(h2, 1)
        h3 = _make_label("状态", bold=True); h3.setFixedWidth(50)
        cc_hdr_row.addWidget(h3)
        h4 = _make_label("操作", bold=True); h4.setFixedWidth(180)
        cc_hdr_row.addWidget(h4)
        cc_lay.addLayout(cc_hdr_row)
        cc_sep = QFrame(); cc_sep.setFixedHeight(1)
        cc_sep.setStyleSheet("background: rgba(128,128,128,0.2);")
        cc_lay.addWidget(cc_sep)
        # 滚动区域放行列表
        self._ext_pat_scroll = QScrollArea()
        self._ext_pat_scroll.setWidgetResizable(True)
        self._ext_pat_scroll.setStyleSheet("QScrollArea { border: none; }")
        self._ext_pat_inner = QWidget()
        self._ext_pat_layout = QVBoxLayout(self._ext_pat_inner)
        self._ext_pat_layout.setContentsMargins(0, 0, 0, 0)
        self._ext_pat_layout.setSpacing(4)
        self._ext_pat_layout.addStretch()
        self._ext_pat_scroll.setWidget(self._ext_pat_inner)
        cc_lay.addWidget(self._ext_pat_scroll)
        regex_lay.addWidget(custom_card, 1)  # stretch=1，自定义区域占大空间

        # 内置正则卡片（紧凑）
        builtin_card = _make_card()
        bc_lay = QVBoxLayout(builtin_card)
        bc_lay.setContentsMargins(16, 10, 16, 10)
        bc_lay.setSpacing(6)
        bc_lay.addWidget(_make_label("内置正则规则 (只读)", bold=True))

        self._ext_builtin_tree = QTreeWidget()
        self._ext_builtin_tree.setFont(_qfn())
        self._ext_builtin_tree.header().setFont(_qfn())
        self._ext_builtin_tree.setHeaderLabels(["分类", "正则/说明"])
        bh = self._ext_builtin_tree.header()
        bh.setStretchLastSection(True)
        bh.setSectionResizeMode(0, QHeaderView.Interactive)
        self._ext_builtin_tree.setColumnWidth(0, 200)
        self._ext_builtin_tree.setRootIsDecorated(False)
        self._ext_builtin_tree.setMaximumHeight(200)
        bc_lay.addWidget(self._ext_builtin_tree)
        regex_lay.addWidget(builtin_card)  # 无stretch，内置区域紧凑

        self._ext_stack.addWidget(regex_page)  # index 1

        # =================== 查看敏感信息子页面 ===================
        view_page = QWidget()
        view_lay = QVBoxLayout(view_page)
        view_lay.setContentsMargins(16, 8, 16, 8)
        view_lay.setSpacing(6)

        view_top = QHBoxLayout()
        btn_back_view = _make_btn("← 返回", lambda: self._ext_stack.setCurrentIndex(0))
        view_top.addWidget(btn_back_view)
        self._ext_view_title = _make_label("查看敏感信息", bold=True)
        view_top.addWidget(self._ext_view_title)
        view_top.addStretch()
        self._btn_ext_open_html = _make_btn("网页访问", self._ext_open_html)
        view_top.addWidget(self._btn_ext_open_html)
        view_lay.addLayout(view_top)

        # 结果展示区 (滚动)
        self._ext_view_scroll = QScrollArea()
        self._ext_view_scroll.setWidgetResizable(True)
        self._ext_view_scroll.setStyleSheet("QScrollArea { border: none; }")
        self._ext_view_inner = QWidget()
        self._ext_view_top_layout = QVBoxLayout(self._ext_view_inner)
        self._ext_view_top_layout.setContentsMargins(0, 0, 0, 0)
        self._ext_view_top_layout.setSpacing(0)
        self._ext_view_scroll.setWidget(self._ext_view_inner)
        view_lay.addWidget(self._ext_view_scroll, 1)

        self._ext_stack.addWidget(view_page)  # index 2

        # 注册到主 stack
        self._stack.addWidget(self._ext_stack)
        self._page_map["extract"] = self._stack.count() - 1

        # 填充内置正则
        self._ext_fill_builtin_patterns()
        self._ext_refresh_custom_patterns()

        # 延迟加载小程序列表
        QTimer.singleShot(500, self._ext_refresh_apps)

        # 定时监控目录变化 (每5秒)
        self._ext_watch_timer = QTimer()
        self._ext_watch_timer.timeout.connect(self._ext_check_dir_changes)
        self._ext_watch_timer.start(5000)
        self._ext_last_appids = set()  # 上一次扫描到的 appids

        # 存储当前查看的 html path
        self._ext_current_html = ""
        self._ext_current_json = ""

    # ============================================
    # 提取页 - 辅助方法
    # ============================================

    def _ext_browse(self):
        d = QFileDialog.getExistingDirectory(self, "选择小程序包目录", self._ext_path_ent.text())
        if d:
            self._ext_path_ent.setText(d)

    def _ext_on_path_changed(self):
        """路径变化时自动保存和刷新列表"""
        self._auto_save()
        self._ext_refresh_apps()

    def _ext_check_dir_changes(self):
        """定时检查目录是否有新的小程序包"""
        pkg_dir = self._ext_path_ent.text().strip()
        if not pkg_dir or not os.path.isdir(pkg_dir):
            return

        # 快速扫描子目录名称
        try:
            current_dirs = set()
            for entry in os.listdir(pkg_dir):
                if os.path.isdir(os.path.join(pkg_dir, entry)):
                    current_dirs.add(entry)
        except Exception:
            return

        if current_dirs != self._ext_last_appids:
            new_ids = current_dirs - self._ext_last_appids
            self._ext_last_appids = current_dirs
            if new_ids:
                self._ext_refresh_apps()
                for nid in new_ids:
                    self._ext_log(f"检测到新小程序: {nid}")
                # 自动处理新增的小程序
                self._ext_auto_process_new(new_ids)

    def _ext_auto_detect(self):
        """自动检测默认路径"""
        from src.wxapkg import get_default_packages_dir
        default_pkg = get_default_packages_dir()
        if default_pkg:
            if self._ext_path_ent.text().strip() == default_pkg:
                self._ext_refresh_apps()
            else:
                self._ext_path_ent.setText(default_pkg)
            self._ext_log(f"已自动检测到 Applet 目录: {default_pkg}")
        else:
            hint = ("~/Library/Containers/com.tencent.xinWeChat/Data/Documents/"
                    "app_data/radium/users/<微信用户ID>/applet/packages"
                    if sys.platform == "darwin" else
                    "未找到默认 Applet 目录")
            self._ext_log(f"未自动检测到目录，请手动选择。macOS 参考路径: {hint}"
                          if sys.platform == "darwin" else
                          f"{hint}，请手动选择")

    def _ext_auto_process_new(self, new_ids):
        """对新增的小程序自动执行反编译/扫描（按开关状态）"""
        if not self._tog_auto_dec.isChecked() and not self._tog_auto_scan.isChecked():
            return
        # 如果当前已有任务在运行，排队延迟处理
        if self._ext_current_op is not None:
            QTimer.singleShot(3000, lambda ids=set(new_ids): self._ext_auto_process_new(ids))
            return
        for appid in sorted(new_ids):
            state = self._ext_app_states.get(appid, {})
            if self._tog_auto_dec.isChecked() and not state.get("decompiled", False):
                self._ext_log(f"[自动] 开始反编译: {appid}")
                self._ext_do_decompile(appid)
                return  # 一次处理一个，完成后 _handle_ext 会触发下一步
            if self._tog_auto_scan.isChecked() and state.get("decompiled", False) and not state.get("scanned", False):
                self._ext_log(f"[自动] 开始提取: {appid}")
                self._ext_do_scan(appid)
                return

    def _ext_auto_process_pending(self):
        """遍历所有已知app，对未处理的自动执行反编译/扫描"""
        if self._ext_current_op is not None:
            return
        for appid, state in self._ext_app_states.items():
            if self._tog_auto_dec.isChecked() and not state.get("decompiled", False):
                self._ext_log(f"[自动] 开始反编译: {appid}")
                self._ext_do_decompile(appid)
                return
            if self._tog_auto_scan.isChecked() and state.get("decompiled", False) and not state.get("scanned", False):
                self._ext_log(f"[自动] 开始提取: {appid}")
                self._ext_do_scan(appid)
                return

    def _ext_log(self, msg):
        c = _TH[self._tn]
        self._ext_logbox.append(f'<span style="color:{c["text2"]}">{msg}</span>')
        sb = self._ext_logbox.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _ext_get_app_name(self, appid, pkgs, output_base):
        """尝试从已解包文件中读取小程序名称"""
        app_output = os.path.join(output_base, appid)
        decompile_dir = os.path.join(app_output, "decompiled")

        # 尝试从 app-config.json 读取
        for fname in ("app-config.json", "app.json"):
            cfg_path = os.path.join(decompile_dir, fname)
            if os.path.isfile(cfg_path):
                try:
                    with open(cfg_path, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                    # 多种可能的字段
                    name = (cfg.get("window", {}).get("navigationBarTitleText", "")
                            or cfg.get("appname", "")
                            or cfg.get("entryPagePath", ""))
                    if name:
                        return f"{name}  ({len(pkgs)}pkg)"
                except Exception:
                    pass

        return f"{len(pkgs)} pkg"

    def _ext_refresh_apps(self):
        """刷新小程序列表"""
        pkg_dir = self._ext_path_ent.text().strip()
        if not pkg_dir or not os.path.isdir(pkg_dir):
            return

        # 清除旧列表
        while self._ext_list_layout.count() > 1:  # 保留 stretch
            item = self._ext_list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._ext_app_widgets.clear()

        # 扫描目录
        try:
            from src.wxapkg import find_wxapkg_files
            all_pkgs = find_wxapkg_files(pkg_dir)
        except Exception as e:
            self._ext_log(f"扫描目录失败: {e}")
            return

        # 按 appid 分组
        appid_groups = {}
        for pkg in all_pkgs:
            appid_groups.setdefault(pkg["appid"], []).append(pkg)

        if not appid_groups:
            self._ext_status_lbl.setText("未找到小程序")
            return

        c = _TH[self._tn]
        output_base = os.path.join(_BASE_DIR, "output")

        # 按最新包文件的修改时间排序，最旧的先插入，最新的最后插入到位置0因此显示在最上面
        def _appid_mtime(item):
            _, pkgs = item
            return max((os.path.getmtime(p["path"]) for p in pkgs if os.path.exists(p["path"])), default=0)

        for appid, pkgs in sorted(appid_groups.items(), key=_appid_mtime):
            row = QFrame()
            row.setStyleSheet(
                f"QFrame {{ background: {c['input']}; border-radius: 8px; }}"
                f"QFrame QLabel {{ background: transparent; }}")
            row_lay = QHBoxLayout(row)
            row_lay.setContentsMargins(12, 6, 12, 6)
            row_lay.setSpacing(6)

            lbl_id = QLabel(appid)
            lbl_id.setFixedWidth(180)
            lbl_id.setFont(_qfm())
            lbl_id.setStyleSheet(f"color: {c['text1']};")
            row_lay.addWidget(lbl_id)

            # 检查是否已解包
            app_output = os.path.join(output_base, appid)
            decompile_dir = os.path.join(app_output, "decompiled")
            result_dir = os.path.join(app_output, "result")
            is_decompiled = os.path.isdir(decompile_dir) and any(
                f.endswith(('.js', '.html', '.htm'))
                for _, _, files in os.walk(decompile_dir) for f in files
            ) if os.path.isdir(decompile_dir) else False
            is_scanned = os.path.isfile(os.path.join(result_dir, "report.json"))

            # 尝试读取小程序名称
            app_name = self._ext_get_app_name(appid, pkgs, output_base) if is_decompiled else f"{len(pkgs)} pkg (未反编译)"
            lbl_name = QLabel(app_name)
            lbl_name.setMinimumWidth(100)
            lbl_name.setFont(_qfn())
            lbl_name.setStyleSheet(f"color: {c['text2']};")
            row_lay.addWidget(lbl_name, 1)

            self._ext_app_states[appid] = {
                "decompiled": is_decompiled,
                "scanned": is_scanned,
                "packages": pkgs,
                "decompile_dir": decompile_dir,
                "result_dir": result_dir,
            }

            # 按钮
            btn_dec = QPushButton("反编译")
            btn_dec.setFixedWidth(60)
            btn_dec.clicked.connect(lambda _, a=appid: self._ext_do_decompile(a))
            if is_decompiled:
                btn_dec.setStyleSheet(
                    f"QPushButton {{ background: {c['success']}; color: #111; border-radius: 6px; padding: 4px 8px; font-size: 9px; }}")
            row_lay.addWidget(btn_dec)

            btn_scan = QPushButton("提取")
            btn_scan.setFixedWidth(50)
            btn_scan.setEnabled(is_decompiled)
            btn_scan.clicked.connect(lambda _, a=appid: self._ext_do_scan(a))
            row_lay.addWidget(btn_scan)

            btn_view = QPushButton("查看")
            btn_view.setFixedWidth(50)
            btn_view.setEnabled(is_scanned)
            btn_view.clicked.connect(lambda _, a=appid: self._ext_view_results(a))
            row_lay.addWidget(btn_view)

            btn_del = QPushButton("删除")
            btn_del.setFixedWidth(50)
            btn_del.clicked.connect(lambda _, a=appid: self._ext_delete_app(a))
            btn_del.setStyleSheet(
                f"QPushButton {{ background: {c['error']}; color: #fff; border-radius: 6px; padding: 4px 8px; font-size: 9px; }}"
                f"QPushButton:hover {{ background: #dc2626; }}")
            row_lay.addWidget(btn_del)

            self._ext_app_widgets[appid] = {
                "row": row, "btn_dec": btn_dec, "btn_scan": btn_scan,
                "btn_view": btn_view, "btn_del": btn_del,
                "lbl_name": lbl_name, "lbl_id": lbl_id,
            }

            # 插入在最前面（最新的在上面）
            self._ext_list_layout.insertWidget(0, row)

        self._ext_status_lbl.setText(f"发现 {len(appid_groups)} 个小程序")
        # 记录当前已知 appid 集合 (供目录监控用)
        self._ext_last_appids = set(appid_groups.keys())

    def _ext_update_app_buttons(self, appid):
        """更新指定 app 的按钮状态"""
        state = self._ext_app_states.get(appid, {})
        widgets = self._ext_app_widgets.get(appid, {})
        if not widgets:
            return
        c = _TH[self._tn]
        is_dec = state.get("decompiled", False)
        is_scanned = state.get("scanned", False)

        btn_dec = widgets["btn_dec"]
        if is_dec:
            btn_dec.setStyleSheet(
                f"QPushButton {{ background: {c['success']}; color: #111; border-radius: 6px; padding: 4px 8px; font-size: 9px; }}")
        else:
            btn_dec.setStyleSheet("")

        widgets["btn_scan"].setEnabled(is_dec)
        widgets["btn_view"].setEnabled(is_scanned)

    # ============================================
    # 提取页 - 反编译
    # ============================================

    def _ext_do_decompile(self, appid):
        if self._ext_proc:
            self._ext_log("有任务正在运行，请等待完成")
            return

        output_base = os.path.join(_BASE_DIR, "output")
        app_output = os.path.join(output_base, appid)
        os.makedirs(app_output, exist_ok=True)

        pkg_dir = self._ext_path_ent.text().strip()
        worker_path = os.path.join(_BASE_DIR, "src", "extract_worker.py")
        cmd = [
            sys.executable, worker_path, "decompile",
            "--packages-dir", pkg_dir,
            "--appid", appid,
            "--output-dir", app_output,
        ]

        self._ext_log(f"开始反编译: {appid}")
        self._ext_prog.setValue(0)
        self._ext_status_lbl.setText(f"正在反编译 {appid}...")
        self._ext_current_op = ("decompile", appid)

        try:
            self._ext_proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
        except Exception as e:
            self._ext_log(f"启动失败: {e}")
            return

        self._ext_thread = threading.Thread(target=self._ext_reader, daemon=True)
        self._ext_thread.start()

    # ============================================
    # 提取页 - 敏感信息扫描
    # ============================================

    def _ext_do_scan(self, appid):
        if self._ext_proc:
            self._ext_log("有任务正在运行，请等待完成")
            return

        state = self._ext_app_states.get(appid, {})
        if not state.get("decompiled"):
            self._ext_log(f"请先反编译 {appid}")
            return

        output_base = os.path.join(_BASE_DIR, "output")
        app_output = os.path.join(output_base, appid)
        decompile_dir = state.get("decompile_dir", os.path.join(app_output, "decompiled"))
        result_dir = os.path.join(app_output, "result")
        os.makedirs(result_dir, exist_ok=True)

        # 保存自定义正则
        custom_file = ""
        if self._ext_custom_patterns:
            custom_file = os.path.join(_BASE_DIR, ".extract_custom_patterns.json")
            with open(custom_file, "w", encoding="utf-8") as f:
                json.dump(self._ext_custom_patterns, f, ensure_ascii=False)

        worker_path = os.path.join(_BASE_DIR, "src", "extract_worker.py")
        cmd = [
            sys.executable, worker_path, "scan",
            "--scan-dir", decompile_dir,
            "--output-dir", result_dir,
        ]
        if custom_file:
            cmd += ["--custom-patterns", custom_file]

        self._ext_log(f"开始提取敏感信息: {appid}")
        self._ext_prog.setValue(0)
        self._ext_status_lbl.setText(f"正在扫描 {appid}...")
        self._ext_current_op = ("scan", appid)

        try:
            self._ext_proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
        except Exception as e:
            self._ext_log(f"启动失败: {e}")
            return

        self._ext_thread = threading.Thread(target=self._ext_reader, daemon=True)
        self._ext_thread.start()

    # ============================================
    # 提取页 - 子进程通信
    # ============================================

    def _ext_reader(self):
        """后台线程读取子进程 stdout"""
        proc = self._ext_proc
        if not proc or not proc.stdout:
            return
        try:
            for line in proc.stdout:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    self._ext_q.put(obj)
                except json.JSONDecodeError:
                    self._ext_q.put({"type": "log", "msg": line})
        except Exception:
            pass
        finally:
            proc.wait()
            stderr_out = ""
            if proc.stderr:
                try:
                    stderr_out = proc.stderr.read()
                except Exception:
                    pass
            if stderr_out:
                self._ext_q.put({"type": "log", "msg": f"[stderr] {stderr_out[:500]}"})
            self._ext_q.put({"type": "__done__", "returncode": proc.returncode})

    # ============================================
    # 提取页 - 查看结果
    # ============================================

    def _ext_view_results(self, appid):
        """查看敏感信息子页面 — 双列布局，仿 HTML 报告样式"""
        state = self._ext_app_states.get(appid, {})
        result_dir = state.get("result_dir", "")
        json_path = os.path.join(result_dir, "report.json")
        html_path = os.path.join(result_dir, "report.html")

        if not os.path.isfile(json_path):
            self._ext_log(f"未找到 {appid} 的扫描结果")
            return

        self._ext_current_html = html_path
        self._ext_current_json = json_path
        self._ext_view_title.setText(f"查看敏感信息 - {appid}")

        # 清除旧内容
        layout = self._ext_view_top_layout
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
            elif item.layout():
                # 递归删除子布局
                sub = item.layout()
                while sub.count():
                    si = sub.takeAt(0)
                    sw = si.widget()
                    if sw:
                        sw.deleteLater()

        # 加载 JSON 数据
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            self._ext_log(f"加载结果失败: {e}")
            return

        c = _TH[self._tn]
        accent = c["accent"]  # 绿色

        cat_labels = {
            'ip': 'IP', 'ip_port': 'IP:PORT', 'domain': '域名',
            'sfz': '身份证', 'mobile': '手机号', 'mail': '邮箱',
            'jwt': 'JWT', 'algorithm': '加密算法', 'secret': 'Secret/密钥',
            'path': 'Path', 'incomplete_path': 'IncompletePath',
            'url': 'URL', 'static': 'StaticUrl'
        }
        # 反向映射: 中文标签 → 内置key
        label_to_key = {v: k for k, v in cat_labels.items()}

        left_cats = ['ip', 'ip_port', 'domain', 'sfz', 'mobile', 'mail', 'jwt', 'algorithm', 'secret']
        right_cats = ['path', 'incomplete_path', 'url', 'static']
        all_builtin = set(left_cats + right_cats)

        # 合并自定义结果到同名内置分类，去重
        merged_data = {}
        custom_only_keys = []
        for k, v in data.items():
            if k == "_meta":
                continue
            items = v if isinstance(v, list) else []
            if k in all_builtin:
                merged_data.setdefault(k, []).extend(items)
            elif k in label_to_key:
                # 自定义名称和内置中文标签相同，合并到内置分类
                builtin_key = label_to_key[k]
                merged_data.setdefault(builtin_key, []).extend(items)
            else:
                merged_data.setdefault(k, []).extend(items)
                if k not in all_builtin:
                    custom_only_keys.append(k)

        # 去重
        for k in merged_data:
            seen = set()
            deduped = []
            for item in merged_data[k]:
                s = str(item)
                if s not in seen:
                    seen.add(s)
                    deduped.append(item)
            merged_data[k] = deduped

        def _build_cat_widget(key, label, items):
            """构建单个分类的 widget — 支持展开/折叠"""
            w = QWidget()
            lay = QVBoxLayout(w)
            lay.setContentsMargins(0, 8, 0, 4)
            lay.setSpacing(2)

            # 标题行: ▶ 分类名 (数量)   [复制]
            title_row = QHBoxLayout()
            title_row.setContentsMargins(0, 0, 0, 0)

            # 展开/折叠按钮
            btn_fold = QPushButton("▼")
            btn_fold.setFixedSize(20, 20)
            btn_fold.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_fold.setStyleSheet(
                f"QPushButton {{ background: transparent; color: {c['text3']}; border: none;"
                f"font-size: 10px; padding: 0; }}"
                f"QPushButton:hover {{ color: {c['text1']}; }}")
            title_row.addWidget(btn_fold)

            title_lbl = QLabel(f"{label} ({len(items)})")
            title_lbl.setFont(_qfn(2, QFont.Weight.Bold))
            title_lbl.setStyleSheet(
                f"color: {c['text1']}; border-left: 4px solid {accent}; padding-left: 8px;"
                f"background: transparent;")
            title_row.addWidget(title_lbl)
            title_row.addStretch()

            btn_copy = QPushButton("复制")
            btn_copy.setFixedSize(48, 26)
            btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_copy.setStyleSheet(
                f"QPushButton {{ background: {c['input']}; color: {accent}; border: 1px solid {accent};"
                f"border-radius: 4px; font-size: 11px; padding: 2px 8px; }}"
                f"QPushButton:hover {{ background: {accent}; color: #111; }}")
            copy_text = "\n".join(str(i) for i in items)
            btn_copy.clicked.connect(lambda _, t=copy_text, b=btn_copy: self._ext_copy_cat(t, b))
            title_row.addWidget(btn_copy)
            lay.addLayout(title_row)

            # 内容区域（可折叠）
            content_widget = QWidget()
            content_lay = QVBoxLayout(content_widget)
            content_lay.setContentsMargins(0, 0, 0, 0)
            content_lay.setSpacing(0)
            if items:
                content_lbl = QLabel()
                content_lbl.setFont(_qfm())
                content_lbl.setWordWrap(True)
                content_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                content_lbl.setStyleSheet(
                    f"color: {c['text2']}; padding-left: 14px; background: transparent;")
                display_items = items[:200]
                lines = [str(i) for i in display_items]
                if len(items) > 200:
                    lines.append(f"... 共 {len(items)} 条，仅显示前 200 条")
                content_lbl.setText("\n".join(lines))
                content_lay.addWidget(content_lbl)
            lay.addWidget(content_widget)

            # 展开/折叠逻辑 — 默认展开
            def toggle_fold():
                visible = content_widget.isVisible()
                content_widget.setVisible(not visible)
                btn_fold.setText("▶" if visible else "▼")

            btn_fold.clicked.connect(toggle_fold)

            return w

        # === 双列布局 ===
        cols_widget = QWidget()
        cols_layout = QHBoxLayout(cols_widget)
        cols_layout.setContentsMargins(0, 0, 0, 0)
        cols_layout.setSpacing(16)

        # 左列
        left_col = QWidget()
        left_lay = QVBoxLayout(left_col)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_lay.setSpacing(0)
        for cat in left_cats:
            label = cat_labels.get(cat, cat)
            items = merged_data.get(cat, [])
            left_lay.addWidget(_build_cat_widget(cat, label, items))
        # 自定义规则(非同名)放左列底部
        for key in custom_only_keys:
            items = merged_data.get(key, [])
            left_lay.addWidget(_build_cat_widget(key, key, items))
        left_lay.addStretch()
        cols_layout.addWidget(left_col, 1)

        # 分隔线
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color: rgba(128,128,128,0.2);")
        cols_layout.addWidget(sep)

        # 右列
        right_col = QWidget()
        right_lay = QVBoxLayout(right_col)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.setSpacing(0)
        for cat in right_cats:
            label = cat_labels.get(cat, cat)
            items = merged_data.get(cat, [])
            right_lay.addWidget(_build_cat_widget(cat, label, items))
        right_lay.addStretch()
        cols_layout.addWidget(right_col, 1)

        layout.addWidget(cols_widget)
        layout.addStretch()

        # 切换到查看页
        self._ext_stack.setCurrentIndex(2)

    def _ext_copy_cat(self, text, btn):
        """复制分类内容并显示反馈"""
        QApplication.clipboard().setText(text)
        old = btn.text()
        btn.setText("✓")
        QTimer.singleShot(1200, lambda: btn.setText(old))

    def _ext_open_html(self):
        """浏览器打开 HTML 报告"""
        if self._ext_current_html and os.path.isfile(self._ext_current_html):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self._ext_current_html))
        else:
            self._ext_log("HTML 报告不存在")

    # ============================================
    # 提取页 - 删除
    # ============================================

    def _ext_delete_app(self, appid):
        """删除指定小程序的解包和结果"""
        import shutil
        output_base = os.path.join(_BASE_DIR, "output")
        app_output = os.path.join(output_base, appid)
        if os.path.isdir(app_output):
            try:
                shutil.rmtree(app_output)
                self._ext_log(f"已删除 {appid} 的数据")
            except Exception as e:
                self._ext_log(f"删除失败: {e}")

        # 更新状态
        if appid in self._ext_app_states:
            self._ext_app_states[appid]["decompiled"] = False
            self._ext_app_states[appid]["scanned"] = False
        self._ext_update_app_buttons(appid)
        # 如果开启了自动反编译，重新处理
        QTimer.singleShot(500, self._ext_auto_process_pending)

    def _ext_clear_decompiled(self):
        """清空所有解包文件"""
        import shutil
        output_base = os.path.join(_BASE_DIR, "output")
        if not os.path.isdir(output_base):
            return
        count = 0
        for appid in os.listdir(output_base):
            dec_dir = os.path.join(output_base, appid, "decompiled")
            if os.path.isdir(dec_dir):
                try:
                    shutil.rmtree(dec_dir)
                    count += 1
                except Exception:
                    pass
        self._ext_log(f"已清空 {count} 个小程序的解包文件")
        # 刷新状态（不触发自动处理，用户主动清空不应自动重跑）
        for appid in self._ext_app_states:
            self._ext_app_states[appid]["decompiled"] = False
            self._ext_app_states[appid]["scanned"] = False
            self._ext_update_app_buttons(appid)

    def _ext_clear_applet(self):
        """清空 Applet 目录"""
        import shutil
        pkg_dir = self._ext_path_ent.text().strip()
        if not pkg_dir or not os.path.isdir(pkg_dir):
            self._ext_log("Applet 目录不存在")
            return
        try:
            for entry in os.listdir(pkg_dir):
                full = os.path.join(pkg_dir, entry)
                if os.path.isdir(full):
                    shutil.rmtree(full)
            self._ext_log("已清空 Applet 目录")
            # 清空后重置已知 appid 集合，防止旧 appid 触发自动反编译
            self._ext_app_states.clear()
            self._ext_last_appids = set()
            self._ext_refresh_apps()
        except Exception as e:
            self._ext_log(f"清空失败: {e}")

    # ============================================
    # 提取页 - 正则管理
    # ============================================

    def _ext_goto_regex(self):
        self._ext_stack.setCurrentIndex(1)

    def _ext_fill_builtin_patterns(self):
        """填充内置正则到树"""
        from src.extractor import Extractor
        builtin = Extractor.get_all_builtin_patterns()
        self._ext_builtin_tree.clear()
        for name, pat in builtin.items():
            display = pat if len(pat) < 200 else pat[:200] + "..."
            item = QTreeWidgetItem([name, display])
            self._ext_builtin_tree.addTopLevelItem(item)

    def _ext_refresh_custom_patterns(self):
        """刷新自定义正则行列表 — 用 QFrame 行代替 QTableWidget"""
        lay = self._ext_pat_layout
        # 清除旧行(保留最后一个 stretch)
        while lay.count() > 1:
            item = lay.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        c = _TH[self._tn]
        for name, info in self._ext_custom_patterns.items():
            if isinstance(info, str):
                pat = info; enabled = True
            else:
                pat = info.get("regex", ""); enabled = info.get("enabled", True)
            row = QFrame()
            row.setObjectName("_ext_pat_row")
            row.setStyleSheet(
                f"QFrame#_ext_pat_row {{ background: {c['input']}; border-radius: 8px; }}"
                f"QFrame#_ext_pat_row QLabel {{ background: transparent; border: none; }}")
            row.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            row.customContextMenuRequested.connect(lambda pos, n=name: self._ext_pattern_ctx(pos, n))
            rl = QHBoxLayout(row)
            rl.setContentsMargins(12, 6, 12, 6)
            rl.setSpacing(6)
            lbl_n = QLabel(name)
            lbl_n.setFixedWidth(120)
            lbl_n.setFont(_qfm())
            lbl_n.setStyleSheet(f"color: {c['text1']};")
            rl.addWidget(lbl_n)
            lbl_p = QLabel(pat if len(pat) < 60 else pat[:60] + "...")
            lbl_p.setFont(_qfm())
            lbl_p.setStyleSheet(f"color: {c['text2']};")
            lbl_p.setToolTip(pat)
            lbl_p.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
            rl.addWidget(lbl_p, 1)
            lbl_s = QLabel("启用" if enabled else "禁用")
            lbl_s.setFixedWidth(50)
            lbl_s.setStyleSheet(f"color: {c['success'] if enabled else c['error']};")
            rl.addWidget(lbl_s)
            btn_edit = QPushButton("修改")
            btn_edit.setFixedWidth(50)
            btn_edit.clicked.connect(lambda _, n=name: self._ext_edit_pattern(n))
            rl.addWidget(btn_edit)
            btn_toggle = QPushButton("禁用" if enabled else "启用")
            btn_toggle.setFixedWidth(50)
            if enabled:
                btn_toggle.setStyleSheet(
                    f"QPushButton {{ background: {c['warning']}; color: #111; border-radius: 6px; padding: 4px 8px; font-size: 9px; }}"
                    f"QPushButton:hover {{ background: #ca8a04; }}")
            else:
                btn_toggle.setStyleSheet(
                    f"QPushButton {{ background: {c['success']}; color: #111; border-radius: 6px; padding: 4px 8px; font-size: 9px; }}")
            btn_toggle.clicked.connect(lambda _, n=name: self._ext_toggle_pattern(n))
            rl.addWidget(btn_toggle)
            btn_del = QPushButton("删除")
            btn_del.setFixedWidth(50)
            btn_del.setStyleSheet(
                f"QPushButton {{ background: {c['error']}; color: #fff; border-radius: 6px; padding: 4px 8px; font-size: 9px; }}"
                f"QPushButton:hover {{ background: #dc2626; }}")
            btn_del.clicked.connect(lambda _, n=name: self._ext_delete_pattern(n))
            rl.addWidget(btn_del)
            lay.insertWidget(lay.count() - 1, row)

    def _ext_add_pattern(self):
        """新建空白行 — 用 QLineEdit 输入"""
        c = _TH[self._tn]
        row = QFrame()
        row.setObjectName("_ext_new_row")
        row.setStyleSheet(
            f"QFrame#_ext_new_row {{ background: {c['input']}; border-radius: 8px; border: 1px solid {c['accent']}; }}"
            f"QFrame#_ext_new_row QLabel {{ background: transparent; border: none; }}"
            f"QFrame#_ext_new_row QLineEdit {{ border: 1px solid {c['border']}; border-radius: 4px; padding: 4px 6px; background: {c['card']}; color: {c['text1']}; }}")
        rl = QHBoxLayout(row)
        rl.setContentsMargins(12, 6, 12, 6)
        rl.setSpacing(6)
        ent_name = QLineEdit()
        ent_name.setPlaceholderText("栏目名...")
        ent_name.setFixedWidth(120)
        rl.addWidget(ent_name)
        ent_regex = QLineEdit()
        ent_regex.setPlaceholderText("正则表达式...")
        rl.addWidget(ent_regex, 1)
        lbl_s = QLabel("启用")
        lbl_s.setFixedWidth(50)
        rl.addWidget(lbl_s)
        btn_ok = QPushButton("确认")
        btn_ok.setFixedWidth(50)
        btn_ok.clicked.connect(lambda: self._ext_confirm_new(ent_name, ent_regex, row))
        rl.addWidget(btn_ok)
        btn_cancel = QPushButton("取消")
        btn_cancel.setFixedWidth(50)
        btn_cancel.setStyleSheet(
            f"QPushButton {{ background: {c['error']}; color: #fff; border-radius: 6px; padding: 4px 8px; font-size: 9px; }}"
            f"QPushButton:hover {{ background: #dc2626; }}")
        btn_cancel.clicked.connect(lambda: (row.deleteLater(),))
        rl.addWidget(btn_cancel)
        self._ext_pat_layout.insertWidget(self._ext_pat_layout.count() - 1, row)
        ent_name.setFocus()

    def _ext_confirm_new(self, ent_name, ent_regex, row_widget):
        """确认新建正则"""
        name = ent_name.text().strip()
        regex = ent_regex.text().strip()
        if not name or not regex:
            self._ext_log("栏目名和正则不能为空")
            return
        import re as _re
        try:
            _re.compile(regex)
        except _re.error as e:
            self._ext_log(f"正则语法错误: {e}")
            return
        self._ext_custom_patterns[name] = {"regex": regex, "enabled": True}
        row_widget.deleteLater()
        self._ext_refresh_custom_patterns()
        self._auto_save()
        self._ext_log(f"已添加规则: {name}")

    def _ext_pattern_ctx(self, pos, name):
        """右键菜单"""
        info = self._ext_custom_patterns.get(name, "")
        regex = info.get("regex", info) if isinstance(info, dict) else info
        menu = QMenu(self)
        menu.addAction("测试正则", lambda: self._ext_test_pattern(name))
        menu.addAction("复制正则", lambda: QApplication.clipboard().setText(regex))
        # 找到发送信号的 widget
        sender = self.sender()
        if sender:
            menu.exec(sender.mapToGlobal(pos))
        else:
            menu.exec(self.cursor().pos())

    def _ext_test_pattern(self, name):
        """弹窗测试正则"""
        info = self._ext_custom_patterns.get(name, "")
        regex = info.get("regex", info) if isinstance(info, dict) else info
        import re as _re
        c = _TH[self._tn]

        dlg = QDialog(self)
        dlg.setWindowTitle(f"测试正则 - {name}")
        dlg.resize(600, 400)
        dlg.setStyleSheet(f"""
            QDialog {{ background: {c['bg']}; color: {c['text1']}; }}
            QLabel {{ color: {c['text2']}; background: transparent; }}
            QTextEdit {{
                background: {c['input']}; color: {c['text1']};
                border: 1px solid {c['border']}; border-radius: 8px;
                padding: 6px; font-family: {_FM};
            }}
            QPushButton {{
                background: {c['accent']}; color: #111;
                border-radius: 8px; padding: 8px 16px; font-size: 13px;
            }}
            QPushButton:hover {{ background: {c['accent2']}; }}
        """)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(8)

        lay.addWidget(QLabel(f"正则: {regex}"))

        input_lbl = QLabel("输入测试文本:")
        lay.addWidget(input_lbl)
        input_box = QTextEdit()
        input_box.setFont(_qfm())
        input_box.setPlaceholderText("在此粘贴或输入要测试的文本...")
        lay.addWidget(input_box, 1)

        result_lbl = QLabel("匹配结果:")
        lay.addWidget(result_lbl)
        result_box = QTextEdit()
        result_box.setReadOnly(True)
        result_box.setFont(_qfm())
        lay.addWidget(result_box, 1)

        def do_test():
            text = input_box.toPlainText()
            try:
                pat = _re.compile(regex, _re.IGNORECASE)
                matches = pat.findall(text)
                if matches:
                    if isinstance(matches[0], tuple):
                        matches = [m.group(0) for m in pat.finditer(text)]
                    result_box.setPlainText(f"找到 {len(matches)} 个匹配:\n" + "\n".join(str(m) for m in matches))
                else:
                    result_box.setPlainText("无匹配")
            except _re.error as e:
                result_box.setPlainText(f"正则错误: {e}")

        btn_test = QPushButton("测试")
        btn_test.clicked.connect(do_test)
        lay.addWidget(btn_test)
        dlg.exec()

    def _ext_edit_pattern(self, name):
        """编辑正则 — 替换该行为可编辑的 QLineEdit 行"""
        info = self._ext_custom_patterns.get(name, "")
        if isinstance(info, str):
            pat = info; enabled = True
        else:
            pat = info.get("regex", ""); enabled = info.get("enabled", True)
        c = _TH[self._tn]
        # 找到并删除原行
        lay = self._ext_pat_layout
        idx = -1
        for i in range(lay.count()):
            w = lay.itemAt(i).widget()
            if w:
                rl = w.layout()
                if rl and rl.count() > 0:
                    first = rl.itemAt(0).widget()
                    if isinstance(first, QLabel) and first.text() == name:
                        idx = i
                        w.deleteLater()
                        break
        if idx < 0:
            idx = lay.count() - 1  # before stretch
        # 创建编辑行
        row = QFrame()
        row.setObjectName("_ext_edit_row")
        row.setStyleSheet(
            f"QFrame#_ext_edit_row {{ background: {c['input']}; border-radius: 8px; border: 1px solid {c['accent']}; }}"
            f"QFrame#_ext_edit_row QLabel {{ background: transparent; border: none; }}"
            f"QFrame#_ext_edit_row QLineEdit {{ border: 1px solid {c['border']}; border-radius: 4px; padding: 4px 6px; background: {c['card']}; color: {c['text1']}; }}")
        rl = QHBoxLayout(row)
        rl.setContentsMargins(12, 6, 12, 6)
        rl.setSpacing(6)
        ent_name = QLineEdit(name)
        ent_name.setFixedWidth(120)
        rl.addWidget(ent_name)
        ent_regex = QLineEdit(pat)
        rl.addWidget(ent_regex, 1)
        lbl_s = QLabel("启用" if enabled else "禁用")
        lbl_s.setFixedWidth(50)
        rl.addWidget(lbl_s)
        btn_save = QPushButton("保存")
        btn_save.setFixedWidth(50)
        btn_save.clicked.connect(lambda: self._ext_save_edit(name, ent_name, ent_regex, enabled, row))
        rl.addWidget(btn_save)
        btn_cancel = QPushButton("取消")
        btn_cancel.setFixedWidth(50)
        btn_cancel.setStyleSheet(
            f"QPushButton {{ background: {c['error']}; color: #fff; border-radius: 6px; padding: 4px 8px; font-size: 9px; }}"
            f"QPushButton:hover {{ background: #dc2626; }}")
        btn_cancel.clicked.connect(lambda: (row.deleteLater(), self._ext_refresh_custom_patterns()))
        rl.addWidget(btn_cancel)
        lay.insertWidget(idx, row)
        ent_name.setFocus()

    def _ext_save_edit(self, old_name, ent_name, ent_regex, enabled, row_widget):
        """保存编辑后的正则"""
        new_name = ent_name.text().strip()
        new_regex = ent_regex.text().strip()
        if not new_name or not new_regex:
            self._ext_log("栏目名和正则不能为空")
            return
        import re as _re
        try:
            _re.compile(new_regex)
        except _re.error as e:
            self._ext_log(f"正则语法错误: {e}")
            return
        self._ext_custom_patterns.pop(old_name, None)
        self._ext_custom_patterns[new_name] = {"regex": new_regex, "enabled": enabled}
        row_widget.deleteLater()
        self._ext_refresh_custom_patterns()
        self._auto_save()
        self._ext_log(f"已保存规则: {new_name}")

    def _ext_toggle_pattern(self, name):
        """切换正则启用/禁用"""
        info = self._ext_custom_patterns.get(name, "")
        if isinstance(info, str):
            self._ext_custom_patterns[name] = {"regex": info, "enabled": False}
        else:
            info["enabled"] = not info.get("enabled", True)
        self._ext_refresh_custom_patterns()
        self._auto_save()

    def _ext_delete_pattern(self, name):
        self._ext_custom_patterns.pop(name, None)
        self._ext_refresh_custom_patterns()
        self._auto_save()
        self._ext_log(f"已删除规则: {name}")

    # ── 调试开关 (vConsole) ──

    def _build_vconsole(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(24, 12, 24, 16)
        lay.setSpacing(10)
        lay.setAlignment(Qt.AlignTop)

        # 风险警告卡片
        warn_card = _make_card()
        warn_lay = QVBoxLayout(warn_card)
        warn_lay.setContentsMargins(16, 12, 16, 12)
        warn_lay.setSpacing(6)
        warn_title = QLabel("⚠  风险提示")
        warn_title.setFont(_qfn(2, QFont.Bold))
        warn_title.setStyleSheet("color: #e6a23c;")
        warn_lay.addWidget(warn_title)
        warn_text = QLabel(
            "非正规开启小程序调试有封号风险。测试需谨慎！\n"
            "请勿在主力账号上使用，建议使用测试号操作。")
        warn_text.setWordWrap(True)
        warn_text.setStyleSheet("color: #e6a23c; font-size: 12px;")
        warn_lay.addWidget(warn_text)
        lay.addWidget(warn_card)

        # 功能说明卡片
        info_card = _make_card()
        info_lay = QVBoxLayout(info_card)
        info_lay.setContentsMargins(16, 12, 16, 12)
        info_lay.setSpacing(6)
        info_lay.addWidget(_make_label("功能说明", bold=True))
        desc = QLabel(
            "通过官方 API wx.setEnableDebug 开启小程序内置的 vConsole 调试面板。\n\n"
            "开启后可以：\n"
            "  •  在小程序内直接执行 JS 代码\n"
            "  •  调用 wx.cloud.callFunction 调试云函数\n\n"
            "关闭后重启小程序即可恢复正常。")
        desc.setWordWrap(True)
        desc.setProperty("class", "muted")
        info_lay.addWidget(desc)
        ref_lbl = QLabel(
            '学习文档: <a href="https://mp.weixin.qq.com/s/hTlekrCPiMJCvsHYx7CAxw">'
            '微信公众号文档</a>')
        ref_lbl.setOpenExternalLinks(True)
        ref_lbl.setStyleSheet("font-size: 11px;")
        info_lay.addWidget(ref_lbl)
        lay.addWidget(info_card)

        # 操作卡片
        op_card = _make_card()
        op_lay = QVBoxLayout(op_card)
        op_lay.setContentsMargins(16, 12, 16, 12)
        op_lay.setSpacing(8)
        op_lay.addWidget(_make_label("操作", bold=True))

        btn_row = QHBoxLayout()
        self._btn_vc_enable = _make_btn("▶  开启调试", self._do_vc_enable)
        self._btn_vc_enable.setFont(_qfn(1, QFont.Bold))
        self._btn_vc_enable.setEnabled(False)
        btn_row.addWidget(self._btn_vc_enable)
        self._btn_vc_disable = _make_btn("■  关闭调试", self._do_vc_disable)
        self._btn_vc_disable.setFont(_qfn(1, QFont.Bold))
        self._btn_vc_disable.setEnabled(False)
        btn_row.addWidget(self._btn_vc_disable)
        btn_row.addStretch()
        op_lay.addLayout(btn_row)

        self._vc_status_lbl = QLabel("状态: 未连接小程序")
        self._vc_status_lbl.setProperty("class", "muted")
        op_lay.addWidget(self._vc_status_lbl)
        lay.addWidget(op_card)

        lay.addStretch()

        self._stack.addWidget(page)
        self._page_map["vconsole"] = self._stack.count() - 1

    def _do_vc_enable(self):
        if not self._engine or not self._loop or not self._loop.is_running():
            self._log_add("error", "[调试] 请先启动调试并连接小程序")
            return
        from PySide6.QtWidgets import QMessageBox
        r = QMessageBox.warning(
            self, "风险确认",
            "非正规开启小程序调试有封号风险。\n测试需谨慎！\n\n确定要开启吗？",
            QMessageBox.Ok | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )
        if r != QMessageBox.Ok:
            return
        self._btn_vc_enable.setEnabled(False)
        asyncio.run_coroutine_threadsafe(self._avc_set_debug(True), self._loop)

    def _do_vc_disable(self):
        if not self._engine or not self._loop or not self._loop.is_running():
            self._log_add("error", "[调试] 请先启动调试并连接小程序")
            return
        self._btn_vc_disable.setEnabled(False)
        asyncio.run_coroutine_threadsafe(self._avc_set_debug(False), self._loop)

    async def _avc_set_debug(self, enable):
        try:
            val = "true" if enable else "false"
            # 先确保 navigator 已注入，通过 wxFrame.wx 调用避免超时
            await self._navigator._ensure(force=True)
            result = await self._engine.evaluate_js(
                "(function(){"
                "try{"
                "var nav=window.nav;"
                "if(!nav||!nav.wxFrame||!nav.wxFrame.wx)return JSON.stringify({err:'no wxFrame'});"
                f"nav.wxFrame.wx.setEnableDebug({{enableDebug:{val},"
                "success:function(){console.log('[First] setEnableDebug success')},"
                "fail:function(e){console.error('[First] setEnableDebug fail',e)}"
                "});"
                "return JSON.stringify({ok:true})"
                "}catch(e){return JSON.stringify({err:e.message})}"
                "})()",
                timeout=5.0,
            )
            value = None
            if result:
                r = result.get("result", {})
                inner = r.get("result", {})
                value = inner.get("value")
            if value:
                import json as _json
                info = _json.loads(value)
                if info.get("err"):
                    raise RuntimeError(info["err"])
            state = "已开启" if enable else "已关闭"
            self._rte_q.put(("__vc__", enable, True))
            self._log_q.put(("info", f"[调试] vConsole {state}"))
        except Exception as e:
            self._rte_q.put(("__vc__", enable, False))
            self._log_q.put(("error", f"[调试] 操作失败: {e}"))

    async def _avc_detect_debug(self):
        """自动检测小程序是否已开启 vConsole 调试。"""
        try:
            await self._navigator._ensure(force=True)
            result = await self._engine.evaluate_js(
                "(function(){"
                "try{"
                "var f=window.nav&&window.nav.wxFrame?window.nav.wxFrame:window;"
                "var c=f.__wxConfig||{};"
                "var d=!!c.debug;"
                "var v=!!(f.document&&f.document.getElementById('__vconsole'));"
                "return JSON.stringify({debug:d,vconsole:v})"
                "}catch(e){return JSON.stringify({err:e.message})}"
                "})()",
                timeout=5.0,
            )
            value = None
            if result:
                r = result.get("result", {})
                inner = r.get("result", {})
                value = inner.get("value")
            if value:
                info = json.loads(value)
                if info.get("err"):
                    return
                is_debug = info.get("debug", False) or info.get("vconsole", False)
                self._rte_q.put(("__vc_detect__", is_debug))
        except Exception:
            pass

    # ── 日志 ──

    def _build_logs(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(24, 12, 24, 16)
        lay.setSpacing(10)

        # 调试选项卡片
        dc = _make_card()
        dc_lay = QVBoxLayout(dc)
        dc_lay.setContentsMargins(16, 10, 16, 10)
        dc_lay.setSpacing(6)
        dc_lay.addWidget(_make_label("调试选项", bold=True))
        warn_lbl = QLabel("⚠ 开启后可能导致小程序卡死，请谨慎使用")
        warn_lbl.setStyleSheet("color: #fbbf24; font-size: 9px;")
        dc_lay.addWidget(warn_lbl)
        chkr = QHBoxLayout()
        self._tog_dm = ToggleSwitch(self._cfg.get("debug_main", False))
        self._tog_dm.toggled.connect(lambda v: self._auto_save())
        chkr.addWidget(self._tog_dm)
        chkr.addWidget(QLabel("调试主包"))
        chkr.addSpacing(24)
        self._tog_df = ToggleSwitch(self._cfg.get("debug_frida", False))
        self._tog_df.toggled.connect(lambda v: self._auto_save())
        chkr.addWidget(self._tog_df)
        chkr.addWidget(QLabel("调试 Frida"))
        chkr.addStretch()
        dc_lay.addLayout(chkr)
        lay.addWidget(dc)

        hdr = QHBoxLayout()
        hdr.addWidget(_make_label("日志输出", bold=True))
        hdr.addStretch()
        self._btn_clear = _make_btn("清空", self._do_clear)
        hdr.addWidget(self._btn_clear)
        lay.addLayout(hdr)

        lc = _make_card()
        lc_lay = QVBoxLayout(lc)
        lc_lay.setContentsMargins(0, 0, 0, 0)
        self._logbox = QTextEdit()
        self._logbox.setReadOnly(True)
        self._logbox.setFont(_qfm())
        lc_lay.addWidget(self._logbox)
        lay.addWidget(lc, 1)

        self._stack.addWidget(page)
        self._page_map["logs"] = self._stack.count() - 1

    # ──────────────────────────────────
    #  页面切换
    # ──────────────────────────────────

    def _show(self, pid):
        self._pg = pid
        idx = self._page_map.get(pid, 0)
        self._stack.setCurrentIndexAnimated(idx)
        titles = {k: n for k, _, n in _MENU}
        self._hdr_title.setText(titles.get(pid, ""))
        self._hl_sb()

    def _hl_sb(self):
        for pid, (fr, ic, nm) in self._sb_items.items():
            if pid == self._pg:
                fr.setProperty("class", "sb_item_active")
            else:
                fr.setProperty("class", "sb_item")
            fr.style().unpolish(fr)
            fr.style().polish(fr)
            ic.style().unpolish(ic)
            ic.style().polish(ic)
            nm.style().unpolish(nm)
            nm.style().polish(nm)

    # ──────────────────────────────────
    #  主题
    # ──────────────────────────────────

    def _toggle_theme(self):
        self._tn = "light" if self._tn == "dark" else "dark"
        self.setStyleSheet(build_qss(self._tn))
        self._update_theme_label()
        self._update_toggle_colors()
        self._refresh_sb_app_card()
        self._ext_restyle_rows()
        self._ext_refresh_custom_patterns()
        self._hl_sb()
        self._auto_save()

    def _ext_restyle_rows(self):
        """切换主题时更新应用列表行的内联样式。"""
        c = _TH[self._tn]
        row_ss = (
            f"QFrame {{ background: {c['input']}; border-radius: 8px; }}"
            f"QFrame QLabel {{ background: transparent; }}"
        )
        for appid, widgets in self._ext_app_widgets.items():
            row = widgets.get("row")
            if row:
                row.setStyleSheet(row_ss)
            lbl_id = widgets.get("lbl_id")
            if lbl_id:
                lbl_id.setStyleSheet(f"color: {c['text1']};")
            lbl_name = widgets.get("lbl_name")
            if lbl_name:
                lbl_name.setStyleSheet(f"color: {c['text2']};")
            # 反编译按钮颜色也跟主题走
            btn_dec = widgets.get("btn_dec")
            if btn_dec:
                state = self._ext_app_states.get(appid, {})
                if state.get("decompiled"):
                    btn_dec.setStyleSheet(
                        f"QPushButton {{ background: {c['success']}; color: #111; "
                        f"border-radius: 6px; padding: 4px 8px; font-size: 9px; }}")

    def _update_theme_label(self):
        txt = "☀  浅色模式" if self._tn == "dark" else "☽  深色模式"
        self._sb_theme.setText(txt)

    def _update_toggle_colors(self):
        c = _TH[self._tn]
        for tog in (self._tog_dm, self._tog_df, self._tog_auto_dec, self._tog_auto_scan):
            tog.set_colors(c["accent"], c["text4"])

    def _refresh_sb_app_card(self):
        """主题切换时刷新侧栏小程序卡片颜色。"""
        c = _TH[self._tn]
        if self._sb_app_id.isVisible():
            self._sb_app_name.setStyleSheet(f"color: {c['success']};")
            self._sb_app_id.setStyleSheet(f"color: {c['success']};")
        else:
            self._sb_app_name.setStyleSheet(f"color: {c['text3']};")

    def _auto_save(self):
        data = {
            "theme": self._tn,
            "cdp_port": self._cp_ent.text(),
            "debug_main": self._tog_dm.isChecked(),
            "debug_frida": self._tog_df.isChecked(),
            "extract_packages_dir": self._ext_path_ent.text(),
            "extract_custom_patterns": dict(self._ext_custom_patterns),
            "auto_decompile": self._tog_auto_dec.isChecked(),
            "auto_scan": self._tog_auto_scan.isChecked(),
            "global_hook_scripts": list(self._global_hook_scripts),
            "font_ui": _FN,
            "font_ui_size": _FN_SIZE,
            "font_mono": _FM,
            "font_mono_size": _FM_SIZE,
        }
        _save_cfg(data)

    # ──────────────────────────────────
    #  业务
    # ──────────────────────────────────

    def _copy_devtools_url(self):
        url = self._devtools_lbl.text()
        if url:
            QApplication.clipboard().setText(url)
            c = _TH[self._tn]
            self._devtools_copy_hint.setText("已复制!")
            self._devtools_copy_hint.setStyleSheet(f"color: {c['success']};")
            QTimer.singleShot(1500, lambda: (
                self._devtools_copy_hint.setText("点击复制"),
                self._devtools_copy_hint.setStyleSheet(f"color: {c['text3']};")
            ))
            self._log_add("info", "[gui] DevTools 链接已复制到剪贴板")

    def _do_clear(self):
        self._logbox.clear()

    _LOG_MAX_BLOCKS = 500  # 最多保留的日志行数

    def _log_add(self, lv, txt):
        c = _TH[self._tn]
        color_map = {
            "info": c["text2"],
            "error": c["error"],
            "debug": c["text3"],
            "frida": c["accent"],
            "warn": c["warning"],
        }
        color = color_map.get(lv, c["text2"])
        self._logbox.append(f'<span style="color:{color}">{txt}</span>')
        # 限制日志行数，防止 QTextEdit 内容过多导致 UI 卡顿
        doc = self._logbox.document()
        overflow = doc.blockCount() - self._LOG_MAX_BLOCKS
        if overflow > 50:  # 攒够 50 行再批量删，减少操作频率
            cursor = self._logbox.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            for _ in range(overflow):
                cursor.movePosition(cursor.MoveOperation.Down, cursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()
            cursor.deleteChar()  # 删掉残留空行
        sb = self._logbox.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _do_start(self):
        if self._running:
            return
        try:
            cp = int(self._cp_ent.text())
        except ValueError:
            self._log_add("error", "[gui] 端口号无效")
            return
        opts = CliOptions(
            cdp_port=cp,
            debug_main=self._tog_dm.isChecked(),
            debug_frida=self._tog_df.isChecked(),
            scripts_dir="",
            script_files=[])
        logger = Logger(opts)
        logger.set_output_callback(lambda lv, tx: self._log_q.put((lv, tx)))
        self._engine = DebugEngine(opts, logger)
        self._navigator = MiniProgramNavigator(self._engine)
        self._auditor = CloudAuditor(self._engine)
        self._engine.on_status_change(lambda s: self._sts_q.put(s))
        self._loop = asyncio.new_event_loop()
        self._loop_th = threading.Thread(
            target=lambda: (asyncio.set_event_loop(self._loop), self._loop.run_forever()),
            daemon=True)
        self._loop_th.start()
        asyncio.run_coroutine_threadsafe(self._astart(), self._loop)
        self._running = True
        self._btn_start.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._btn_fetch.setEnabled(True)
        url = f"devtools://devtools/bundled/inspector.html?ws=127.0.0.1:{cp}"
        self._devtools_lbl.setText(url)
        c = _TH[self._tn]
        self._devtools_copy_hint.setText("点击复制")
        self._devtools_copy_hint.setStyleSheet(f"color: {c['text3']};")
        self._log_add("info", f"[gui] 浏览器访问: {url}")

    async def _astart(self):
        try:
            await self._engine.start()
        except Exception as e:
            self._log_q.put(("error", f"[gui] 启动失败: {e}"))
            QTimer.singleShot(0, self._on_fail)

    def _on_fail(self):
        self._running = False
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._btn_fetch.setEnabled(False)
        self._nav_btns(False)
        self._targets_btns(False)
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)

    def _do_stop(self):
        if not self._running:
            return
        self._running = False
        self._poll_route_stop()
        if self._cloud_scan_active:
            self._cloud_scan_active = False
            if self._cloud_scan_poll_timer:
                self._cloud_scan_poll_timer.stop()
                self._cloud_scan_poll_timer = None
        if self._wxapi_active:
            self._wxapi_active = False
            if self._wxapi_poll_timer:
                self._wxapi_poll_timer.stop()
                self._wxapi_poll_timer = None
        if self._cancel_ev:
            self._cancel_ev.set()
        if self._engine and self._loop and self._loop.is_running():
            fut = asyncio.run_coroutine_threadsafe(self._engine.stop(), self._loop)
            fut.add_done_callback(lambda _: self._loop.call_soon_threadsafe(self._loop.stop))
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._btn_fetch.setEnabled(False)
        self._nav_btns(False)
        self._targets_btns(False)
        self._btn_autostop.setEnabled(False)
        self._redirect_guard_on = False
        self._guard_switch.setChecked(False)
        self._guard_label.setText("防跳转: 关闭")
        self._targets_tree.clear()
        self._targets_status_lbl.setText("状态: 未连接小程序")
        self._devtools_lbl.setText("")
        self._devtools_copy_hint.setText("")
        # 引擎停止，清除侧栏和运行状态卡片的小程序信息
        c = _TH[self._tn]
        self._sb_app_name.setText("未连接")
        self._sb_app_name.setStyleSheet(f"color: {c['text3']};")
        self._sb_app_id.setText("")
        self._sb_app_id.setVisible(False)
        self._app_lbl.setText("AppID: --")
        self._appname_lbl.setText("")
        self._appname_lbl.setVisible(False)

    def _nav_btns(self, on):
        for b in (self._btn_go, self._btn_relaunch,
                  self._btn_back, self._btn_refresh, self._btn_auto, self._btn_prev,
                  self._btn_next, self._btn_copy_route):
            b.setEnabled(on)
        self._guard_switch.setEnabled(on)

    def _do_fetch(self):
        if self._engine and self._loop:
            asyncio.run_coroutine_threadsafe(self._afetch(), self._loop)

    async def _afetch(self):
        try:
            await self._navigator.fetch_config()
            self._rte_q.put(("routes", self._navigator.pages, self._navigator.tab_bar_pages))
            self._rte_q.put(("app_info", self._navigator.app_info))
            QTimer.singleShot(0, self._poll_route_start)
            # fetch_config 的 name 可能为空，补充通过 wxFrame 路径获取完整信息
            await self._afetch_app_info()
        except Exception as e:
            self._log_q.put(("error", f"[导航] 获取失败: {e}"))

    async def _afetch_app_info(self):
        """通过 nav_inject 的 wxFrame.__wxConfig 获取小程序名称和appid，用于侧栏显示。"""
        try:
            # 强制重新注入 navigator（重连后 WebView 上下文是全新的）
            await self._navigator._ensure(force=True)
            result = await self._engine.evaluate_js(
                "(function(){"
                "try{"
                "var nav=window.nav;"
                "if(!nav||!nav.wxFrame)return JSON.stringify({err:'no nav'});"
                "var c=nav.wxFrame.__wxConfig||{};"
                "var ai=c.accountInfo||{};"
                "var aa=ai.appAccount||{};"
                "return JSON.stringify({"
                "appid:aa.appId||ai.appId||c.appid||'',"
                "name:aa.nickname||ai.nickname||c.appname||''"
                "})"
                "}catch(e){return JSON.stringify({err:e.message})}"
                "})()",
                timeout=5.0,
            )
            value = None
            if result:
                r = result.get("result", {})
                inner = r.get("result", {})
                value = inner.get("value")
            if value:
                info = json.loads(value)
                if info.get("err"):
                    return
                self._rte_q.put(("app_info", info))
        except Exception:
            pass

    def _delayed_stable_connect(self, gen):
        """连接稳定后再启用按钮和触发后续操作，gen 不匹配说明中间又断过，跳过。"""
        if gen != self._vc_stable_gen:
            return
        if not self._miniapp_connected:
            return
        self._nav_btns(True)
        self._targets_btns(True)
        self._targets_status_lbl.setText("状态: 可刷新目标")
        self._btn_vc_enable.setEnabled(True)
        self._btn_vc_disable.setEnabled(True)
        self._vc_status_lbl.setText("状态: 就绪")
        # 自动检测 vConsole 调试状态
        if self._engine and self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._avc_detect_debug(), self._loop)
        # 延迟获取侧栏信息
        self._sb_fetch_gen += 1
        fetch_gen = self._sb_fetch_gen
        QTimer.singleShot(1500, lambda: self._delayed_fetch_app_info(fetch_gen))
        # 自动恢复云扫描
        if not self._cloud_scan_active and self._auditor:
            self._cloud_start_scan()
            self._log_add("info", "[云扫描] 小程序连接后自动恢复捕获")
        # 自动启动 WxAPI 捕获（不自动启动，用户手动开启）

    def _delayed_fetch_app_info(self, gen):
        """延迟调用，只有最后一次触发的 gen 匹配才执行。"""
        if gen != self._sb_fetch_gen:
            return
        if self._miniapp_connected and self._engine and self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._afetch_app_info(), self._loop)

    def _delayed_clear_app_info(self, gen):
        """延迟清除侧栏信息，gen 不匹配说明已重连，跳过。"""
        if gen != self._sb_fetch_gen:
            return
        c = _TH[self._tn]
        self._sb_app_name.setText("未连接")
        self._sb_app_name.setStyleSheet(f"color: {c['text3']};")
        self._sb_app_id.setText("")
        self._sb_app_id.setVisible(False)
        self._app_lbl.setText("AppID: --")
        self._appname_lbl.setText("")
        self._appname_lbl.setVisible(False)

    def _poll_route_start(self):
        if not self._running:
            return
        if self._engine and self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._apoll_route(), self._loop)
        self._route_poll_id = QTimer.singleShot(2000, self._poll_route_start)

    def _poll_route_stop(self):
        self._route_poll_id = None

    async def _apoll_route(self):
        try:
            r = await self._navigator.get_current_route()
            self._rte_q.put(("current", r))
            if self._redirect_guard_on:
                blocked = await self._navigator.get_blocked_redirects()
                if blocked:
                    self._rte_q.put(("blocked", blocked))
        except Exception:
            pass

    def _sel_route(self):
        items = self._tree.selectedItems()
        if not items:
            self._log_add("error", "[导航] 请先选择路由")
            return None
        item = items[0]
        return item.data(0, Qt.UserRole)

    def _do_go(self):
        r = self._sel_route()
        if r and self._engine and self._loop:
            if r in self._flat_routes:
                self._nav_route_idx = self._flat_routes.index(r)
            asyncio.run_coroutine_threadsafe(
                self._anav("navigate_to", r, "跳转"), self._loop)

    def _do_relaunch(self):
        r = self._sel_route()
        if r and self._engine and self._loop:
            asyncio.run_coroutine_threadsafe(
                self._anav("relaunch_to", r, "重启"), self._loop)

    def _do_back(self):
        if self._engine and self._loop:
            asyncio.run_coroutine_threadsafe(self._aback(), self._loop)

    async def _anav(self, method, route, desc):
        try:
            await getattr(self._navigator, method)(route)
            self._log_q.put(("info", f"[导航] 已{desc}到: {route}"))
        except Exception as e:
            self._log_q.put(("error", f"[导航] {desc}失败: {e}"))

    async def _aback(self):
        try:
            await self._navigator.navigate_back()
            self._log_q.put(("info", "[导航] 已返回"))
        except Exception as e:
            self._log_q.put(("error", f"[导航] 返回失败: {e}"))

    def _do_refresh(self):
        if self._engine and self._loop:
            asyncio.run_coroutine_threadsafe(self._arefresh(), self._loop)

    async def _arefresh(self):
        try:
            result = await self._navigator.refresh_page()
            if result:
                import json as _json
                try:
                    info = _json.loads(result)
                    if info.get("err"):
                        self._log_q.put(("error", f"[导航] 刷新失败: {info['err']}"))
                        return
                    route = info.get("route", "")
                    self._log_q.put(("info", f"[导航] 已刷新页面: /{route}"))
                except (_json.JSONDecodeError, TypeError):
                    self._log_q.put(("info", "[导航] 已刷新页面"))
            else:
                self._log_q.put(("info", "[导航] 已刷新页面"))
        except Exception as e:
            self._log_q.put(("error", f"[导航] 刷新失败: {e}"))

    def _do_autovis(self):
        if not self._navigator or not self._navigator.pages:
            self._log_add("error", "[导航] 请先获取路由")
            return
        self._cancel_ev = asyncio.Event()
        self._btn_auto.setEnabled(False)
        self._btn_autostop.setEnabled(True)
        asyncio.run_coroutine_threadsafe(
            self._aauto(list(self._navigator.pages)), self._loop)

    async def _aauto(self, pages):
        def prog(i, total, route):
            self._rte_q.put(("progress", i, total, route))
        try:
            await self._navigator.auto_visit(
                pages, delay=2.0, on_progress=prog, cancel_event=self._cancel_ev)
        except Exception as e:
            self._log_q.put(("error", f"[导航] 遍历出错: {e}"))
        finally:
            self._rte_q.put(("auto_done",))

    def _do_autostop(self):
        if self._cancel_ev:
            self._cancel_ev.set()
        self._btn_autostop.setEnabled(False)
        self._btn_auto.setEnabled(True)

    def _do_prev(self):
        routes = self._flat_routes or self._all_routes
        if not routes:
            self._log_add("error", "[导航] 请先获取路由")
            return
        if self._nav_route_idx <= 0:
            self._nav_route_idx = len(routes) - 1
        else:
            self._nav_route_idx -= 1
        route = routes[self._nav_route_idx]
        self._select_tree_route(route)
        self._log_add("info", f"[导航] 上一个: {route} ({self._nav_route_idx + 1}/{len(routes)})")
        if self._engine and self._loop:
            asyncio.run_coroutine_threadsafe(
                self._anav("navigate_to", route, "跳转"), self._loop)

    def _do_next(self):
        routes = self._flat_routes or self._all_routes
        if not routes:
            self._log_add("error", "[导航] 请先获取路由")
            return
        if self._nav_route_idx >= len(routes) - 1:
            self._nav_route_idx = 0
        else:
            self._nav_route_idx += 1
        route = routes[self._nav_route_idx]
        self._select_tree_route(route)
        self._log_add("info", f"[导航] 下一个: {route} ({self._nav_route_idx + 1}/{len(routes)})")
        if self._engine and self._loop:
            asyncio.run_coroutine_threadsafe(
                self._anav("navigate_to", route, "跳转"), self._loop)

    def _do_manual_go(self):
        route = self._nav_input.text().strip().lstrip("/")
        if not route:
            self._log_add("error", "[导航] 请输入路由路径")
            return
        if self._engine and self._loop:
            asyncio.run_coroutine_threadsafe(
                self._anav("navigate_to", route, "跳转"), self._loop)

    def _do_copy_route(self):
        items = self._tree.selectedItems()
        if not items:
            self._log_add("error", "[导航] 请先选择路由")
            return
        route = items[0].data(0, Qt.UserRole)
        if route:
            QApplication.clipboard().setText(route)
            self._log_add("info", f"[导航] 已复制路由: {route}")

    def _nav_context_menu(self, pos):
        item = self._tree.itemAt(pos)
        if not item:
            return
        route = item.data(0, Qt.UserRole)
        if not route:
            return
        self._tree.setCurrentItem(item)
        menu = QMenu(self)
        menu.addAction("复制路由", lambda: (
            QApplication.clipboard().setText(route),
            self._log_add("info", f"[导航] 已复制: {route}")))
        menu.addSeparator()
        menu.addAction("跳转", lambda: asyncio.run_coroutine_threadsafe(
            self._anav("navigate_to", route, "跳转"), self._loop) if self._engine and self._loop else None)
        menu.addAction("重启到页面", lambda: asyncio.run_coroutine_threadsafe(
            self._anav("relaunch_to", route, "重启"), self._loop) if self._engine and self._loop else None)
        menu.exec(self._tree.viewport().mapToGlobal(pos))

    def _do_toggle_guard_switch(self, checked):
        if not self._engine or not self._loop:
            self._guard_switch.blockSignals(True)
            self._guard_switch.setChecked(not checked)
            self._guard_switch.blockSignals(False)
            return
        asyncio.run_coroutine_threadsafe(self._atoggle_guard(checked), self._loop)

    async def _atoggle_guard(self, enable):
        try:
            if enable:
                r = await self._navigator.enable_redirect_guard()
                if r.get("ok"):
                    self._redirect_guard_on = True
                    self._blocked_seen = 0
                    self._log_q.put(("info", "[导航] 防跳转已开启，将拦截 redirectTo/reLaunch"))
                    QTimer.singleShot(0, lambda: self._guard_label.setText("防跳转: 开启"))
                else:
                    self._redirect_guard_on = False
                    self._log_q.put(("error", "[导航] 开启防跳转失败"))
                    QTimer.singleShot(0, self._guard_reset_switch)
            else:
                await self._navigator.disable_redirect_guard()
                self._redirect_guard_on = False
                self._log_q.put(("info", "[导航] 防跳转已关闭"))
                QTimer.singleShot(0, lambda: self._guard_label.setText("防跳转: 关闭"))
        except Exception as e:
            self._log_q.put(("error", f"[导航] 防跳转切换失败: {e}"))
            QTimer.singleShot(0, self._guard_reset_switch)

    def _guard_reset_switch(self):
        self._guard_switch.blockSignals(True)
        self._guard_switch.setChecked(self._redirect_guard_on)
        self._guard_switch.blockSignals(False)
        self._guard_label.setText("防跳转: 开启" if self._redirect_guard_on else "防跳转: 关闭")

    def _do_filter(self):
        q = self._srch_ent.text().strip().lower()
        if not q:
            if self._navigator:
                self._fill_tree(self._all_routes, self._navigator.tab_bar_pages)
            return
        flt = [p for p in self._all_routes if q in p.lower()]
        self._tree.setUpdatesEnabled(False)
        self._tree.clear()
        for p in flt:
            item = QTreeWidgetItem([p])
            item.setData(0, Qt.UserRole, p)
            self._tree.addTopLevelItem(item)
        self._tree.setUpdatesEnabled(True)

    def _fill_tree(self, pages, tab_bar):
        self._tree.setUpdatesEnabled(False)
        self._tree.clear()
        tabs = set(tab_bar)
        groups = {}
        for p in pages:
            parts = p.split("/")
            g = parts[0] if len(parts) > 1 else "(root)"
            groups.setdefault(g, []).append(p)

        flat = []  # tree visual order for prev/next

        tl = [p for p in pages if p in tabs]
        if tl:
            nd = QTreeWidgetItem(["TabBar"])
            nd.setExpanded(True)
            self._tree.addTopLevelItem(nd)
            for p in tl:
                d = p.split("/")[-1] if "/" in p else p
                child = QTreeWidgetItem([d])
                child.setData(0, Qt.UserRole, p)
                nd.addChild(child)
                flat.append(p)
        for g in sorted(groups):
            nd = QTreeWidgetItem([g])
            self._tree.addTopLevelItem(nd)
            for p in groups[g]:
                if p in tabs:
                    continue
                d = p[len(g) + 1:] if p.startswith(g + "/") else p
                child = QTreeWidgetItem([d])
                child.setData(0, Qt.UserRole, p)
                nd.addChild(child)
                flat.append(p)

        self._flat_routes = flat
        self._tree.setUpdatesEnabled(True)

        # 默认选中并定位到第一个页面
        if flat and self._nav_route_idx < 0:
            self._nav_route_idx = 0
            self._select_tree_route(flat[0])

    def _select_tree_route(self, route):
        """Select the tree item matching the given route path."""
        for i in range(self._tree.topLevelItemCount()):
            top = self._tree.topLevelItem(i)
            if top.data(0, Qt.UserRole) == route:
                self._tree.setCurrentItem(top)
                self._tree.scrollToItem(top)
                return
            for j in range(top.childCount()):
                child = top.child(j)
                if child.data(0, Qt.UserRole) == route:
                    self._tree.setCurrentItem(child)
                    self._tree.scrollToItem(child)
                    return

    # ──────────────────────────────────
    #  云扫描业务
    # ──────────────────────────────────

    def _cloud_tree_context_menu(self, pos):
        item = self._cloud_tree.itemAt(pos)
        if not item:
            return
        self._cloud_tree.setCurrentItem(item)
        vals = [item.text(i) for i in range(6)]
        menu = QMenu(self)
        full_text = "  |  ".join(vals)
        menu.addAction("复制整行", lambda: QApplication.clipboard().setText(full_text))
        name_str = vals[2] if len(vals) > 2 else ""
        if name_str:
            menu.addAction(f"复制名称: {name_str[:30]}",
                           lambda: QApplication.clipboard().setText(name_str))
        menu.addSeparator()
        row_id = id(item)
        if row_id in self._cloud_row_results:
            res = self._cloud_row_results[row_id]
            menu.addAction("查看返回结果",
                           lambda: self._cloud_show_result(name_str, res))
            menu.addSeparator()
        menu.addAction("删除此项", lambda: self._cloud_delete_item(item))
        menu.exec(self._cloud_tree.viewport().mapToGlobal(pos))

    def _cloud_delete_item(self, item):
        vals = tuple(item.text(i) for i in range(6))
        idx = self._cloud_tree.indexOfTopLevelItem(item)
        if idx >= 0:
            self._cloud_tree.takeTopLevelItem(idx)
        self._cloud_all_items = [v for v in self._cloud_all_items if tuple(str(x) for x in v) != vals]
        self._cloud_row_results.pop(id(item), None)
        self._cloud_update_status()

    def _cloud_show_result(self, name, result):
        detail = json.dumps(result, ensure_ascii=False, indent=2, default=str)
        c = _TH[self._tn]
        self._cloud_result.setHtml(f'<span style="color:{c["text1"]}">「{name}」返回结果:\n{detail}</span>')

    def _cloud_update_status(self):
        count = self._cloud_tree.topLevelItemCount()
        total = len(self._cloud_all_items)
        if count < total:
            self._cloud_status_lbl.setText(f"显示: {count} / {total} 条")
        else:
            self._cloud_status_lbl.setText(f"捕获: {count} 条")

    def _cloud_filter(self):
        kw = self._cloud_search_ent.text().strip().lower()
        self._cloud_tree.clear()
        for vals in self._cloud_all_items:
            if kw and not any(kw in str(v).lower() for v in vals):
                continue
            item = QTreeWidgetItem([str(v) for v in vals])
            self._cloud_tree.addTopLevelItem(item)
        self._cloud_update_status()

    def _cloud_on_select(self, item):
        if item and item.columnCount() >= 4:
            self._cloud_name_ent.setText(item.text(2))
            data_str = item.text(3).strip()
            try:
                json.loads(data_str)
                self._cloud_data_ent.setText(data_str)
            except Exception:
                self._cloud_data_ent.setText("{}")

    def _cloud_ensure_auditor(self):
        if not self._engine or not self._loop or not self._loop.is_running():
            self._log_add("error", "[云扫描] 请先启动调试")
            return False
        if not self._auditor:
            self._auditor = CloudAuditor(self._engine)
        return True

    def _cloud_do_toggle(self):
        """兼容：现在改为切换到动态捕获页面"""
        self._cloud_show_live()

    def _cloud_show_live(self):
        """切换到动态捕获子页面"""
        self._cloud_stack.setCurrentIndex(1)
        # 确保捕获已启动
        if not self._cloud_scan_active:
            self._cloud_start_scan()
        self._cloud_live_update_status()

    def _cloud_live_back(self):
        """返回主视图"""
        self._cloud_stack.setCurrentIndex(0)

    def _cloud_live_select(self, item):
        """点击动态捕获列表项，显示详情"""
        idx = self._cloud_live_tree.indexOfTopLevelItem(item)
        if idx < 0 or idx >= len(self._cloud_live_items):
            return
        self._cloud_live_selected_idx = idx
        call = self._cloud_live_items[idx]
        # 显示请求参数
        req_data = call.get("data", {})
        self._cloud_live_req.setPlainText(
            json.dumps(req_data, ensure_ascii=False, indent=2, default=str))
        # 显示返回结果
        c = _TH[self._tn]
        status = call.get("status", "")
        if call.get("result") is not None:
            resp_text = json.dumps(call["result"], ensure_ascii=False, indent=2, default=str)
            self._cloud_live_resp.setHtml(
                f'<span style="color:{c["success"]}">{resp_text}</span>')
        elif call.get("error") is not None:
            err_text = json.dumps(call["error"], ensure_ascii=False, indent=2, default=str)
            self._cloud_live_resp.setHtml(
                f'<span style="color:{c["error"]}">{err_text}</span>')
        else:
            self._cloud_live_resp.setPlainText(f"状态: {status} (无返回数据)")
        self._btn_cloud_live_replay.setEnabled(True)

    def _cloud_live_replay(self):
        """一键重放选中的云函数调用"""
        idx = self._cloud_live_selected_idx
        if idx < 0 or idx >= len(self._cloud_live_items):
            return
        if not self._cloud_ensure_auditor():
            return
        call = self._cloud_live_items[idx]
        name = call.get("name", "")
        data = call.get("data", {})
        if not name:
            return
        self._btn_cloud_live_replay.setEnabled(False)
        self._cloud_live_resp.setPlainText(f"正在重放 {name} ...")
        asyncio.run_coroutine_threadsafe(
            self._acloud_live_replay(name, data), self._loop)

    async def _acloud_live_replay(self, name, data):
        try:
            res = await self._auditor.call_function(name, data)
            self._cld_q.put(("live_replay_result", name, res))
        except Exception as e:
            self._cld_q.put(("live_replay_result", name,
                             {"ok": False, "status": "fail", "error": str(e)}))

    def _cloud_live_clear(self):
        """清空动态捕获列表"""
        self._cloud_live_items.clear()
        self._cloud_live_tree.clear()
        self._cloud_live_req.clear()
        self._cloud_live_resp.clear()
        self._btn_cloud_live_replay.setEnabled(False)
        self._cloud_live_selected_idx = -1
        self._cloud_live_update_status()

    def _cloud_live_filter(self):
        """动态捕获列表搜索过滤"""
        kw = self._cloud_live_search_ent.text().strip().lower()
        self._cloud_live_tree.clear()
        _type_cn = {"function": "云函数", "storage": "存储", "container": "容器",
                    "wx.auth": "认证", "wx.request": "请求", "wx.pay": "支付",
                    "wx.storage": "缓存", "wx.share": "分享", "wx.location": "位置",
                    "wx.device": "设备", "wx.nav": "导航", "wx.media": "媒体",
                    "wx.clipboard": "剪贴板", "wx.bridge": "原生桥接"}
        for call in self._cloud_live_items:
            ctype = call.get("type", "function")
            type_label = _type_cn.get(ctype, ctype)
            if ctype.startswith("db"):
                type_label = "数据库"
            name = call.get("name", "")
            status = call.get("status", "")
            ts = call.get("timestamp", "")
            if kw and kw not in type_label.lower() and kw not in name.lower():
                continue
            tree_item = QTreeWidgetItem([type_label, name, status, str(ts)])
            self._cloud_live_tree.addTopLevelItem(tree_item)

    def _cloud_live_update_status(self):
        count = len(self._cloud_live_items)
        if self._cloud_scan_active:
            self._cloud_live_status_lbl.setText(f"捕获中... {count} 条")
            c = _TH[self._tn]
            self._cloud_live_status_lbl.setStyleSheet(f"color: {c['success']};")
        else:
            self._cloud_live_status_lbl.setText(f"已停止 ({count} 条)")
            c = _TH[self._tn]
            self._cloud_live_status_lbl.setStyleSheet(f"color: {c['text3']};")

    def _cloud_start_scan(self):
        if not self._cloud_ensure_auditor():
            return
        self._cloud_scan_active = True
        c = _TH[self._tn]
        self._cloud_scan_lbl.setText("捕获中...")
        self._cloud_scan_lbl.setStyleSheet(f"color: {c['success']};")
        self._log_add("info", "[云扫描] 全局捕获已启动")
        asyncio.run_coroutine_threadsafe(self._acloud_start(), self._loop)
        self._cloud_scan_poll()

    async def _acloud_start(self):
        try:
            await self._auditor.start()
        except Exception as e:
            self._log_q.put(("error", f"[云扫描] Hook 启动异常: {e}"))

    def _cloud_stop_scan(self):
        self._cloud_scan_active = False
        c = _TH[self._tn]
        self._cloud_scan_lbl.setText("已停止")
        self._cloud_scan_lbl.setStyleSheet(f"color: {c['text3']};")
        if self._cloud_scan_poll_timer:
            self._cloud_scan_poll_timer.stop()
            self._cloud_scan_poll_timer = None
        if self._auditor and self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._auditor.stop(), self._loop)
        self._log_add("info", "[云扫描] 全局捕获已停止")

    def _cloud_scan_poll(self):
        if not self._cloud_scan_active or not self._auditor:
            return
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._acloud_poll(), self._loop)
        self._cloud_scan_poll_timer = QTimer()
        self._cloud_scan_poll_timer.setSingleShot(True)
        self._cloud_scan_poll_timer.timeout.connect(self._cloud_scan_poll)
        self._cloud_scan_poll_timer.start(2000)

    async def _acloud_poll(self):
        try:
            new_calls = await self._auditor.poll()
            if new_calls:
                self._cld_q.put(("new_calls", new_calls))
        except Exception:
            pass

    def _cloud_do_static_scan(self):
        if not self._cloud_ensure_auditor():
            return
        self._btn_cloud_static.setEnabled(False)
        self._log_add("info", "[云扫描] 开始静态扫描 JS 源码...")
        asyncio.run_coroutine_threadsafe(self._acloud_static_scan(), self._loop)

    async def _acloud_static_scan(self):
        try:
            def progress(msg):
                self._log_q.put(("info", f"[云扫描] {msg}"))
            results = await self._auditor.static_scan(on_progress=progress)
            self._cld_q.put(("static_results", results))
        except Exception as e:
            self._log_q.put(("error", f"[云扫描] 静态扫描异常: {e}"))
        finally:
            self._cld_q.put(("static_done",))

    def _cloud_do_clear(self):
        self._cloud_tree.clear()
        self._cloud_all_items.clear()
        self._cloud_row_results.clear()
        if self._auditor and self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._auditor.clear(), self._loop)
        self._cloud_status_lbl.setText("捕获: 0 条")

    def _cloud_do_call(self):
        if not self._cloud_ensure_auditor():
            return
        name = self._cloud_name_ent.text().strip()
        if not name:
            self._cloud_result.setPlainText("请输入函数名")
            return
        try:
            data = json.loads(self._cloud_data_ent.text())
        except (json.JSONDecodeError, TypeError):
            self._cloud_result.setPlainText("参数 JSON 格式错误")
            return
        self._btn_cloud_call.setEnabled(False)
        self._cloud_result.setPlainText(f"正在调用 {name} ...")
        asyncio.run_coroutine_threadsafe(self._acloud_call(name, data), self._loop)

    async def _acloud_call(self, name, data):
        try:
            res = await self._auditor.call_function(name, data)
            self._cld_q.put(("call_result", name, res))
        except Exception as e:
            self._cld_q.put(("call_result", name, {"ok": False, "status": "fail",
                                                    "error": str(e)}))

    def _cloud_do_export(self):
        if not self._auditor:
            self._log_add("error", "[云扫描] 无数据")
            return
        report = self._auditor.export_report(self._cloud_all_items, self._cloud_call_history)
        path = os.path.join(_BASE_DIR, "cloud_audit_report.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False, default=str)
            self._log_add("info", f"[云扫描] 报告已导出: {path}")
        except Exception as e:
            self._log_add("error", f"[云扫描] 导出失败: {e}")

    # ──────────────────────────────────
    #  WxAPI 捕获逻辑
    # ──────────────────────────────────

    def _wxapi_ensure(self):
        if not self._engine or not self._loop or not self._loop.is_running():
            self._log_add("error", "[WxAPI] 请先启动调试")
            return False
        if not self._wxapi_auditor:
            self._wxapi_auditor = WxApiAuditor(self._engine)
        return True

    def _wxapi_toggle(self):
        if self._wxapi_active:
            self._wxapi_stop()
            self._btn_wxapi_toggle.setText("开启捕获")
            c = _TH[self._tn]
            self._wxapi_status_lbl.setText("已关闭")
            self._wxapi_status_lbl.setStyleSheet(f"color: {c['text3']};")
        else:
            self._wxapi_start()
            self._btn_wxapi_toggle.setText("停止捕获")

    def _wxapi_start(self):
        if not self._wxapi_ensure():
            return
        if self._wxapi_active:
            return
        self._wxapi_active = True
        c = _TH[self._tn]
        self._wxapi_status_lbl.setText("捕获中...")
        self._wxapi_status_lbl.setStyleSheet(f"color: {c['success']};")
        self._log_add("info", "[WxAPI] 捕获已启动")
        asyncio.run_coroutine_threadsafe(self._awxapi_start(), self._loop)
        self._wxapi_poll()

    async def _awxapi_start(self):
        try:
            await self._wxapi_auditor.start()
        except Exception as e:
            self._log_q.put(("error", f"[WxAPI] Hook 启动异常: {e}"))

    def _wxapi_stop(self):
        self._wxapi_active = False
        if self._wxapi_poll_timer:
            self._wxapi_poll_timer.stop()
            self._wxapi_poll_timer = None
        if self._wxapi_auditor and self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._wxapi_auditor.stop(), self._loop)

    def _wxapi_poll(self):
        if not self._wxapi_active or not self._wxapi_auditor:
            return
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._awxapi_poll(), self._loop)
        self._wxapi_poll_timer = QTimer()
        self._wxapi_poll_timer.setSingleShot(True)
        self._wxapi_poll_timer.timeout.connect(self._wxapi_poll)
        self._wxapi_poll_timer.start(2000)

    async def _awxapi_poll(self):
        try:
            new_calls = await self._wxapi_auditor.poll()
            if new_calls:
                self._wxapi_q.put(("new_calls", new_calls))
        except Exception:
            pass

    def _wxapi_select(self, item):
        idx = self._wxapi_tree.indexOfTopLevelItem(item)
        if idx < 0 or idx >= len(self._wxapi_items):
            return
        self._wxapi_selected_idx = idx
        call = self._wxapi_items[idx]
        # 显示类型 + 名称标题
        ctype = call.get("type", "wx.api")
        name = call.get("name", "")
        self._wxapi_detail_title.setText(f"[{ctype}] {name}")
        # 请求参数 - 使用 setPlainText 确保可复制
        req_data = call.get("data", {})
        self._wxapi_req.setPlainText(
            json.dumps(req_data, ensure_ascii=False, indent=2, default=str))
        # 返回结果
        if call.get("result") is not None:
            resp_text = json.dumps(call["result"], ensure_ascii=False, indent=2, default=str)
            self._wxapi_resp.setPlainText(resp_text)
        elif call.get("error") is not None:
            err_text = json.dumps(call["error"], ensure_ascii=False, indent=2, default=str)
            self._wxapi_resp.setPlainText(err_text)
        else:
            self._wxapi_resp.setPlainText(f"状态: {call.get('status', '')} (无返回数据)")
        self._btn_wxapi_replay.setEnabled(True)

    def _wxapi_replay(self):
        idx = self._wxapi_selected_idx
        if idx < 0 or idx >= len(self._wxapi_items):
            return
        if not self._wxapi_ensure():
            return
        call = self._wxapi_items[idx]
        # 从 name 中提取原始 API 名称
        api_name = call.get("name", "")
        # wx.request 的 name 格式是 "GET https://..." 需要用 "request"
        if call.get("type") == "wx.request":
            api_name = "request"
        data = call.get("data", {})
        self._btn_wxapi_replay.setEnabled(False)
        self._wxapi_resp.setPlainText(f"正在重放 {api_name} ...")
        asyncio.run_coroutine_threadsafe(
            self._awxapi_replay(api_name, data), self._loop)

    async def _awxapi_replay(self, api_name, data):
        try:
            res = await self._wxapi_auditor.replay(api_name, data)
            self._wxapi_q.put(("replay_result", api_name, res))
        except Exception as e:
            self._wxapi_q.put(("replay_result", api_name,
                               {"ok": False, "status": "fail", "error": str(e)}))

    def _wxapi_clear(self):
        self._wxapi_items.clear()
        self._wxapi_tree.clear()
        self._wxapi_req.clear()
        self._wxapi_resp.clear()
        self._btn_wxapi_replay.setEnabled(False)
        self._wxapi_selected_idx = -1
        self._wxapi_status_lbl.setText(f"捕获中... 0 条" if self._wxapi_active else "已停止")
        if self._wxapi_auditor and self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._wxapi_auditor.clear(), self._loop)

    def _wxapi_filter(self):
        kw = self._wxapi_search_ent.text().strip().lower()
        self._wxapi_tree.clear()
        _type_cn = {"wx.auth": "认证", "wx.request": "请求", "wx.pay": "支付",
                    "wx.storage": "缓存", "wx.share": "分享", "wx.location": "位置",
                    "wx.device": "设备", "wx.nav": "导航", "wx.media": "媒体",
                    "wx.clipboard": "剪贴板"}
        for call in self._wxapi_items:
            ctype = call.get("type", "wx.api")
            type_label = _type_cn.get(ctype, ctype)
            name = call.get("name", "")
            status = call.get("status", "")
            ts = call.get("timestamp", "")
            if kw and kw not in type_label.lower() and kw not in name.lower():
                continue
            tree_item = QTreeWidgetItem([type_label, name, status, str(ts)])
            self._wxapi_tree.addTopLevelItem(tree_item)

    def _handle_wxapi(self, item):
        kind = item[0]
        c = _TH[self._tn]
        _type_cn = {"wx.auth": "认证", "wx.request": "请求", "wx.pay": "支付",
                    "wx.storage": "缓存", "wx.share": "分享", "wx.location": "位置",
                    "wx.device": "设备", "wx.nav": "导航", "wx.media": "媒体",
                    "wx.clipboard": "剪贴板", "wx.bridge": "原生桥接"}
        if kind == "new_calls":
            calls = item[1]
            if calls:
                kw = self._wxapi_search_ent.text().strip().lower()
                show_bridge = self._wxapi_bridge_cb.isChecked()
                show_request = self._wxapi_request_cb.isChecked()
                show_storage = self._wxapi_storage_cb.isChecked()
                for call in calls:
                    ctype = call.get("type", "wx.api")
                    # 原生桥接开关关闭时跳过 bridge 类型
                    if ctype == "wx.bridge" and not show_bridge:
                        continue
                    # wx.request 开关关闭时跳过
                    if ctype == "wx.request" and not show_request:
                        continue
                    # wx.storage 开关关闭时跳过
                    if ctype == "wx.storage" and not show_storage:
                        continue
                    self._wxapi_items.append(call)
                    type_label = _type_cn.get(ctype, ctype)
                    name = call.get("name", "")
                    status = call.get("status", "")
                    ts = call.get("timestamp", "")
                    if kw and kw not in type_label.lower() and kw not in name.lower():
                        continue
                    tree_item = QTreeWidgetItem([type_label, name, status, str(ts)])
                    self._wxapi_tree.addTopLevelItem(tree_item)
                self._wxapi_tree.scrollToBottom()
                count = len(self._wxapi_items)
                self._wxapi_status_lbl.setText(f"捕获中... {count} 条")
                self._wxapi_status_lbl.setStyleSheet(f"color: {c['success']};")
        elif kind == "replay_result":
            _, name, res = item
            self._btn_wxapi_replay.setEnabled(True)
            status = res.get("status", "unknown")
            if status == "success":
                detail = json.dumps(res.get("result", {}), ensure_ascii=False, indent=2, default=str)
                self._wxapi_resp.setHtml(
                    f'<span style="color:{c["success"]}">重放成功:\n{detail}</span>')
            elif status == "fail":
                err = res.get("error", "") or res.get("reason", "未知错误")
                self._wxapi_resp.setHtml(
                    f'<span style="color:{c["error"]}">重放失败: {err}</span>')
            else:
                detail = json.dumps(res, ensure_ascii=False, indent=2, default=str)
                self._wxapi_resp.setHtml(
                    f'<span style="color:{c["warning"]}">重放结果:\n{detail}</span>')

    # ──────────────────────────────────
    #  轮询
    # ──────────────────────────────────

    def _tick(self):
        for _ in range(60):  # 每轮最多处理60条日志，防止阻塞UI
            try:
                msg = self._log_q.get_nowait()
            except queue.Empty:
                break
            if isinstance(msg, tuple) and len(msg) == 3 and msg[0] == "__hook_status__":
                _, fn, ok = msg
                self._hook_update_status(fn, ok)
            else:
                lv, tx = msg
                self._log_add(lv, tx)
        last_sts = None
        for _ in range(50):
            try:
                last_sts = self._sts_q.get_nowait()
            except queue.Empty:
                break
        if last_sts is not None:
            self._apply_sts(last_sts)
        for _ in range(50):
            try:
                item = self._rte_q.get_nowait()
            except queue.Empty:
                break
            self._handle_rte(item)
        for _ in range(50):
            try:
                item = self._cld_q.get_nowait()
            except queue.Empty:
                break
            self._handle_cld(item)
        for _ in range(50):
            try:
                item = self._tgt_q.get_nowait()
            except queue.Empty:
                break
            self._handle_tgt(item)
        for _ in range(50):
            try:
                item = self._ext_q.get_nowait()
            except queue.Empty:
                break
            self._handle_ext(item)
        for _ in range(50):
            try:
                item = self._wxapi_q.get_nowait()
            except queue.Empty:
                break
            self._handle_wxapi(item)

    def _apply_sts(self, sts):
        c = _TH[self._tn]
        is_connected = sts.get("miniapp", False)
        for key, (dot, lb, name) in self._dots.items():
            on = sts.get(key, False)
            dot.set_color(c["success"] if on else c["text4"])
            lb.setText(f"{name}: {'已连接' if on else '未连接'}")
            lb.setStyleSheet(f"color: {c['success'] if on else c['text2']};")
        # 断开时立即禁用（除了已有路由时保留导航按钮）
        if not is_connected and self._miniapp_connected:
            if not self._all_routes:
                self._nav_btns(False)
            self._targets_btns(False)
            self._targets_status_lbl.setText("状态: 未连接小程序")
            self._btn_vc_enable.setEnabled(False)
            self._btn_vc_disable.setEnabled(False)
            self._vc_status_lbl.setText("状态: 未连接小程序")
            # 清除注入标记，切换小程序时全局脚本会重新注入
            self._hook_injected.clear()
            self._hook_refresh()
            # 已有路由数据时不清除侧栏信息（短暂断连不影响）
            if not self._all_routes:
                self._sb_fetch_gen += 1
                gen = self._sb_fetch_gen
                QTimer.singleShot(5000, lambda: self._delayed_clear_app_info(gen))
        # 小程序连接时，独立定时器触发全局 Hook 注入（不受 CDP 等状态变化影响）
        if is_connected and not self._miniapp_connected and self._global_hook_scripts:
            self._global_inject_gen += 1
            _gi_gen = self._global_inject_gen
            QTimer.singleShot(1500, lambda: self._do_global_inject(_gi_gen))
        # 连接时延迟启用，等连接稳定（防止重启时反复抖动）
        self._vc_stable_gen += 1
        gen_stable = self._vc_stable_gen
        if is_connected:
            QTimer.singleShot(1500, lambda: self._delayed_stable_connect(gen_stable))
        self._miniapp_connected = is_connected

    def _handle_rte(self, item):
        kind = item[0]
        if kind == "routes":
            _, pages, tab = item
            self._all_routes = list(pages)
            self._fill_tree(pages, tab)
        elif kind == "app_info":
            info = item[1]
            aid = info.get("appid", "")
            aname = info.get("name", "")
            ent = info.get("entry", "")
            # 运行状态卡片 — appid
            txt = f"AppID: {aid}" if aid else "AppID: --"
            if ent:
                txt += f"  |  入口: {ent}"
            self._app_lbl.setText(txt)
            # 运行状态卡片 — 名称
            if aname:
                self._appname_lbl.setText(f"当前链接小程序: {aname}")
                self._appname_lbl.setVisible(True)
            else:
                self._appname_lbl.setVisible(False)
            # 更新侧栏小程序信息卡片
            c = _TH[self._tn]
            if aname or aid:
                self._sb_app_name.setText(f"名称: {aname}" if aname else "名称: --")
                self._sb_app_name.setStyleSheet(f"color: {c['success']};")
                self._sb_app_id.setText(f"AppID: {aid}" if aid else "AppID: --")
                self._sb_app_id.setStyleSheet(f"color: {c['success']};")
                self._sb_app_id.setVisible(True)
            else:
                self._sb_app_name.setText("未连接")
                self._sb_app_name.setStyleSheet(f"color: {c['text3']};")
                self._sb_app_id.setVisible(False)
        elif kind == "current":
            r = item[1]
            self._route_lbl.setText(f"当前路由: /{r}" if r else "当前路由: --")
            if r:
                routes = self._flat_routes or self._all_routes
                if r in routes:
                    self._nav_route_idx = routes.index(r)
                    self._select_tree_route(r)
        elif kind == "progress":
            _, i, total, route = item
            if total > 0:
                self._prog.setValue(int((i / total) * 100))
            if route != "done":
                self._select_tree_route(route)
            self._route_lbl.setText(
                f"正在访问: /{route}" if route != "done" else "遍历完成")
        elif kind == "blocked":
            blocked = item[1]
            for b in blocked[self._blocked_seen:]:
                self._log_add("warn",
                    f"[防跳转] 拦截 {b.get('type','')} → {b.get('url','')}  ({b.get('time','')})")
            self._blocked_seen = len(blocked)
        elif kind == "auto_done":
            self._prog.setValue(100)
            self._btn_auto.setEnabled(True)
            self._btn_autostop.setEnabled(False)
            self._log_add("info", "[导航] 遍历完成")
        elif kind == "__vc__":
            _, enable, ok = item
            c = _TH[self._tn]
            if ok:
                if enable:
                    self._vc_status_lbl.setText("状态: 已开启 (重启小程序后生效)")
                    self._vc_status_lbl.setStyleSheet(f"color: {c['success']};")
                else:
                    self._vc_status_lbl.setText("状态: 已关闭 (重启小程序后生效)")
                    self._vc_status_lbl.setStyleSheet(f"color: {c['text3']};")
            else:
                self._vc_status_lbl.setText("状态: 操作失败")
                self._vc_status_lbl.setStyleSheet(f"color: {c['error']};")
            self._btn_vc_enable.setEnabled(True)
            self._btn_vc_disable.setEnabled(True)
        elif kind == "__vc_detect__":
            is_debug = item[1]
            c = _TH[self._tn]
            if is_debug:
                self._vc_status_lbl.setText("状态: 已开启")
                self._vc_status_lbl.setStyleSheet(f"color: {c['success']};")
            else:
                self._vc_status_lbl.setText("状态: 未开启")
                self._vc_status_lbl.setStyleSheet(f"color: {c['text3']};")

    def _handle_cld(self, item):
        kind = item[0]
        c = _TH[self._tn]
        _type_cn = {"function": "云函数", "storage": "存储", "container": "容器",
                    "wx.auth": "认证", "wx.request": "请求", "wx.pay": "支付",
                    "wx.storage": "缓存", "wx.share": "分享", "wx.location": "位置",
                    "wx.device": "设备", "wx.nav": "导航", "wx.media": "媒体",
                    "wx.clipboard": "剪贴板", "wx.bridge": "原生桥接"}
        if kind == "new_calls":
            calls = item[1]
            if calls:
                kw = self._cloud_search_ent.text().strip().lower()
                live_kw = self._cloud_live_search_ent.text().strip().lower()
                for call in calls:
                    data_str = json.dumps(call.get("data", {}), ensure_ascii=False)
                    if len(data_str) > 80:
                        data_str = data_str[:77] + "..."
                    ctype = call.get("type", "function")
                    type_label = _type_cn.get(ctype, ctype)
                    if ctype.startswith("db"):
                        type_label = "数据库"
                    status = call.get("status", "")
                    vals = (call.get("appId", ""), type_label,
                            call.get("name", ""), data_str,
                            status, call.get("timestamp", ""))
                    self._cloud_all_items.append(vals)
                    if not (kw and not any(kw in str(v).lower() for v in vals)):
                        tree_item = QTreeWidgetItem([str(v) for v in vals])
                        self._cloud_tree.addTopLevelItem(tree_item)
                        result_data = call.get("result") or call.get("error")
                        if result_data is not None:
                            self._cloud_row_results[id(tree_item)] = {
                                "status": status,
                                "result": call.get("result"),
                                "error": call.get("error"),
                                "data": call.get("data"),
                            }
                    # 同时推送到动态捕获列表
                    self._cloud_live_items.append(call)
                    name = call.get("name", "")
                    ts = call.get("timestamp", "")
                    if not (live_kw and live_kw not in type_label.lower()
                            and live_kw not in name.lower()):
                        live_item = QTreeWidgetItem([type_label, name, status, str(ts)])
                        self._cloud_live_tree.addTopLevelItem(live_item)
                self._cloud_tree.scrollToBottom()
                self._cloud_live_tree.scrollToBottom()
                self._cloud_update_status()
                self._cloud_live_update_status()
                self._cloud_scan_lbl.setText(f"捕获中... {len(self._cloud_all_items)} 条")
                self._cloud_scan_lbl.setStyleSheet(f"color: {c['success']};")
        elif kind == "static_results":
            funcs = item[1]
            if funcs:
                kw = self._cloud_search_ent.text().strip().lower()
                for f in funcs:
                    params = ", ".join(f.get("params", [])) or "--"
                    if len(params) > 80:
                        params = params[:77] + "..."
                    ftype = f.get("type", "function")
                    type_label = {"function": "云函数", "storage": "存储",
                                  "database": "数据库"}.get(ftype, ftype)
                    vals = (f.get("appId", ""), f"[静态]{type_label}",
                            f["name"], params, f"x{f.get('count',1)}", "")
                    self._cloud_all_items.append(vals)
                    if kw and not any(kw in str(v).lower() for v in vals):
                        continue
                    tree_item = QTreeWidgetItem([str(v) for v in vals])
                    self._cloud_tree.addTopLevelItem(tree_item)
                self._cloud_tree.scrollToBottom()
                self._cloud_update_status()
                self._log_add("info", f"[云扫描] 静态扫描发现 {len(funcs)} 个云函数引用")
        elif kind == "static_done":
            self._btn_cloud_static.setEnabled(True)
        elif kind == "call_result":
            _, name, res = item
            self._btn_cloud_call.setEnabled(True)
            status = res.get("status", "unknown")
            if status == "success":
                detail = json.dumps(res.get("result", {}), ensure_ascii=False, default=str)
                self._cloud_result.setHtml(
                    f'<span style="color:{c["success"]}">{name} -> 成功:\n{detail}</span>')
            elif status == "fail":
                err = res.get("error", "") or res.get("reason", "未知错误")
                self._cloud_result.setHtml(
                    f'<span style="color:{c["error"]}">{name} -> 失败: {err}</span>')
            else:
                detail = json.dumps(res, ensure_ascii=False, default=str)
                self._cloud_result.setHtml(
                    f'<span style="color:{c["warning"]}">{name} -> {detail}</span>')
        elif kind == "live_replay_result":
            _, name, res = item
            self._btn_cloud_live_replay.setEnabled(True)
            status = res.get("status", "unknown")
            if status == "success":
                detail = json.dumps(res.get("result", {}), ensure_ascii=False, indent=2, default=str)
                self._cloud_live_resp.setHtml(
                    f'<span style="color:{c["success"]}">重放成功:\n{detail}</span>')
            elif status == "fail":
                err = res.get("error", "") or res.get("reason", "未知错误")
                self._cloud_live_resp.setHtml(
                    f'<span style="color:{c["error"]}">重放失败: {err}</span>')
            else:
                detail = json.dumps(res, ensure_ascii=False, indent=2, default=str)
                self._cloud_live_resp.setHtml(
                    f'<span style="color:{c["warning"]}">重放结果:\n{detail}</span>')

    def _handle_ext(self, item):
        kind = item.get("type", "")
        c = _TH[self._tn]
        op = self._ext_current_op  # ("decompile"/"scan", appid) or None

        if kind == "progress":
            done = item.get("done", 0)
            total = item.get("total", 1)
            if total > 0:
                self._ext_prog.setValue(int((done / total) * 100))
            self._ext_status_lbl.setText(f"进度: {done}/{total}")

        elif kind == "log":
            self._ext_log(item.get("msg", ""))

        elif kind == "result":
            data = item.get("data", {})
            if op:
                op_type, appid = op
                if op_type == "decompile":
                    # 反编译完成
                    state = self._ext_app_states.setdefault(appid, {})
                    state["decompiled"] = True
                    decompile_dir = data.get("decompile_dir", "")
                    if decompile_dir:
                        state["decompile_dir"] = decompile_dir
                    extracted = data.get("extracted", 0)
                    self._ext_status_lbl.setText(f"反编译完成! {appid} 提取了 {extracted} 个文件")
                    self._ext_status_lbl.setStyleSheet(f"color: {c['success']};")
                    self._ext_update_app_buttons(appid)
                    # 刷新名称显示（解包后可读取 app-config.json）
                    widgets = self._ext_app_widgets.get(appid, {})
                    if "lbl_name" in widgets:
                        pkgs = state.get("packages", [])
                        output_base = os.path.join(_BASE_DIR, "output")
                        name = self._ext_get_app_name(appid, pkgs, output_base)
                        widgets["lbl_name"].setText(name)

                elif op_type == "scan":
                    # 扫描完成
                    state = self._ext_app_states.setdefault(appid, {})
                    state["scanned"] = True
                    result_dir = data.get("result_dir", "")
                    if result_dir:
                        state["result_dir"] = result_dir
                    findings = data.get("findings", 0)
                    self._ext_status_lbl.setText(f"扫描完成! {appid} 发现 {findings} 条敏感信息")
                    self._ext_status_lbl.setStyleSheet(f"color: {c['success']};")
                    self._ext_update_app_buttons(appid)

        elif kind == "error":
            self._ext_log(f"错误: {item.get('msg', '')}")
            self._ext_status_lbl.setText("出错")
            self._ext_status_lbl.setStyleSheet(f"color: {c['error']};")

        elif kind == "__done__":
            self._ext_proc = None
            prev_op = self._ext_current_op
            self._ext_current_op = None
            self._ext_prog.setValue(100)
            rc = item.get("returncode", -1)
            if rc != 0 and "完成" not in self._ext_status_lbl.text():
                self._ext_status_lbl.setText(f"进程退出 (code={rc})")
                self._ext_status_lbl.setStyleSheet(f"color: {c['error']};")

            # 自动处理链: 反编译完成后 → 自动扫描; 扫描完成后 → 处理下一个
            if prev_op and rc == 0:
                op_type, appid = prev_op
                if op_type == "decompile" and self._tog_auto_scan.isChecked():
                    state = self._ext_app_states.get(appid, {})
                    if state.get("decompiled") and not state.get("scanned"):
                        QTimer.singleShot(500, lambda a=appid: self._ext_do_scan(a))
                        return
                # 继续处理其他未完成的小程序
                QTimer.singleShot(500, self._ext_auto_process_pending)
    # ──────────────────────────────────
    #  退出
    # ──────────────────────────────────

    def closeEvent(self, event):
        if self._ext_proc:
            try:
                self._ext_proc.kill()  # 强制杀死子进程
                self._ext_proc.wait(timeout=2)
            except Exception:
                pass
            self._ext_proc = None
        if self._running:
            self._do_stop()
            QTimer.singleShot(400, lambda: QApplication.quit())
            event.ignore()
        else:
            event.accept()


if __name__ == "__main__":
    multiprocessing.freeze_support()  # PyInstaller 打包需要
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)   # Ctrl+C 直接退出

    # Windows 任务栏图标: 设置 AppUserModelID 使其显示自定义图标而非 Python 默认图标
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("spade.first.gui")
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setFont(QFont(_FN, _FN_SIZE))
    _ico = os.path.join(_BASE_DIR, "icon.png")
    if os.path.exists(_ico):
        app.setWindowIcon(QIcon(_ico))
    window = App()
    window.show()
    sys.exit(app.exec())
