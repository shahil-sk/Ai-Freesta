import sys
import os
from PySide6.QtCore import QUrl, Qt, QSettings, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QToolBar,
    QLineEdit,
    QMessageBox,
    QCheckBox,
    QScrollArea,
    QInputDialog,
    QLabel,
    QCompleter,
    QComboBox,
    QFrame,
)
from PySide6.QtGui import QAction, QKeyEvent, QIcon, QKeySequence, QShortcut
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage


# ------------------------------- config -------------------------------

AI_SITES = [
    {
        "name": "ChatGPT",
        "url": "https://chatgpt.com",
        "mobile": True,
        "input_selector": "textarea#prompt-textarea, textarea, [contenteditable='true']",
        "send_selector": "button[data-testid='send-button'], button[type='submit']",
        "delay_ms": 200,
    },
    {
        "name": "Grok",
        "url": "https://grok.com",
        "mobile": False,
        "input_selector": "textarea, [contenteditable='true']",
        "send_selector": "button[type='submit'], button[aria-label*='send' i]",
        "delay_ms": 200,
    },
    {
        "name": "Gemini",
        "url": "https://gemini.google.com",
        "mobile": False,
        "input_selector": "div.ql-editor[contenteditable='true'], textarea[aria-label*='Prompt'], textarea[placeholder*='Message Gemini']",
        "send_selector": "button[aria-label*='Send'], button[data-test-id='send-button']",
        "delay_ms": 200,
    },
    {
        "name": "Z.AI",
        "url": "https://chat.z.ai/",
        "mobile": False,
        "input_selector": "textarea, [contenteditable='true'], input[type='text']",
        "send_selector": "button[type='submit'], button[aria-label*='send' i]",
        "delay_ms": 100,
    },
    {
        "name": "Perplexity Ai",
        "url": "https://perplexity.ai/",
        "mobile": False,
        "input_selector": "textarea, [contenteditable='true'], input[type='text']",
        "send_selector": "button[type='submit'], button[aria-label*='send' i]",
        "delay_ms": 200,
    },
]

DESKTOP_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

MOBILE_UA = (
    "Mozilla/5.0 (Linux; Android 10; Mobile) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Mobile Safari/537.36"
)

MIN_PANE_WIDTH = 400
MAX_HISTORY = 100

DARK_STYLESHEET = """
QMainWindow {
    background-color: #1e1e1e;
}

QToolBar {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #2d2d30, stop:1 #252526);
    border-bottom: 1px solid #3e3e42;
    spacing: 8px;
    padding: 6px;
}

QToolBar QToolButton {
    background-color: #3e3e42;
    color: #ffffff;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 6px 12px;
    font-weight: bold;
    min-width: 70px;
}

QToolBar QToolButton:hover {
    background-color: #505050;
    border: 1px solid #007acc;
}

QToolBar QToolButton:pressed {
    background-color: #007acc;
    border: 1px solid #00a2ff;
}

QToolBar::separator {
    background: #555555;
    width: 2px;
    margin: 4px 8px;
}

QLineEdit {
    background-color: #2d2d30;
    color: #ffffff;
    border: 2px solid #3e3e42;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 14px;
    selection-background-color: #007acc;
}

QLineEdit:focus {
    border: 2px solid #007acc;
    background-color: #333333;
}

QLineEdit QToolButton {
    background-color: transparent;
    border: none;
    padding: 2px;
    margin-right: 4px;
}

QLineEdit QToolButton:hover {
    background-color: #505050;
    border-radius: 3px;
}

QScrollArea {
    background-color: #1e1e1e;
    border: none;
}

QSplitter::handle {
    background-color: #3e3e42;
}

QSplitter::handle:hover {
    background-color: #007acc;
}

QSplitter::handle:horizontal {
    width: 3px;
}

QSplitter::handle:vertical {
    height: 3px;
}

QMessageBox {
    background-color: #2d2d30;
    color: #ffffff;
}

QMessageBox QPushButton {
    background-color: #007acc;
    color: #ffffff;
    border: none;
    border-radius: 4px;
    padding: 6px 20px;
    min-width: 80px;
}

QMessageBox QPushButton:hover {
    background-color: #1a8ccc;
}

QLabel {
    color: #ffffff;
}

QComboBox {
    background-color: #3e3e42;
    color: #ffffff;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 4px 8px;
    min-width: 80px;
}

QComboBox QAbstractItemView {
    background-color: #2d2d30;
    color: #ffffff;
    selection-background-color: #007acc;
}

QFrame#pane_label_bar {
    background-color: #252526;
    border-bottom: 1px solid #3e3e42;
}
"""


# ---------------------------- web helpers ----------------------------

def make_view(url: str, *, mobile: bool) -> QWebEngineView:
    view = QWebEngineView()
    profile = view.page().profile()
    profile.setHttpUserAgent(MOBILE_UA if mobile else DESKTOP_UA)
    view.setUrl(QUrl(url))
    view.setMinimumWidth(MIN_PANE_WIDTH)
    return view


def js_fill_and_send(text: str, input_sel: str, send_sel: str, delay_ms: int) -> str:
    return f"""
setTimeout(() => {{
  const text = {text!r};
  const inputSel = {input_sel!r};
  const sendSel  = {send_sel!r};

  const el = document.querySelector(inputSel);
  if (!el) {{ console.warn('[AiFreesta] Input not found:', inputSel); return; }}
  if (el.disabled) {{ console.warn('[AiFreesta] Input is disabled'); return; }}

  el.focus();
  const isContentEditable = el.isContentEditable || el.getAttribute("contenteditable") === "true";
  if (isContentEditable) {{
    el.innerText = text;
    if (el.classList.contains('ql-editor')) el.innerHTML = '<p>' + text + '</p>';
  }} else {{
    el.value = text;
  }}

  el.dispatchEvent(new Event("input",  {{ bubbles: true }}));
  el.dispatchEvent(new Event("change", {{ bubbles: true }}));
  el.dispatchEvent(new InputEvent("input", {{ bubbles: true, inputType: 'insertText', data: text }}));

  setTimeout(() => {{
    const btn = document.querySelector(sendSel);
    if (btn && !btn.disabled) {{ btn.click(); return; }}
    const evDown  = new KeyboardEvent("keydown",  {{ key: "Enter", code: "Enter", keyCode: 13, which: 13, bubbles: true }});
    const evPress = new KeyboardEvent("keypress", {{ key: "Enter", code: "Enter", keyCode: 13, which: 13, bubbles: true }});
    const evUp    = new KeyboardEvent("keyup",    {{ key: "Enter", code: "Enter", keyCode: 13, which: 13, bubbles: true }});
    el.dispatchEvent(evDown); el.dispatchEvent(evPress); el.dispatchEvent(evUp);
  }}, 100);
}}, {delay_ms});
"""


def js_clear_chat() -> str:
    return """
const clearSelectors = [
    'button[aria-label*="New chat" i]', 'button[aria-label*="Clear" i]',
    'a[aria-label*="New chat" i]', '[data-testid*="new-chat"]'
];
for (let sel of clearSelectors) {
    const btn = document.querySelector(sel);
    if (btn) { btn.click(); break; }
}
console.log('[AiFreesta] Clear attempted');
"""


# ------------------------------ widgets ------------------------------

class BroadcastLineEdit(QLineEdit):
    """Input bar that broadcasts to all AI panes with history navigation."""

    def __init__(self, parent_window, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parent_window = parent_window
        self.setClearButtonEnabled(True)
        self._hist_idx = -1

    def keyPressEvent(self, event: QKeyEvent):
        history = self.parent_window.prompt_history

        # Up / Down arrow: navigate history
        if event.key() == Qt.Key_Up:
            if history and self._hist_idx < len(history) - 1:
                self._hist_idx += 1
                self.setText(history[self._hist_idx])
                self.selectAll()
            return

        if event.key() == Qt.Key_Down:
            if self._hist_idx > 0:
                self._hist_idx -= 1
                self.setText(history[self._hist_idx])
                self.selectAll()
            elif self._hist_idx == 0:
                self._hist_idx = -1
                self.clear()
            return

        # Enter: broadcast
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            text = self.text().strip()
            if text:
                if not history or history[0] != text:
                    history.insert(0, text)
                    if len(history) > MAX_HISTORY:
                        history.pop()
                    self.parent_window._save_history()
                    self.parent_window._refresh_completer()
                self._hist_idx = -1

                for view in self.parent_window.views:
                    if view is None:
                        continue
                    target = view.focusProxy() or view
                    ev = QKeyEvent(event.type(), event.key(), event.modifiers(),
                                   event.text(), event.isAutoRepeat(), event.count())
                    QApplication.postEvent(target, ev)

                for i, view in enumerate(self.parent_window.views):
                    if view is None or i >= len(self.parent_window.ai_sites):
                        continue
                    site = self.parent_window.ai_sites[i]
                    view.page().runJavaScript(
                        js_fill_and_send(text, site["input_selector"],
                                         site["send_selector"], site["delay_ms"])
                    )

            super().keyPressEvent(event)
            self.clear()
            return

        # All other keys: broadcast
        for view in self.parent_window.views:
            if view is None:
                continue
            target = view.focusProxy() or view
            ev = QKeyEvent(event.type(), event.key(), event.modifiers(),
                           event.text(), event.isAutoRepeat(), event.count())
            QApplication.postEvent(target, ev)

        super().keyPressEvent(event)


# --------------------------- main window -----------------------------

class DynamicAIWindow(QMainWindow):
    def __init__(self, ai_sites):
        super().__init__()

        self.setWindowTitle("🤖 Ai Freesta - Multi-AI Chat Interface")
        self.resize(1800, 950)

        self.ai_sites = ai_sites.copy()
        self.views = []
        self.zoom_level = 1.0
        self._always_on_top = False
        self.prompt_history: list = []
        self._current_layout = "horizontal"

        self.setStyleSheet(DARK_STYLESHEET)
        self._set_app_icon()
        self._load_history()

        # Central widget
        self.central = QWidget()
        self.vlayout = QVBoxLayout()
        self.vlayout.setContentsMargins(0, 0, 0, 0)
        self.vlayout.setSpacing(0)
        self.central.setLayout(self.vlayout)
        self.setCentralWidget(self.central)

        # Status bar
        self.status_label = QLabel()
        self.statusBar().addPermanentWidget(self.status_label)
        self.statusBar().setStyleSheet(
            "QStatusBar { background-color: #2d2d30; color: #ffffff; border-top: 1px solid #3e3e42; }"
        )

        # Scrollable pane area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.splitter_container = QWidget()
        self.splitter_layout = QVBoxLayout()
        self.splitter_layout.setContentsMargins(0, 0, 0, 0)
        self.splitter_container.setLayout(self.splitter_layout)
        self.scroll_area.setWidget(self.splitter_container)
        self.vlayout.addWidget(self.scroll_area)

        # Input row
        self._create_input_row()

        # Toolbar
        self.current_root_splitter = None
        self._create_toolbar()

        # Keyboard shortcuts
        self._setup_shortcuts()

        # Build
        self._initialize_views()
        self._rebuild_layout()
        self._update_status()

        self.show_startup_notice_once()

    # -------------------- setup helpers --------------------

    def _set_app_icon(self):
        for path in ("icon.png", "icon.ico"):
            if os.path.exists(path):
                icon = QIcon(path)
                self.setWindowIcon(icon)
                QApplication.instance().setWindowIcon(icon)
                break

    def _initialize_views(self):
        for site in self.ai_sites:
            view = make_view(site["url"], mobile=site["mobile"])
            self.views.append(view)

    # -------------------- prompt history --------------------

    def _history_path(self) -> str:
        return os.path.join(os.path.expanduser("~"), ".aifreesta_history.txt")

    def _load_history(self):
        path = self._history_path()
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                self.prompt_history = [l.rstrip("\n") for l in f if l.strip()][:MAX_HISTORY]

    def _save_history(self):
        with open(self._history_path(), "w", encoding="utf-8") as f:
            f.write("\n".join(self.prompt_history[:MAX_HISTORY]))

    def _refresh_completer(self):
        completer = QCompleter(self.prompt_history, self)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        self.input_edit.setCompleter(completer)

    # -------------------- input row --------------------

    def _create_input_row(self):
        self.input_edit = BroadcastLineEdit(self)
        self.input_edit.setMinimumHeight(50)
        f = self.input_edit.font()
        f.setPointSize(13)
        self.input_edit.setFont(f)
        self.input_edit.setPlaceholderText(
            "✨ Type your message — broadcasts to all AIs  |↑↓ history  | Enter to send"
        )
        self._refresh_completer()

        hbox = QHBoxLayout()
        hbox.setContentsMargins(8, 6, 8, 8)
        hbox.addWidget(self.input_edit)
        self.vlayout.addLayout(hbox)

    def _update_placeholder(self):
        self.input_edit.setPlaceholderText(
            f"✨ Broadcasting to {len(self.views)} panes  |↑↓ history  | Enter to send"
        )

    def _update_status(self):
        self.status_label.setText(
            f"   🤖 {len(self.views)} AI Chats Active   |   Zoom {int(self.zoom_level * 100)}%   |   Ready"
        )

    # -------------------- keyboard shortcuts --------------------

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+="), self, self.zoom_in)
        QShortcut(QKeySequence("Ctrl+-"), self, self.zoom_out)
        QShortcut(QKeySequence("Ctrl+0"), self, self.zoom_reset)
        QShortcut(QKeySequence("Ctrl+L"), self, self.input_edit.setFocus)
        QShortcut(QKeySequence("Ctrl+R"), self, self.refresh_all_panes)
        QShortcut(QKeySequence("Ctrl+T"), self, self.toggle_always_on_top)

    # -------------------- toolbar --------------------

    def _create_toolbar(self):
        toolbar = QToolBar("Main Controls")
        toolbar.setMovable(False)
        toolbar.setIconSize(toolbar.iconSize() * 1.2)
        self.addToolBar(toolbar)

        act_add = QAction("➕ Add AI", self)
        act_add.triggered.connect(self.add_new_ai)
        act_add.setToolTip("Add a new AI chat pane")
        toolbar.addAction(act_add)

        act_remove = QAction("➖ Remove", self)
        act_remove.triggered.connect(self.remove_ai_pane)
        act_remove.setToolTip("Remove an AI pane")
        toolbar.addAction(act_remove)

        toolbar.addSeparator()

        self.layout_combo = QComboBox()
        self.layout_combo.addItems(["▬ Horizontal", "▥ Vertical", "⊞ Grid"])
        self.layout_combo.setToolTip("Switch pane layout")
        self.layout_combo.currentIndexChanged.connect(self._on_layout_combo)
        toolbar.addWidget(self.layout_combo)

        toolbar.addSeparator()

        act_zin = QAction("🔍+", self)
        act_zin.triggered.connect(self.zoom_in)
        act_zin.setToolTip("Zoom in all panes  (Ctrl+=)")
        toolbar.addAction(act_zin)

        act_zout = QAction("🔍−", self)
        act_zout.triggered.connect(self.zoom_out)
        act_zout.setToolTip("Zoom out all panes  (Ctrl+-)")
        toolbar.addAction(act_zout)

        act_zreset = QAction("100%", self)
        act_zreset.triggered.connect(self.zoom_reset)
        act_zreset.setToolTip("Reset zoom  (Ctrl+0)")
        toolbar.addAction(act_zreset)

        toolbar.addSeparator()

        act_refresh_all = QAction("🔄 Refresh", self)
        act_refresh_all.triggered.connect(self.refresh_all_panes)
        act_refresh_all.setToolTip("Open all AI sites fresh  (Ctrl+R)")
        toolbar.addAction(act_refresh_all)

        act_stop = QAction("🛑 Stop", self)
        act_stop.triggered.connect(self.stop_all_panes)
        act_stop.setToolTip("Stop loading all pages")
        toolbar.addAction(act_stop)

        act_clear = QAction("🗑️ Clear All", self)
        act_clear.triggered.connect(self.clear_all_chats)
        act_clear.setToolTip("Attempt to click New Chat on all sites")
        toolbar.addAction(act_clear)

        toolbar.addSeparator()

        self.act_ontop = QAction("📌 On Top", self)
        self.act_ontop.setCheckable(True)
        self.act_ontop.setToolTip("Keep window always on top  (Ctrl+T)")
        self.act_ontop.triggered.connect(self.toggle_always_on_top)
        toolbar.addAction(self.act_ontop)

        toolbar.addSeparator()

        act_hist = QAction("📜 History", self)
        act_hist.triggered.connect(self.show_history)
        act_hist.setToolTip("View / clear prompt history")
        toolbar.addAction(act_hist)

        act_help = QAction("❓ Help", self)
        act_help.triggered.connect(self.show_help)
        toolbar.addAction(act_help)

    def _on_layout_combo(self, index: int):
        styles = ["horizontal", "vertical", "grid"]
        self._rebuild_layout(styles[index])

    # -------------------- zoom --------------------

    def _apply_zoom(self):
        for view in self.views:
            if view:
                view.setZoomFactor(self.zoom_level)
        self._update_status()

    def zoom_in(self):
        self.zoom_level = min(3.0, round(self.zoom_level + 0.1, 1))
        self._apply_zoom()
        self.statusBar().showMessage(f"🔍 Zoom {int(self.zoom_level * 100)}%", 1500)

    def zoom_out(self):
        self.zoom_level = max(0.3, round(self.zoom_level - 0.1, 1))
        self._apply_zoom()
        self.statusBar().showMessage(f"🔍 Zoom {int(self.zoom_level * 100)}%", 1500)

    def zoom_reset(self):
        self.zoom_level = 1.0
        self._apply_zoom()
        self.statusBar().showMessage("🔍 Zoom reset to 100%", 1500)

    # -------------------- always on top --------------------

    def toggle_always_on_top(self):
        self._always_on_top = not self._always_on_top
        flags = self.windowFlags()
        if self._always_on_top:
            self.setWindowFlags(flags | Qt.WindowStaysOnTopHint)
            self.act_ontop.setChecked(True)
            self.statusBar().showMessage("📌 Always on top: ON", 2000)
        else:
            self.setWindowFlags(flags & ~Qt.WindowStaysOnTopHint)
            self.act_ontop.setChecked(False)
            self.statusBar().showMessage("📌 Always on top: OFF", 2000)
        self.show()

    # -------------------- remove pane --------------------

    def remove_ai_pane(self):
        if not self.views:
            return
        names = [site["name"] for site in self.ai_sites]
        name, ok = QInputDialog.getItem(
            self, "Remove AI Pane", "Select pane to remove:",
            names, len(names) - 1, False
        )
        if not ok:
            return
        idx = next((i for i, s in enumerate(self.ai_sites) if s["name"] == name), None)
        if idx is None:
            return
        view = self.views.pop(idx)
        self.ai_sites.pop(idx)
        view.setParent(None)
        view.deleteLater()
        self._rebuild_layout(self._current_layout)
        self._update_placeholder()
        self._update_status()
        self.statusBar().showMessage(f"Removed {name}", 3000)

    # -------------------- prompt history UI --------------------

    def show_history(self):
        if not self.prompt_history:
            QMessageBox.information(self, "Prompt History", "No history yet.")
            return
        preview = "\n".join(f"{i+1}. {p[:80]}" for i, p in enumerate(self.prompt_history[:20]))
        reply = QMessageBox.question(
            self, "Prompt History",
            f"Last {min(20, len(self.prompt_history))} prompts:\n\n{preview}\n\nClear all history?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.prompt_history.clear()
            self._save_history()
            self._refresh_completer()
            self.statusBar().showMessage("🗑️ Prompt history cleared", 2000)

    # -------------------- refresh / stop / clear --------------------

    def refresh_all_panes(self):
        for i, view in enumerate(self.views):
            if view and i < len(self.ai_sites):
                view.setUrl(QUrl(self.ai_sites[i]["url"]))
        self.statusBar().showMessage("♻️ Opening all sites fresh...", 3000)

    def stop_all_panes(self):
        for view in self.views:
            if view:
                view.stop()
        self.statusBar().showMessage("🛑 Stopped all loading", 2000)

    def clear_all_chats(self):
        reply = QMessageBox.question(
            self, "Clear All Chats",
            "This will try to click 'New Chat' on all sites.\nProceed?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            for view in self.views:
                if view:
                    view.page().runJavaScript(js_clear_chat())
            self.statusBar().showMessage("🗑️ Clear attempted on all panes", 3000)

    # -------------------- add pane --------------------

    def add_new_ai(self):
        url, ok = QInputDialog.getText(
            self, "Add New AI Chat",
            "Enter the AI chat URL:\n(e.g., https://claude.ai)"
        )
        if not ok or not url.strip():
            return
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        name, ok = QInputDialog.getText(
            self, "AI Name", "Enter a display name:",
            text=url.split("//")[-1].split("/")[0]
        )
        if not ok or not name.strip():
            name = url.split("//")[-1].split("/")[0]
        new_site = {
            "name": name, "url": url, "mobile": False,
            "input_selector": "textarea, [contenteditable='true'], input[type='text']",
            "send_selector": "button[type='submit'], button[aria-label*='send' i]",
            "delay_ms": 200,
        }
        self.ai_sites.append(new_site)
        view = make_view(url, mobile=False)
        view.setZoomFactor(self.zoom_level)
        self.views.append(view)
        self._rebuild_layout(self._current_layout)
        self._update_placeholder()
        self._update_status()
        self.statusBar().showMessage(f"Added {name}!", 5000)

    # -------------------- layouts --------------------

    def _make_pane_widget(self, view: QWebEngineView, name: str) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        bar = QFrame()
        bar.setObjectName("pane_label_bar")
        bar.setFixedHeight(26)
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(8, 0, 4, 0)

        lbl = QLabel(name)
        lbl.setStyleSheet("color: #cccccc; font-size: 12px; font-weight: bold;")
        bar_layout.addWidget(lbl)
        bar_layout.addStretch()

        layout.addWidget(bar)
        layout.addWidget(view)
        return container

    def _rebuild_layout(self, style: str = "horizontal"):
        self._current_layout = style

        if self.current_root_splitter is not None:
            self.splitter_layout.removeWidget(self.current_root_splitter)
            self.current_root_splitter.setParent(None)

        if not self.views:
            return

        pane_widgets = [
            self._make_pane_widget(
                view,
                self.ai_sites[i]["name"] if i < len(self.ai_sites) else f"Pane {i+1}"
            )
            for i, view in enumerate(self.views)
        ]

        if style == "vertical":
            root = QSplitter(Qt.Vertical)
            for w in pane_widgets:
                root.addWidget(w)
            root.setSizes([1] * len(pane_widgets))

        elif style == "grid":
            root = QSplitter(Qt.Horizontal)
            left = QSplitter(Qt.Vertical)
            right = QSplitter(Qt.Vertical)
            for i, w in enumerate(pane_widgets):
                (left if i % 2 == 0 else right).addWidget(w)
            root.addWidget(left)
            if right.count() > 0:
                root.addWidget(right)
            root.setSizes([1, 1])

        else:
            root = QSplitter(Qt.Horizontal)
            for w in pane_widgets:
                root.addWidget(w)
            root.setSizes([1] * len(pane_widgets))

        root.setChildrenCollapsible(False)
        self.current_root_splitter = root
        self.splitter_layout.addWidget(root)

        min_total_width = MIN_PANE_WIDTH * len(self.views)
        self.splitter_container.setMinimumWidth(min_total_width)

        self.statusBar().showMessage(f"📐 Layout: {style}", 1500)

    # -------------------- help --------------------

    def show_help(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("Ai Freesta - Help")
        msg.setIcon(QMessageBox.Information)
        msg.setText("🤖 Multi-AI Chat Interface")
        msg.setInformativeText(
            "<b>New Features:</b><br>"
            "• <b>↑/↓ arrows</b> in input bar to browse prompt history<br>"
            "• <b>Autocomplete</b> suggestions from past prompts<br>"
            "• <b>➖ Remove pane</b> — remove any AI pane by name<br>"
            "• <b>Zoom</b> all panes in/out simultaneously (Ctrl += / -)<br>"
            "• <b>Layout picker</b> (Horizontal / Vertical / Grid)<br>"
            "• <b>Always on Top</b> toggle (Ctrl+T)<br>"
            "• <b>Pane labels</b> show AI name above each pane<br><br>"

            "<b>Shortcuts:</b><br>"
            "• Ctrl+L — focus input bar<br>"
            "• Ctrl+R — refresh all panes<br>"
            "• Ctrl+= / Ctrl+- — zoom in / out<br>"
            "• Ctrl+0 — reset zoom<br>"
            "• Ctrl+T — always on top<br><br>"

            "<b>Tips:</b><br>"
            "• History saved to ~/.aifreesta_history.txt<br>"
            "• Click each AI input box once to focus it<br>"
            "• Press F12 in any pane to open DevTools"
        )
        msg.exec()

    # -------------------- startup notice --------------------

    def show_startup_notice_once(self):
        settings = QSettings("Ai Freesta", "Ai Freesta")
        if settings.value("hide_notice", False, type=bool):
            return
        msg = QMessageBox(self)
        msg.setWindowTitle("Welcome to Ai Freesta")
        msg.setIcon(QMessageBox.Information)
        msg.setText(f"🚀 Started with {len(self.views)} AI chats\nType once, get responses from all AIs!")
        msg.setInformativeText(
            "<b>Quick Start:</b><br>"
            "1. Type in the bottom bar<br>"
            "2. Press Enter to broadcast<br>"
            "3. Use ↑/↓ to recall past prompts<br>"
            "4. Ctrl+= / Ctrl+- to zoom<br><br>"
            "Click <b>❓ Help</b> for all shortcuts!"
        )
        cb = QCheckBox("Don't show again")
        msg.setCheckBox(cb)
        msg.exec()
        if cb.isChecked():
            settings.setValue("hide_notice", True)


# ------------------------------- main -------------------------------

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = DynamicAIWindow(AI_SITES)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
