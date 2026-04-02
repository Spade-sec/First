"""
First GUI — PySide6 版
Author: Spade-sec | https://github.com/Spade-sec/First
"""
import asyncio
import json
import multiprocessing
import os
import queue
import sys
import threading
from datetime import datetime

from PySide6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, Property, QRect,
    Signal, QPoint, QUrl,
)
from PySide6.QtGui import QPainter, QColor, QFont, QIcon, QPixmap, QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QFrame, QPushButton, QScrollArea, QTextEdit,
    QTreeWidget, QTreeWidgetItem, QProgressBar, QStackedWidget,
    QMenu, QHeaderView, QAbstractItemView,
)

from src.cli import CliOptions, DEBUG_PORT, CDP_PORT
from src.logger import Logger
from src.engine import DebugEngine
from src.navigator import MiniProgramNavigator
from src.cloud_audit import CloudAuditor
from src.userscript import load_userscripts_by_files
from src.js_analyzer import analyze_js, merge_results, CATEGORY_INFO, save_report, load_reports, delete_report

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
_FN = "Microsoft YaHei UI"
_FM = "Consolas"
_MENU = [
    ("control",   "\u25c9", "控制台"),
    ("navigator", "\u2b21", "路由导航"),
    ("hook",      "\u25c8", "Hook"),
    ("cloud",     "\u2601", "云扫描"),
    ("security",  "\u2623", "敏感提取"),
    ("logs",      "\u2261", "运行日志"),
]

# ══════════════════════════════════════════
#  配置持久化
# ══════════════════════════════════════════
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if getattr(sys, 'frozen', False):
    _BASE_DIR = os.path.dirname(sys.executable)
_CFG_FILE = os.path.join(_BASE_DIR, "gui_config.json")

os.makedirs(os.path.join(_BASE_DIR, "userscripts"), exist_ok=True)
os.makedirs(os.path.join(_BASE_DIR, "hook_scripts"), exist_ok=True)
os.makedirs(os.path.join(_BASE_DIR, "scan_reports"), exist_ok=True)


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
        l.setFont(QFont(_FM, 10))
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
#  敏感提取 — 独立进程 worker
# ══════════════════════════════════════════

def _sec_analyze_one(src):
    """独立进程 Pool 的 worker 函数：分析单个 JS 源码。"""
    try:
        return analyze_js(src)
    except Exception:
        return None


def _sec_worker_proc(js_sources, appid, base_dir, result_q, name=""):
    """在独立进程中并行分析 JS，通过 multiprocessing.Queue 回传进度和结果。"""
    try:
        total = len(js_sources)
        total_size = sum(len(s) for s in js_sources)

        if total == 0:
            result_q.put(("done", {}, 0, 0))
            return

        import os
        workers = min(total, max(4, os.cpu_count() or 4))
        result_q.put(("progress", 35, f"并行分析 ({workers} 线程) ..."))

        from concurrent.futures import ThreadPoolExecutor, as_completed
        results = []
        done_count = 0
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futs = {pool.submit(_sec_analyze_one, src): i for i, src in enumerate(js_sources)}
            for fut in as_completed(futs):
                r = fut.result()
                if r:
                    results.append(r)
                done_count += 1
                if done_count % 5 == 0 or done_count == total:
                    pct = 30 + int(done_count / total * 60)
                    result_q.put(("progress", pct, f"分析中 {done_count}/{total} ..."))

        merged = merge_results(results) if results else {}
        result_q.put(("progress", 95, "生成报告..."))

        try:
            save_report(base_dir, appid, merged, total, total_size, name=name)
        except Exception:
            pass

        result_q.put(("done", merged, total, total_size))
    except Exception as e:
        result_q.put(("error", f"分析进程异常: {e}"))
        result_q.put(("done", None, 0, 0))


def _sec_run_worker(js_sources, appid, base_dir, sec_q, name=""):
    """启动独立分析进程，用后台线程转发 multiprocessing.Queue 到 UI 的 queue.Queue。"""
    mp_q = multiprocessing.Queue()
    proc = multiprocessing.Process(
        target=_sec_worker_proc,
        args=(js_sources, appid, base_dir, mp_q, name),
        daemon=True,
    )
    proc.start()

    # 后台线程：等待进程完成，转发消息到 UI 队列
    def _relay():
        while proc.is_alive() or not mp_q.empty():
            try:
                item = mp_q.get(timeout=0.2)
                sec_q.put(item)
            except Exception:
                pass
        # 确保队列清空
        while not mp_q.empty():
            try:
                sec_q.put(mp_q.get_nowait())
            except Exception:
                break

    t = threading.Thread(target=_relay, daemon=True)
    t.start()


# ══════════════════════════════════════════
#  主窗口
# ══════════════════════════════════════════

class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("First")
        _ico = os.path.join(_BASE_DIR, "icon.ico")
        if os.path.exists(_ico):
            self.setWindowIcon(QIcon(_ico))
        self.resize(960, 620)
        self.setMinimumSize(780, 500)

        self._cfg = _load_cfg()
        self._tn = self._cfg.get("theme", "dark")
        self._pg = "control"
        self._running = False
        self._loop = self._loop_th = self._engine = self._navigator = self._auditor = None
        self._cloud_call_history = {}
        self._cloud_all_items = []
        self._cloud_row_results = {}
        self._cancel_ev = None
        self._route_poll_id = None
        self._all_routes = []
        self._cloud_scan_active = False
        self._cloud_scan_poll_timer = None
        self._redirect_guard_on = False
        self._hook_injected = set()
        self._blocked_seen = 0
        self._sec_scanning = False
        self._sec_result = None
        self._sec_view = "scan"  # "scan" | "report" | "history"

        self._log_q = queue.Queue()
        self._sts_q = queue.Queue()
        self._rte_q = queue.Queue()
        self._cld_q = queue.Queue()
        self._sec_q = queue.Queue()

        self._selected_preload = list(self._cfg.get("selected_preload_scripts", []))
        self._nav_route_idx = -1

        self._sb_items = {}
        self._page_map = {}

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
        sb_head.setFixedHeight(76)
        sb_head_lay = QVBoxLayout(sb_head)
        sb_head_lay.addStretch()

        logo_row = QHBoxLayout()
        logo_row.setContentsMargins(0, 0, 0, 0)
        logo_row.setSpacing(6)
        logo_row.addStretch()
        _ico_path = os.path.join(_BASE_DIR, "icon.ico")
        if os.path.exists(_ico_path):
            _ico_lbl = QLabel()
            _pix = QPixmap(_ico_path).scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            _ico_lbl.setPixmap(_pix)
            _ico_lbl.setFixedSize(20, 20)
            logo_row.addWidget(_ico_lbl)
        self._sb_logo = QLabel("First")
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
            ic.setFont(QFont(_FN, 13))
            nm = QLabel(name)
            nm.setProperty("class", "sb_name")
            nm.setFont(QFont(_FN, 10))
            row_lay.addWidget(ic)
            row_lay.addWidget(nm, 1)
            sb_nav_lay.addWidget(row)
            row.mousePressEvent = lambda e, p=pid: self._show(p)
            self._sb_items[pid] = (row, ic, nm)
        sb_nav_lay.addStretch()
        sb_lay.addWidget(sb_nav, 1)

        self._sb_theme = QLabel()
        self._sb_theme.setObjectName("sb_theme")
        self._sb_theme.setAlignment(Qt.AlignCenter)
        self._sb_theme.setCursor(Qt.PointingHandCursor)
        self._sb_theme.setFont(QFont(_FN, 9))
        self._sb_theme.mousePressEvent = lambda e: self._toggle_theme()
        sb_lay.addWidget(self._sb_theme)

        sb_author = QLabel("by vs-olitus")
        sb_author.setObjectName("sb_theme")
        sb_author.setAlignment(Qt.AlignCenter)
        sb_author.setFont(QFont(_FN, 8))
        sb_lay.addWidget(sb_author)
        sb_gh = QLabel("github.com/Spade-sec/First")
        sb_gh.setObjectName("sb_theme")
        sb_gh.setAlignment(Qt.AlignCenter)
        sb_gh.setFont(QFont(_FN, 7))
        sb_gh.setCursor(Qt.PointingHandCursor)
        sb_gh.mousePressEvent = lambda e: (
            QDesktopServices.openUrl(QUrl("https://github.com/Spade-sec/First")),
            self._log_add("info", "[gui] 已打开 GitHub 页面"))
        sb_lay.addWidget(sb_gh)
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
        self._build_cloud()
        self._build_security()
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
        row1.addWidget(QLabel("调试端口"))
        self._dp_ent = _make_entry(width=100)
        self._dp_ent.setText(str(self._cfg.get("debug_port", DEBUG_PORT)))
        self._dp_ent.textChanged.connect(lambda: self._auto_save())
        row1.addWidget(self._dp_ent)
        row1.addSpacing(20)
        row1.addWidget(QLabel("CDP 端口"))
        self._cp_ent = _make_entry(width=100)
        self._cp_ent.setText(str(self._cfg.get("cdp_port", CDP_PORT)))
        self._cp_ent.textChanged.connect(lambda: self._auto_save())
        row1.addWidget(self._cp_ent)
        row1.addStretch()
        c1_lay.addLayout(row1)

        c1_lay.addWidget(_make_label("调试选项", bold=True))
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
        c1_lay.addLayout(chkr)
        lay.addWidget(c1)

        # Card 2: 前加载脚本
        c2 = _make_card()
        c2_lay = QVBoxLayout(c2)
        c2_lay.setContentsMargins(16, 10, 16, 10)
        c2_lay.setSpacing(4)
        hdr_row = QHBoxLayout()
        hdr_row.addWidget(_make_label("前加载脚本", bold=True))
        hdr_row.addWidget(_make_label("(启动调试前可用)", muted=True))
        hdr_row.addStretch()
        self._btn_preload_refresh = _make_btn("刷新", self._preload_refresh)
        hdr_row.addWidget(self._btn_preload_refresh)
        c2_lay.addLayout(hdr_row)
        self._preload_container = QVBoxLayout()
        self._preload_container.setSpacing(2)
        c2_lay.addLayout(self._preload_container)
        lay.addWidget(c2)
        self._preload_refresh()

        # Action row
        ar = QHBoxLayout()
        self._btn_start = _make_btn("▶  启动调试", self._do_start)
        self._btn_start.setFont(QFont(_FN, 10, QFont.Bold))
        ar.addWidget(self._btn_start)
        self._btn_stop = _make_btn("■  停止", self._do_stop)
        self._btn_stop.setFont(QFont(_FN, 10, QFont.Bold))
        self._btn_stop.setEnabled(False)
        ar.addWidget(self._btn_stop)
        ar.addStretch()
        lay.addLayout(ar)

        # DevTools URL
        dt_row = QHBoxLayout()
        self._devtools_lbl = QLabel("")
        self._devtools_lbl.setProperty("class", "accent")
        self._devtools_lbl.setFont(QFont(_FM, 8))
        self._devtools_lbl.setCursor(Qt.PointingHandCursor)
        self._devtools_lbl.mousePressEvent = lambda e: self._copy_devtools_url()
        dt_row.addWidget(self._devtools_lbl)
        self._devtools_copy_hint = QLabel("")
        self._devtools_copy_hint.setProperty("class", "muted")
        self._devtools_copy_hint.setFont(QFont(_FN, 8))
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
        lay.addWidget(c3)

        self._stack.addWidget(page)
        self._page_map["control"] = self._stack.count() - 1

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
        self._btn_redir = _make_btn("重定向", self._do_redir)
        self._btn_redir.setEnabled(False)
        b1.addWidget(self._btn_redir)
        self._btn_relaunch = _make_btn("重启到页面", self._do_relaunch)
        self._btn_relaunch.setEnabled(False)
        b1.addWidget(self._btn_relaunch)
        self._btn_back = _make_btn("返回上页", self._do_back)
        self._btn_back.setEnabled(False)
        b1.addWidget(self._btn_back)
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
            icon_lbl.setFont(QFont(_FM, 8, QFont.Bold))
            icon_lbl.setFixedWidth(30)
            icon_lbl.setAlignment(Qt.AlignCenter)
            row_lay.addWidget(icon_lbl)

            name_lbl = QLabel(fn)
            name_lbl.setFont(QFont(_FN, 10))
            row_lay.addWidget(name_lbl, 1)

            injected = fn in self._hook_injected
            status_lbl = QLabel("● 已注入" if injected else "○ 未注入")
            c = _TH[self._tn]
            status_lbl.setStyleSheet(f"color: {c['success'] if injected else c['text3']};")
            row_lay.addWidget(status_lbl)
            self._hook_status_lbls[fn] = status_lbl

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
            lbl.setText("● 已注入" if injected else "○ 未注入")
            lbl.setStyleSheet(f"color: {c['success'] if injected else c['text3']};")

    # ── 云扫描 ──

    def _build_cloud(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(24, 12, 24, 16)
        lay.setSpacing(10)

        ctrl = QHBoxLayout()
        self._btn_cloud_toggle = _make_btn("停止捕获", self._cloud_do_toggle)
        ctrl.addWidget(self._btn_cloud_toggle)
        self._btn_cloud_static = _make_btn("静态扫描", self._cloud_do_static_scan)
        ctrl.addWidget(self._btn_cloud_static)
        self._btn_cloud_clear = _make_btn("清空记录", self._cloud_do_clear)
        ctrl.addWidget(self._btn_cloud_clear)
        self._cloud_scan_lbl = QLabel("")
        ctrl.addWidget(self._cloud_scan_lbl)
        ctrl.addStretch()
        self._btn_cloud_export = _make_btn("导出报告", self._cloud_do_export)
        ctrl.addWidget(self._btn_cloud_export)
        lay.addLayout(ctrl)

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
        lay.addWidget(tc, 1)

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
        lay.addLayout(call_row)

        self._cloud_result = QTextEdit()
        self._cloud_result.setReadOnly(True)
        self._cloud_result.setFixedHeight(120)
        self._cloud_result.setFont(QFont(_FM, 9))
        lay.addWidget(self._cloud_result)

        bot = QHBoxLayout()
        self._cloud_status_lbl = QLabel("捕获: 0 条")
        bot.addWidget(self._cloud_status_lbl)
        bot.addStretch()
        lay.addLayout(bot)

        self._stack.addWidget(page)
        self._page_map["cloud"] = self._stack.count() - 1

    # ── 敏感提取 ──

    def _build_security(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(24, 8, 24, 8)
        lay.setSpacing(6)

        # 顶部操作栏
        bar = QHBoxLayout()
        self._btn_sec_scan = _make_btn("扫描当前小程序", self._sec_do_scan)
        bar.addWidget(self._btn_sec_scan)
        self._btn_sec_history = _make_btn("历史记录", self._sec_show_history)
        bar.addWidget(self._btn_sec_history)
        self._btn_sec_back = _make_btn("返回", self._sec_back_to_scan)
        self._btn_sec_back.setVisible(False)
        bar.addWidget(self._btn_sec_back)
        bar.addStretch()
        self._sec_status_lbl = QLabel("")
        self._sec_status_lbl.setProperty("class", "muted")
        bar.addWidget(self._sec_status_lbl)
        lay.addLayout(bar)

        # 进度条
        self._sec_prog = QProgressBar()
        self._sec_prog.setFixedHeight(6)
        self._sec_prog.setRange(0, 100)
        self._sec_prog.setValue(0)
        self._sec_prog.setTextVisible(False)
        self._sec_prog.setVisible(False)
        lay.addWidget(self._sec_prog)

        # 主内容区 — 内含 QStackedWidget 切换 scan/report/history
        self._sec_stack = QStackedWidget()

        # --- 扫描提示页 (index 0) ---
        scan_hint = QWidget()
        sh_lay = QVBoxLayout(scan_hint)
        sh_lay.setAlignment(Qt.AlignCenter)
        hint_lbl = QLabel("连接小程序后，点击「扫描当前小程序」提取 JS 中的敏感信息")
        hint_lbl.setProperty("class", "muted")
        hint_lbl.setAlignment(Qt.AlignCenter)
        hint_lbl.setWordWrap(True)
        sh_lay.addWidget(hint_lbl)
        self._sec_stack.addWidget(scan_hint)

        # --- 报告页 (index 1) ---
        report_page = QWidget()
        rp_lay = QVBoxLayout(report_page)
        rp_lay.setContentsMargins(0, 0, 0, 0)
        rp_lay.setSpacing(6)

        # 报告头部: appid + 概要
        rp_hdr = QHBoxLayout()
        self._sec_rpt_header = QLabel("")
        self._sec_rpt_header.setProperty("class", "bold")
        rp_hdr.addWidget(self._sec_rpt_header)
        rp_hdr.addStretch()
        self._sec_rpt_summary = QLabel("")
        self._sec_rpt_summary.setProperty("class", "muted")
        rp_hdr.addWidget(self._sec_rpt_summary)
        rp_lay.addLayout(rp_hdr)

        # 左右分栏
        rp_split = QHBoxLayout()
        rp_split.setSpacing(8)

        # 左栏: 类别列表 (滚动)
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.NoFrame)
        left_scroll.setFixedWidth(220)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        left_inner = QWidget()
        self._sec_cat_lay = QVBoxLayout(left_inner)
        self._sec_cat_lay.setContentsMargins(0, 0, 0, 0)
        self._sec_cat_lay.setSpacing(2)
        self._sec_cat_lay.addStretch()
        left_scroll.setWidget(left_inner)
        rp_split.addWidget(left_scroll)

        # 右栏: 详情列表 (滚动)
        right_card = _make_card()
        right_card_lay = QVBoxLayout(right_card)
        right_card_lay.setContentsMargins(0, 0, 0, 0)
        right_card_lay.setSpacing(0)

        # 右栏顶部: 类别名 + 复制全部
        self._sec_detail_bar = QHBoxLayout()
        self._sec_detail_bar.setContentsMargins(14, 8, 14, 4)
        self._sec_detail_title = QLabel("选择左侧类别查看详情")
        self._sec_detail_title.setProperty("class", "bold")
        self._sec_detail_bar.addWidget(self._sec_detail_title)
        self._sec_detail_bar.addStretch()
        self._btn_sec_copy_all = _make_btn("复制全部", self._sec_copy_all)
        self._btn_sec_copy_all.setVisible(False)
        self._sec_detail_bar.addWidget(self._btn_sec_copy_all)
        right_card_lay.addLayout(self._sec_detail_bar)

        # 右栏内容: QTextEdit (只读，自带滚动条，填满剩余空间)
        self._sec_detail_text = QTextEdit()
        self._sec_detail_text.setReadOnly(True)
        self._sec_detail_text.setFont(QFont(_FM, 9))
        self._sec_detail_text.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        self._sec_detail_text.setFrameShape(QFrame.NoFrame)
        right_card_lay.addWidget(self._sec_detail_text, 1)

        rp_split.addWidget(right_card, 1)
        rp_lay.addLayout(rp_split, 1)

        self._sec_cur_cat = None  # 当前选中类别 key
        self._sec_cat_widgets = {}  # key -> row widget
        self._sec_stack.addWidget(report_page)

        # --- 历史页 (index 2) ---
        history_page = QWidget()
        hp_lay = QVBoxLayout(history_page)
        hp_lay.setContentsMargins(0, 0, 0, 0)
        hp_lay.setSpacing(6)

        self._sec_hist_tree = QTreeWidget()
        self._sec_hist_tree.setHeaderLabels(["时间", "AppID", "名称", "JS数量", "发现项"])
        self._sec_hist_tree.setColumnCount(5)
        self._sec_hist_tree.header().setStretchLastSection(True)
        self._sec_hist_tree.setRootIsDecorated(False)
        self._sec_hist_tree.setAlternatingRowColors(False)
        self._sec_hist_tree.header().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._sec_hist_tree.itemDoubleClicked.connect(self._sec_hist_open)
        self._sec_hist_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self._sec_hist_tree.customContextMenuRequested.connect(self._sec_hist_menu)
        hp_lay.addWidget(self._sec_hist_tree, 1)

        self._sec_stack.addWidget(history_page)

        lay.addWidget(self._sec_stack, 1)

        self._stack.addWidget(page)
        self._page_map["security"] = self._stack.count() - 1

    # ── 日志 ──

    def _build_logs(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(24, 12, 24, 16)
        lay.setSpacing(10)

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
        self._logbox.setFont(QFont(_FM, 9))
        lc_lay.addWidget(self._logbox)
        lay.addWidget(lc, 1)

        self._stack.addWidget(page)
        self._page_map["logs"] = self._stack.count() - 1

    # ──────────────────────────────────
    #  前加载脚本
    # ──────────────────────────────────

    def _preload_refresh(self):
        while self._preload_container.count():
            item = self._preload_container.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        scripts_dir = os.path.join(_BASE_DIR, "userscripts")
        js_files = sorted(f for f in os.listdir(scripts_dir) if f.endswith(".js")) if os.path.isdir(scripts_dir) else []

        if not js_files:
            lbl = QLabel("userscripts/ 目录下无 .js 文件")
            lbl.setProperty("class", "muted")
            self._preload_container.addWidget(lbl)
            return

        for fn in js_files:
            row = QHBoxLayout()
            tog = ToggleSwitch(fn in self._selected_preload)
            tog.setFixedSize(36, 18)
            tog.toggled.connect(lambda v, f=fn: self._preload_toggle(f, v))
            row.addWidget(tog)
            row.addWidget(QLabel(fn))
            row.addStretch()
            w = QWidget()
            w.setLayout(row)
            self._preload_container.addWidget(w)

    def _preload_toggle(self, filename, val):
        if val:
            if filename not in self._selected_preload:
                self._selected_preload.append(filename)
        else:
            if filename in self._selected_preload:
                self._selected_preload.remove(filename)
        self._auto_save()

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
        self._hl_sb()
        self._auto_save()

    def _update_theme_label(self):
        txt = "\u2600  浅色模式" if self._tn == "dark" else "\u263d  深色模式"
        self._sb_theme.setText(txt)

    def _update_toggle_colors(self):
        c = _TH[self._tn]
        for tog in (self._tog_dm, self._tog_df):
            tog.set_colors(c["accent"], c["text4"])

    def _auto_save(self):
        data = {
            "theme": self._tn,
            "debug_port": self._dp_ent.text(),
            "cdp_port": self._cp_ent.text(),
            "debug_main": self._tog_dm.isChecked(),
            "debug_frida": self._tog_df.isChecked(),
            "selected_preload_scripts": list(self._selected_preload),
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
            dp = int(self._dp_ent.text())
            cp = int(self._cp_ent.text())
        except ValueError:
            self._log_add("error", "[gui] 端口号无效")
            return
        scripts_dir = os.path.join(_BASE_DIR, "userscripts")
        selected_files = [os.path.join(scripts_dir, fn) for fn in self._selected_preload]
        opts = CliOptions(
            debug_port=dp, cdp_port=cp,
            debug_main=self._tog_dm.isChecked(),
            debug_frida=self._tog_df.isChecked(),
            scripts_dir=scripts_dir,
            script_files=selected_files)
        logger = Logger(opts)
        logger.set_output_callback(lambda lv, tx: self._log_q.put((lv, tx)))
        us = load_userscripts_by_files(selected_files) if selected_files else []
        if us:
            logger.info(f"[脚本] 已加载 {len(us)} 个")
        else:
            logger.info("[脚本] 无脚本")
        self._engine = DebugEngine(opts, logger, us)
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
        if self._cancel_ev:
            self._cancel_ev.set()
        if self._engine and self._loop and self._loop.is_running():
            fut = asyncio.run_coroutine_threadsafe(self._engine.stop(), self._loop)
            fut.add_done_callback(lambda _: self._loop.call_soon_threadsafe(self._loop.stop))
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._btn_fetch.setEnabled(False)
        self._nav_btns(False)
        self._btn_autostop.setEnabled(False)
        self._redirect_guard_on = False
        self._guard_switch.setChecked(False)
        self._guard_label.setText("防跳转: 关闭")
        self._devtools_lbl.setText("")
        self._devtools_copy_hint.setText("")
        if self._sec_scanning:
            self._sec_scanning = False
            self._btn_sec_scan.setEnabled(True)
            self._sec_prog.setVisible(False)

    def _nav_btns(self, on):
        for b in (self._btn_go, self._btn_redir, self._btn_relaunch,
                  self._btn_back, self._btn_auto, self._btn_prev,
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
        except Exception as e:
            self._log_q.put(("error", f"[导航] 获取失败: {e}"))

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
            asyncio.run_coroutine_threadsafe(
                self._anav("navigate_to", r, "跳转"), self._loop)

    def _do_redir(self):
        r = self._sel_route()
        if r and self._engine and self._loop:
            asyncio.run_coroutine_threadsafe(
                self._anav("redirect_to", r, "重定向"), self._loop)

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
        if not self._all_routes:
            self._log_add("error", "[导航] 请先获取路由")
            return
        if self._nav_route_idx <= 0:
            self._nav_route_idx = len(self._all_routes) - 1
        else:
            self._nav_route_idx -= 1
        route = self._all_routes[self._nav_route_idx]
        self._select_tree_route(route)
        self._log_add("info", f"[导航] 上一个: {route} ({self._nav_route_idx + 1}/{len(self._all_routes)})")
        if self._engine and self._loop:
            asyncio.run_coroutine_threadsafe(
                self._anav("navigate_to", route, "跳转"), self._loop)

    def _do_next(self):
        if not self._all_routes:
            self._log_add("error", "[导航] 请先获取路由")
            return
        if self._nav_route_idx >= len(self._all_routes) - 1:
            self._nav_route_idx = 0
        else:
            self._nav_route_idx += 1
        route = self._all_routes[self._nav_route_idx]
        self._select_tree_route(route)
        self._log_add("info", f"[导航] 下一个: {route} ({self._nav_route_idx + 1}/{len(self._all_routes)})")
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
        menu.addAction("重定向", lambda: asyncio.run_coroutine_threadsafe(
            self._anav("redirect_to", route, "重定向"), self._loop) if self._engine and self._loop else None)
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
        self._tree.clear()
        for p in flt:
            item = QTreeWidgetItem([p])
            item.setData(0, Qt.UserRole, p)
            self._tree.addTopLevelItem(item)

    def _fill_tree(self, pages, tab_bar):
        self._tree.clear()
        tabs = set(tab_bar)
        groups = {}
        for p in pages:
            parts = p.split("/")
            g = parts[0] if len(parts) > 1 else "(root)"
            groups.setdefault(g, []).append(p)
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
        if not self._cloud_ensure_auditor():
            return
        if self._cloud_scan_active:
            self._cloud_stop_scan()
        else:
            self._cloud_start_scan()

    def _cloud_start_scan(self):
        if not self._cloud_ensure_auditor():
            return
        self._cloud_scan_active = True
        c = _TH[self._tn]
        self._btn_cloud_toggle.setText("停止捕获")
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
        self._btn_cloud_toggle.setText("开启捕获")
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
    #  敏感提取业务
    # ──────────────────────────────────

    def _sec_do_scan(self):
        if self._sec_scanning:
            self._log_add("info", "[敏感提取] 扫描正在进行中，请稍候...")
            return
        if not self._engine or not self._loop or not self._loop.is_running():
            self._log_add("error", "[敏感提取] 请先启动调试并连接小程序")
            return
        if not self._engine.miniapp_clients:
            self._log_add("error", "[敏感提取] 小程序未连接，请先打开小程序")
            return
        self._sec_scanning = True
        self._btn_sec_scan.setEnabled(False)
        self._sec_prog.setVisible(True)
        self._sec_prog.setValue(0)
        self._sec_status_lbl.setText("正在提取 JS 源码...")
        self._sec_stack.setCurrentIndex(0)
        self._log_add("info", "[敏感提取] 开始扫描...")
        fut = asyncio.run_coroutine_threadsafe(self._asec_scan(), self._loop)
        # 捕获 future 异常，防止静默失败
        def _on_scan_done(f):
            try:
                f.result()
            except Exception as e:
                self._sec_q.put(("error", f"扫描协程异常: {e}"))
                self._sec_q.put(("done", None, 0, 0))
        fut.add_done_callback(_on_scan_done)

    async def _asec_scan(self):
        try:
            # Step 1: 通过 CDP Debugger 获取所有 JS 脚本源码
            self._sec_q.put(("progress", 5, "正在收集脚本列表..."))

            script_ids = []

            def _on_parsed(data):
                p = data.get("params", {})
                sid = p.get("scriptId")
                if sid:
                    script_ids.append((sid, p.get("url", "")))

            self._engine.on_cdp_event("Debugger.scriptParsed", _on_parsed)
            try:
                try:
                    await self._engine.send_cdp_command("Debugger.disable", timeout=3.0)
                except Exception:
                    pass
                await asyncio.sleep(0.3)
                try:
                    await self._engine.send_cdp_command("Debugger.enable", timeout=5.0)
                except asyncio.TimeoutError:
                    self._sec_q.put(("log", "Debugger.enable 超时，尝试重新启用..."))
                    await asyncio.sleep(0.5)
                    try:
                        await self._engine.send_cdp_command("Debugger.enable", timeout=5.0)
                    except Exception as e2:
                        self._sec_q.put(("log", f"Debugger.enable 重试失败: {e2}"))
                try:
                    await self._engine.send_cdp_command(
                        "Debugger.setSkipAllPauses", {"skip": True}, timeout=3.0)
                except Exception:
                    pass
                # 等待 scriptParsed 事件全部到达：
                # 先等 2 秒让大部分事件到达，然后连续 3 次(每次 0.4s)数量不变才认为稳定
                await asyncio.sleep(2.0)
                stable_count = 0
                prev = 0
                for _ in range(15):
                    cur = len(script_ids)
                    if cur == prev and cur > 0:
                        stable_count += 1
                        if stable_count >= 3:
                            break
                    else:
                        stable_count = 0
                    prev = cur
                    await asyncio.sleep(0.4)
                self._sec_q.put(("log", f"脚本收集完成: {len(script_ids)} 个"))
            except Exception as e:
                self._sec_q.put(("log", f"Debugger 启动异常: {e}"))
            finally:
                self._engine.off_cdp_event("Debugger.scriptParsed", _on_parsed)

            if not script_ids:
                self._sec_q.put(("error", "未能获取到脚本列表，请确保小程序已打开"))
                self._sec_q.put(("done", None, 0, 0))
                return

            self._sec_q.put(("progress", 15,
                             f"发现 {len(script_ids)} 个脚本，正在提取源码..."))

            # Step 2: 逐个获取脚本源码
            js_sources = []
            for i, (sid, url) in enumerate(script_ids):
                try:
                    resp = await self._engine.send_cdp_command(
                        "Debugger.getScriptSource", {"scriptId": sid}, timeout=8.0)
                    source = resp.get("result", {}).get("scriptSource", "")
                    if source and len(source) > 20:
                        js_sources.append(source)
                except Exception:
                    pass
                if i % 10 == 0:
                    pct = 15 + int((i + 1) / len(script_ids) * 15)
                    self._sec_q.put(("progress", pct,
                                     f"提取源码 {i+1}/{len(script_ids)} ..."))

            try:
                await self._engine.send_cdp_command("Debugger.disable", timeout=3.0)
            except Exception:
                pass

            if not js_sources:
                self._sec_q.put(("error", "脚本源码提取为空"))
                self._sec_q.put(("done", None, 0, 0))
                return

            total_size = sum(len(s) for s in js_sources)
            self._sec_q.put(("progress", 30,
                             f"已提取 {len(js_sources)} 个 JS 源码，启动独立分析进程..."))

            # Step 3: 获取小程序信息 (若还没获取过，自动 fetch_config)
            appid = ""
            app_name = ""
            if self._navigator:
                if not self._navigator.app_info or not self._navigator.app_info.get("appid"):
                    try:
                        await self._navigator.fetch_config()
                    except Exception:
                        pass
                appid = self._navigator.app_info.get("appid", "")
                app_name = self._navigator.app_info.get("name", "")
            if not appid:
                appid = "unknown"

            # Step 4: 在独立进程中分析 (不阻塞主进程/UI)
            _sec_run_worker(js_sources, appid, _BASE_DIR, self._sec_q, name=app_name)

        except Exception as e:
            self._sec_q.put(("error", f"分析失败: {e}"))
            self._sec_q.put(("done", None, 0, 0))

    def _sec_extract_val(self, result):
        if not result:
            return None
        r = result.get("result", {})
        inner = r.get("result", {})
        return inner.get("value")

    def _sec_show_report(self, result, js_count=0, total_size=0, appid="", scan_time="", name=""):
        """在报告页渲染分析结果 (左类别列表 + 右详情)"""
        self._sec_result = result
        c = _TH[self._tn]

        if not scan_time:
            scan_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        header_parts = []
        if name:
            header_parts.append(name)
        if appid:
            header_parts.append(f"AppID: {appid}")
        self._sec_rpt_header.setText("  |  ".join(header_parts) if header_parts else "分析报告")

        total_findings = sum(len(v) for v in result.values() if isinstance(v, list))
        summary = f"{js_count} 个 JS ({self._fmt_size(total_size)})  |  " \
                  f"{total_findings} 项  |  {scan_time}" if js_count else \
                  f"{total_findings} 项  |  {scan_time}"
        self._sec_rpt_summary.setText(summary)

        # 清除旧的左栏类别行
        while self._sec_cat_lay.count() > 1:
            item = self._sec_cat_lay.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._sec_cat_widgets.clear()
        self._sec_cur_cat = None

        # 生成左栏类别行
        for key in CATEGORY_INFO:
            items = result.get(key, [])
            cn, _ = CATEGORY_INFO[key]
            count = len(items)

            row = QFrame()
            row.setFixedHeight(38)
            row.setCursor(Qt.PointingHandCursor)
            row_lay = QHBoxLayout(row)
            row_lay.setContentsMargins(0, 0, 6, 0)
            row_lay.setSpacing(6)

            # 绿色竖条
            bar = QFrame()
            bar.setFixedSize(4, 24)
            bar.setStyleSheet(f"background: {c['accent']}; border-radius: 2px;")
            row_lay.addWidget(bar)

            name_lbl = QLabel(cn)
            name_lbl.setProperty("class", "bold")
            name_lbl.setFont(QFont(_FN, 10))
            row_lay.addWidget(name_lbl, 1)

            count_lbl = QLabel(str(count))
            count_lbl.setFont(QFont(_FM, 9))
            if count > 0:
                count_lbl.setStyleSheet(f"color: {c['accent']};")
            else:
                count_lbl.setStyleSheet(f"color: {c['text3']};")
            row_lay.addWidget(count_lbl)

            copy_btn = QPushButton("复制")
            copy_btn.setFixedSize(52, 26)
            copy_btn.setFont(QFont(_FN, 9))
            copy_btn.clicked.connect(lambda _, k=key, b=copy_btn: self._sec_copy_cat(k, b))
            row_lay.addWidget(copy_btn)

            row.mousePressEvent = lambda e, k=key: self._sec_select_cat(k)
            self._sec_cat_widgets[key] = row
            self._sec_cat_lay.insertWidget(self._sec_cat_lay.count() - 1, row)

        # 清空右侧
        self._sec_clear_detail()
        self._sec_detail_title.setText("选择左侧类别查看详情")
        self._btn_sec_copy_all.setVisible(False)

        # 自动选中第一个有内容的类别
        for key in CATEGORY_INFO:
            if result.get(key):
                self._sec_select_cat(key)
                break

        self._sec_stack.setCurrentIndex(1)
        self._btn_sec_back.setVisible(True)

    def _sec_select_cat(self, key):
        """选中左栏类别，在右栏显示详情列表"""
        c = _TH[self._tn]
        self._sec_cur_cat = key

        # 高亮左栏选中项
        for k, row in self._sec_cat_widgets.items():
            if k == key:
                row.setStyleSheet(
                    f"QFrame {{ background: {c['sb_active']}; border-radius: 6px; }}"
                    f" QLabel {{ color: {c['text1']}; }}"
                    f" QPushButton {{ color: {c['text1']}; }}"
                )
            else:
                row.setStyleSheet("")

        items = self._sec_result.get(key, []) if self._sec_result else []
        cn, _ = CATEGORY_INFO.get(key, (key, ""))

        self._sec_detail_title.setText(f"{cn}  ({len(items)})")
        self._btn_sec_copy_all.setVisible(len(items) > 0)

        # 直接填充 QTextEdit，每行一条
        if items:
            self._sec_detail_text.setStyleSheet(
                f"QTextEdit {{ color: {c['text1']}; background: transparent;"
                f" selection-background-color: {c['accent']}; }}"
            )
            self._sec_detail_text.setPlainText("\n".join(str(v) for v in items))
        else:
            self._sec_detail_text.clear()

    def _sec_clear_detail(self):
        """清空右栏详情"""
        self._sec_detail_text.clear()

    def _sec_copy_cat(self, key, btn=None):
        """复制某个类别的全部内容"""
        items = self._sec_result.get(key, []) if self._sec_result else []
        if items:
            QApplication.clipboard().setText("\n".join(str(v) for v in items))
            cn, _ = CATEGORY_INFO.get(key, (key, ""))
            self._sec_status_lbl.setText(f"已复制 {cn} ({len(items)} 项)")
            if btn and isinstance(btn, QPushButton):
                old_text = btn.text()
                btn.setText("已复制")
                QTimer.singleShot(1200, lambda: btn.setText(old_text) if btn else None)

    def _sec_copy_all(self):
        """复制当前选中类别的全部内容"""
        if self._sec_cur_cat:
            self._sec_copy_cat(self._sec_cur_cat, self._btn_sec_copy_all)

    def _sec_show_history(self):
        self._sec_hist_tree.clear()
        reports = load_reports(_BASE_DIR)
        for r in reports:
            summary = r.get("summary", {})
            total = sum(summary.values())
            item = QTreeWidgetItem([
                r.get("time", ""),
                r.get("appid", ""),
                r.get("name", ""),
                str(r.get("js_count", 0)),
                str(total),
            ])
            item.setData(0, Qt.UserRole, r)
            self._sec_hist_tree.addTopLevelItem(item)
        self._sec_stack.setCurrentIndex(2)
        self._btn_sec_back.setVisible(True)
        self._sec_status_lbl.setText(f"共 {len(reports)} 条记录")

    def _sec_hist_open(self, item):
        r = item.data(0, Qt.UserRole)
        if not r:
            return
        result = r.get("result", {})
        self._sec_show_report(
            result,
            js_count=r.get("js_count", 0),
            total_size=r.get("total_size", 0),
            appid=r.get("appid", ""),
            scan_time=r.get("time", ""),
            name=r.get("name", ""),
        )

    def _sec_hist_menu(self, pos):
        item = self._sec_hist_tree.itemAt(pos)
        if not item:
            return
        r = item.data(0, Qt.UserRole)
        menu = QMenu(self)
        menu.addAction("查看报告", lambda: self._sec_hist_open(item))
        if r:
            menu.addAction("删除", lambda: self._sec_hist_delete(item, r))
        menu.exec(self._sec_hist_tree.viewport().mapToGlobal(pos))

    def _sec_hist_delete(self, item, r):
        fn = r.get("_filename", "")
        if fn:
            delete_report(_BASE_DIR, fn)
        idx = self._sec_hist_tree.indexOfTopLevelItem(item)
        if idx >= 0:
            self._sec_hist_tree.takeTopLevelItem(idx)

    def _sec_back_to_scan(self):
        if self._sec_result:
            self._sec_stack.setCurrentIndex(1)
        else:
            self._sec_stack.setCurrentIndex(0)
        self._btn_sec_back.setVisible(False)
        self._sec_status_lbl.setText("")

    def _handle_sec(self, item):
        kind = item[0]
        if kind == "progress":
            _, pct, msg = item
            self._sec_prog.setValue(pct)
            self._sec_status_lbl.setText(msg)
        elif kind == "log":
            self._log_add("info", f"[敏感提取] {item[1]}")
        elif kind == "error":
            self._log_add("error", f"[敏感提取] {item[1]}")
            self._sec_status_lbl.setText(item[1])
        elif kind == "done":
            _, result, js_count, total_size = item
            self._sec_scanning = False
            self._btn_sec_scan.setEnabled(True)
            self._sec_prog.setValue(100)
            QTimer.singleShot(500, lambda: self._sec_prog.setVisible(False))
            if result:
                total_findings = sum(len(v) for v in result.values() if isinstance(v, list))
                self._sec_status_lbl.setText(f"分析完成，发现 {total_findings} 项")
                self._log_add("info", f"[敏感提取] 完成: {js_count} 个 JS, 发现 {total_findings} 项")
                appid = ""
                app_name = ""
                if self._navigator and self._navigator.app_info:
                    appid = self._navigator.app_info.get("appid", "")
                    app_name = self._navigator.app_info.get("name", "")
                self._sec_show_report(result, js_count, total_size, appid, name=app_name)
            else:
                self._sec_status_lbl.setText("分析完成，无结果")

    @staticmethod
    def _fmt_size(n):
        if n < 1024:
            return f"{n} B"
        elif n < 1024 * 1024:
            return f"{n/1024:.1f} KB"
        else:
            return f"{n/1024/1024:.1f} MB"

    @staticmethod
    def _html_esc(s):
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

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
        for _ in range(50):
            try:
                s = self._sts_q.get_nowait()
            except queue.Empty:
                break
            self._apply_sts(s)
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
                item = self._sec_q.get_nowait()
            except queue.Empty:
                break
            self._handle_sec(item)

    def _apply_sts(self, sts):
        c = _TH[self._tn]
        for key, (dot, lb, name) in self._dots.items():
            on = sts.get(key, False)
            dot.set_color(c["success"] if on else c["text4"])
            lb.setText(f"{name}: {'已连接' if on else '未连接'}")
            lb.setStyleSheet(f"color: {c['success'] if on else c['text2']};")
        self._nav_btns(sts.get("miniapp", False))
        if sts.get("miniapp") and not self._cloud_scan_active and self._auditor:
            self._cloud_start_scan()

    def _handle_rte(self, item):
        kind = item[0]
        if kind == "routes":
            _, pages, tab = item
            self._all_routes = list(pages)
            self._fill_tree(pages, tab)
        elif kind == "app_info":
            info = item[1]
            aid = info.get("appid", "")
            ent = info.get("entry", "")
            txt = f"应用: {aid}" if aid else "应用: --"
            if ent:
                txt += f"  |  入口: {ent}"
            self._app_lbl.setText(txt)
        elif kind == "current":
            r = item[1]
            self._route_lbl.setText(f"当前路由: /{r}" if r else "当前路由: --")
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

    def _handle_cld(self, item):
        kind = item[0]
        c = _TH[self._tn]
        _type_cn = {"function": "云函数", "storage": "存储", "container": "容器"}
        if kind == "new_calls":
            calls = item[1]
            if calls:
                kw = self._cloud_search_ent.text().strip().lower()
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
                    if kw and not any(kw in str(v).lower() for v in vals):
                        continue
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
                self._cloud_tree.scrollToBottom()
                self._cloud_update_status()
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

    # ──────────────────────────────────
    #  退出
    # ──────────────────────────────────

    def closeEvent(self, event):
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

    app = QApplication(sys.argv)
    app.setFont(QFont(_FN, 9))
    window = App()
    window.show()
    sys.exit(app.exec())
