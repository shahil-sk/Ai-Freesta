import sys
from PySide6.QtCore import QUrl, Qt, QSettings
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
)
from PySide6.QtGui import QAction, QKeyEvent, QIcon
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
        "delay_ms": 200,
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

# Modern dark theme stylesheet
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

/* Style the built-in clear button [web:95] */
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
"""


# ---------------------------- web helpers ----------------------------

def make_view(url: str, *, mobile: bool) -> QWebEngineView:
    """Create a QWebEngineView with chosen user-agent and minimum width."""
    view = QWebEngineView()
    profile = view.page().profile()
    profile.setHttpUserAgent(MOBILE_UA if mobile else DESKTOP_UA)
    view.setUrl(QUrl(url))
    view.setMinimumWidth(MIN_PANE_WIDTH)
    return view


def js_fill_and_send(text: str, input_sel: str, send_sel: str, delay_ms: int) -> str:
    """JS with special handling for contenteditable divs."""
    return f"""
setTimeout(() => {{
  const text = {text!r};
  const inputSel = {input_sel!r};
  const sendSel  = {send_sel!r};

  const el = document.querySelector(inputSel);
  if (!el) {{
    console.warn('[AiFreesta] Input not found:', inputSel);
    return;
  }}

  if (el.disabled) {{
    console.warn('[AiFreesta] Input is disabled');
    return;
  }}

  el.focus();

  const isContentEditable = el.isContentEditable || el.getAttribute("contenteditable") === "true";
  if (isContentEditable) {{
    el.innerText = text;
    if (el.classList.contains('ql-editor')) {{
      el.innerHTML = '<p>' + text + '</p>';
    }}
  }} else {{
    el.value = text;
  }}

  el.dispatchEvent(new Event("input",  {{ bubbles: true }}));
  el.dispatchEvent(new Event("change", {{ bubbles: true }}));
  el.dispatchEvent(new InputEvent("input", {{ bubbles: true, inputType: 'insertText', data: text }}));

  setTimeout(() => {{
    const btn = document.querySelector(sendSel);
    if (btn && !btn.disabled) {{
      console.log('[AiFreesta] Clicking send button');
      btn.click();
      return;
    }}

    console.log('[AiFreesta] Dispatching Enter');
    const evDown = new KeyboardEvent("keydown", {{
      key: "Enter", code: "Enter", keyCode: 13, which: 13, bubbles: true
    }});
    const evPress = new KeyboardEvent("keypress", {{
      key: "Enter", code: "Enter", keyCode: 13, which: 13, bubbles: true
    }});
    const evUp = new KeyboardEvent("keyup", {{
      key: "Enter", code: "Enter", keyCode: 13, which: 13, bubbles: true
    }});
    el.dispatchEvent(evDown);
    el.dispatchEvent(evPress);
    el.dispatchEvent(evUp);
  }}, 100);

}}, {delay_ms});
"""


def js_clear_chat() -> str:
    """JS to attempt clearing chat interface."""
    return """
const clearSelectors = [
    'button[aria-label*="New chat" i]',
    'button[aria-label*="Clear" i]',
    'a[aria-label*="New chat" i]',
    '[data-testid*="new-chat"]',
    'button:has(svg):contains("New")'
];

for (let sel of clearSelectors) {
    const btn = document.querySelector(sel);
    if (btn) {
        console.log('[AiFreesta] Clicking clear button:', btn);
        btn.click();
        break;
    }
}
console.log('[AiFreesta] Clear attempted');
"""


# ------------------------------ widgets ------------------------------

class BroadcastLineEdit(QLineEdit):
    """Modern styled QLineEdit with built-in clear button [web:95]."""

    def __init__(self, parent_window, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parent_window = parent_window
        
        # Enable built-in clear button [web:95]
        self.setClearButtonEnabled(True)

    def keyPressEvent(self, event: QKeyEvent):
        # Broadcast Qt key event
    
        for view in self.parent_window.views:
            if view is None:
                continue
            target = view.focusProxy() or view
            ev = QKeyEvent(
                event.type(),
                event.key(),
                event.modifiers(),
                event.text(),
                event.isAutoRepeat(),
                event.count(),
            )
            QApplication.postEvent(target, ev)

        super().keyPressEvent(event)
        self.clear()

        # On Enter JS fallback
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            text = self.text()

            if text.strip():
                for i, view in enumerate(self.parent_window.views):
                    if view is None or i >= len(self.parent_window.ai_sites):
                        continue
                    
                    site = self.parent_window.ai_sites[i]
                    js = js_fill_and_send(
                        text,
                        site["input_selector"],
                        site["send_selector"],
                        site["delay_ms"]
                    )
                    view.page().runJavaScript(js)

            self.clear()


class DynamicAIWindow(QMainWindow):
    def __init__(self, ai_sites):
        super().__init__()

        self.setWindowTitle("🤖 Ai Freesta - Multi-AI Chat Interface")
        self.resize(1800, 950)

        self.ai_sites = ai_sites.copy()
        self.views = []

        # Apply modern dark theme
        self.setStyleSheet(DARK_STYLESHEET)

        # Central widget
        self.central = QWidget()
        self.vlayout = QVBoxLayout()
        self.vlayout.setContentsMargins(0, 0, 0, 0)
        self.central.setLayout(self.vlayout)
        self.setCentralWidget(self.central)

        # Status bar with AI count
        self.status_label = QLabel()
        self.statusBar().addPermanentWidget(self.status_label)
        self.statusBar().setStyleSheet("QStatusBar { background-color: #2d2d30; color: #ffffff; border-top: 1px solid #3e3e42; }")

        # Scrollable container
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

        # Initialize
        self._initialize_views()
        self._rebuild_layout()
        self._update_status()

        self.show_startup_notice_once()

    def _initialize_views(self):
        """Create initial views from AI_SITES."""
        for site in self.ai_sites:
            view = make_view(site["url"], mobile=site["mobile"])
            self.views.append(view)

    # --------------------------- input row ---------------------------

    def _create_input_row(self):
        self.input_edit = BroadcastLineEdit(self)
        self.input_edit.setMinimumHeight(50)
        f = self.input_edit.font()
        f.setPointSize(13)
        self.input_edit.setFont(f)
        self.input_edit.setPlaceholderText(
            "✨ Type your message here - broadcasts to all AI chats simultaneously (X button to clear)"
        )

        hbox = QHBoxLayout()
        hbox.setContentsMargins(8, 6, 8, 8)
        hbox.addWidget(self.input_edit)
        self.vlayout.addLayout(hbox)

    def _update_placeholder(self):
        """Update placeholder text with current pane count."""
        self.input_edit.setPlaceholderText(
            f"✨ Broadcasting to {len(self.views)} AI panes - Type your message (X to clear)"
        )

    def _update_status(self):
        """Update status bar."""
        self.status_label.setText(f"   🤖 {len(self.views)} AI Chats Active   |   Ready")

    # ------------------------------- toolbar -------------------------------

    def _create_toolbar(self):
        toolbar = QToolBar("Main Controls")
        toolbar.setMovable(False)
        toolbar.setIconSize(toolbar.iconSize() * 1.2)
        self.addToolBar(toolbar)

        # AI Management
        act_add = QAction("➕", self)
        act_add.triggered.connect(self.add_new_ai)
        act_add.setToolTip("Add a new AI chat site")
        toolbar.addAction(act_add)

        toolbar.addSeparator()

        # Refresh Actions - Opens sites fresh [web:4]
        act_refresh_all = QAction("🔄", self)
        act_refresh_all.triggered.connect(self.refresh_all_panes)
        act_refresh_all.setToolTip("Open all AI sites fresh (clears history)")
        toolbar.addAction(act_refresh_all)

        act_stop = QAction("🛑", self)
        act_stop.triggered.connect(self.stop_all_panes)
        act_stop.setToolTip("Stop loading all pages")
        toolbar.addAction(act_stop)

        act_clear = QAction("Clear All", self)
        act_clear.triggered.connect(self.clear_all_chats)
        act_clear.setToolTip("Attempt to clear all chat histories")
        toolbar.addAction(act_clear)

        # toolbar.addSeparator()

        # # Layout presets
        # act_horz = QAction("▬ Horizontal", self)
        # act_horz.triggered.connect(lambda: self._rebuild_layout("horizontal"))
        # act_horz.setToolTip("Side-by-side layout")
        # toolbar.addAction(act_horz)

        # act_vert = QAction("▥ Vertical", self)
        # act_vert.triggered.connect(lambda: self._rebuild_layout("vertical"))
        # act_vert.setToolTip("Stacked layout")
        # toolbar.addAction(act_vert)

        # act_grid = QAction("⊞ Grid", self)
        # act_grid.triggered.connect(lambda: self._rebuild_layout("grid"))
        # act_grid.setToolTip("2x2 grid layout")
        # toolbar.addAction(act_grid)

        toolbar.addSeparator()

        # Help
        act_help = QAction("❓ Help", self)
        act_help.triggered.connect(self.show_help)
        act_help.setToolTip("Show usage tips")
        toolbar.addAction(act_help)

    # --------------------------- actions ----------------------------

    def refresh_all_panes(self):
        """
        Open all sites fresh by navigating to original URLs [web:4].
        This clears session/history and starts fresh.
        """
        for i, view in enumerate(self.views):
            if view and i < len(self.ai_sites):
                # Use setUrl() to load fresh instead of reload() [web:4][web:92]
                original_url = self.ai_sites[i]["url"]
                view.setUrl(QUrl(original_url))
        self.statusBar().showMessage("♻️ Opening all sites fresh...", 3000)

    def stop_all_panes(self):
        """Stop loading all pages."""
        for view in self.views:
            if view:
                view.stop()
        self.statusBar().showMessage("🛑 Stopped all loading", 2000)

    def clear_all_chats(self):
        """Attempt to clear all chats using JS."""
        reply = QMessageBox.question(
            self,
            "Clear All Chats",
            "This will try to click 'New Chat' buttons on all sites.\n\n"
            "Note: This may not work on all AI sites.\nProceed?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            for view in self.views:
                if view:
                    view.page().runJavaScript(js_clear_chat())
            self.statusBar().showMessage("🗑️ Clear attempted on all panes", 3000)

    def show_help(self):
        """Show help dialog."""
        msg = QMessageBox(self)
        msg.setWindowTitle("Ai Freesta - Help")
        msg.setIcon(QMessageBox.Information)
        msg.setText("🤖 Multi-AI Chat Interface")
        msg.setInformativeText(
            "<b>Features:</b><br>"
            "• Type once, broadcast to all AIs simultaneously<br>"
            "• Dynamically add more AI chat sites<br>"
            "• Switch layouts (Horizontal, Vertical, Grid)<br>"
            "• Refresh, stop, or clear all chats at once<br>"
            "• Built-in text clear button (X) in input field<br><br>"
            
            "<b>Tips:</b><br>"
            "• Click each AI's input box once to focus it<br>"
            "• Click X button to clear input text quickly<br>"
            "• Press F12 in any pane to see Console logs<br>"
            "• Use '+ Add AI' to add custom chat sites<br>"
            "• 🔄 Refresh All opens sites completely fresh<br>"
            "• Clear All may not work on all sites<br>"
            "• Horizontal scrollbar appears when needed<br><br>"
            
            "<b>Troubleshooting:</b><br>"
            "• If Enter doesn't work: Check F12 Console<br>"
            "• Edit selectors in AI_SITES config<br>"
            "• Try '🔄 Refresh All' if pages get stuck<br>"
            "• Refresh opens sites fresh, not just reload"
        )
        msg.exec()

    def add_new_ai(self):
        """Dialog to add a new AI site dynamically."""
        url, ok = QInputDialog.getText(
            self,
            "Add New AI Chat",
            "Enter the AI chat URL:\n(e.g., https://claude.ai)"
        )
        
        if not ok or not url.strip():
            return

        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        name, ok = QInputDialog.getText(
            self,
            "AI Name",
            "Enter a display name:",
            text=url.split("//")[-1].split("/")[0]
        )
        
        if not ok or not name.strip():
            name = url.split("//")[-1].split("/")[0]

        new_site = {
            "name": name,
            "url": url,
            "mobile": False,
            "input_selector": "textarea, [contenteditable='true'], input[type='text']",
            "send_selector": "button[type='submit'], button[aria-label*='send' i]",
            "delay_ms": 200,
        }

        self.ai_sites.append(new_site)
        new_view = make_view(url, mobile=False)
        self.views.append(new_view)

        self._rebuild_layout()
        self._update_placeholder()
        self._update_status()

        self.statusBar().showMessage(f"Added {name}!", 5000)

    # ------------------------------- layouts -------------------------------

    def _rebuild_layout(self, style="horizontal"):
        """Rebuild splitter with all current views."""
        if self.current_root_splitter is not None:
            self.splitter_layout.removeWidget(self.current_root_splitter)
            self.current_root_splitter.setParent(None)

        if not self.views:
            return

        if style == "horizontal":
            root = QSplitter(Qt.Horizontal)
            for view in self.views:
                root.addWidget(view)
            root.setSizes([1] * len(self.views))

        elif style == "vertical":
            root = QSplitter(Qt.Vertical)
            for view in self.views:
                root.addWidget(view)
            root.setSizes([1] * len(self.views))

        elif style == "grid":
            root = QSplitter(Qt.Horizontal)
            
            left = QSplitter(Qt.Vertical)
            for i in range(0, len(self.views), 2):
                left.addWidget(self.views[i])
            
            right = QSplitter(Qt.Vertical)
            for i in range(1, len(self.views), 2):
                right.addWidget(self.views[i])
            
            root.addWidget(left)
            if right.count() > 0:
                root.addWidget(right)
            
            root.setSizes([1, 1])

        else:
            root = QSplitter(Qt.Horizontal)
            for view in self.views:
                root.addWidget(view)
            root.setSizes([1] * len(self.views))

        root.setChildrenCollapsible(False)
        self.current_root_splitter = root
        self.splitter_layout.addWidget(root)

        min_total_width = MIN_PANE_WIDTH * len(self.views)
        self.splitter_container.setMinimumWidth(min_total_width)

        self.statusBar().showMessage(f"📐 Layout changed to {style}", 2000)

    # ------------------------------ notice ------------------------------

    def show_startup_notice_once(self):
        settings = QSettings("Ai Freesta", "Ai Freesta")
        if settings.value("hide_notice", False, type=bool):
            return

        msg = QMessageBox(self)
        msg.setWindowTitle("Welcome to Ai Freesta")
        msg.setIcon(QMessageBox.Information)
        msg.setText(
            f"🚀 Started with {len(self.views)} AI chats\n"
            "Type once, get responses from all AIs!"
        )
        msg.setInformativeText(
            "<b>Quick Start:</b><br>"
            "1. Click each AI's input box once (to focus)<br>"
            "2. Type in the bottom bar<br>"
            "3. Press Enter to broadcast<br>"
            "4. Click X button to clear text<br><br>"
            
            "<b>Useful Buttons:</b><br>"
            "• <b>🔄 Refresh All</b> - Open sites fresh (new session)<br>"
            "• <b>🛑 Stop All</b> - Stop loading<br>"
            "• <b>🗑️ Clear All</b> - Try to clear chats<br>"
            "• <b>➕ Add AI</b> - Add more chat sites<br>"
            "• <b>X in input</b> - Clear typed text<br><br>"
            
            "Click <b>❓ Help</b> button for more info!"
        )

        cb = QCheckBox("Don't show again")
        msg.setCheckBox(cb)

        msg.exec()

        if cb.isChecked():
            settings.setValue("hide_notice", True)


# ------------------------------- main -------------------------------

def main():
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle("Fusion")
    
    window = DynamicAIWindow(AI_SITES)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
