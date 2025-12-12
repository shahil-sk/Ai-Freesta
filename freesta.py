import sys
from PySide6.QtCore import QUrl, Qt
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QToolBar,
    QLineEdit,
)
from PySide6.QtGui import QAction, QKeyEvent
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QMessageBox, QCheckBox
from PySide6.QtCore import QSettings


# URLs for the three panes
START_URLS = [
    "https://chatgpt.com",        # Pane 0
    "https://grok.com",          # Pane 1
    "https://gemini.google.com", # Pane 2
]

# Desktop user-agent (Chrome on Windows)
DESKTOP_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# Mobile user-agent (Chrome on Android)
MOBILE_UA = (
    "Mozilla/5.0 (Linux; Android 10; Mobile) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Mobile Safari/537.36"
)


def make_view(url: str, *, mobile: bool) -> QWebEngineView:
    """Create a QWebEngineView with a chosen user-agent."""
    view = QWebEngineView()
    profile = view.page().profile()
    ua = MOBILE_UA if mobile else DESKTOP_UA
    profile.setHttpUserAgent(ua)
    view.setUrl(QUrl(url))
    return view


class BroadcastLineEdit(QLineEdit):
    """
    QLineEdit that mirrors every key press into a list of QWebEngineViews
    as real keyboard events (including Enter).
    """

    def __init__(self, target_views, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.target_views = target_views

    def keyPressEvent(self, event: QKeyEvent):
    # Broadcast to panes first
        for view in self.target_views:
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

        # Update the line edit itself
        super().keyPressEvent(event)

        # Clear when Enter pressed
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.clear()



class ThreePaneWindow(QMainWindow):
    def __init__(self, urls):
        super().__init__()

        self.setWindowTitle("Ai Freesta")
        self.resize(1600, 900)

        # Create three browser views (tweak mobile/desktop as you prefer)
        self.views = [
            make_view(urls[0], mobile=True),   # ChatGPT
            make_view(urls[1], mobile=False),   # Grok
            make_view(urls[2], mobile=False),   # Gemini
        ]

        # Central widget and main vertical layout
        self.central = QWidget()
        self.vlayout = QVBoxLayout()
        self.vlayout.setContentsMargins(0, 0, 0, 0)
        self.central.setLayout(self.vlayout)
        self.setCentralWidget(self.central)

        # Container for the splitter (so input row stays at bottom)
        self.splitter_container = QWidget()
        self.splitter_layout = QVBoxLayout()
        self.splitter_layout.setContentsMargins(0, 0, 0, 0)
        self.splitter_container.setLayout(self.splitter_layout)
        self.vlayout.addWidget(self.splitter_container)

        # Shared input row at the bottom
        self._create_input_row()

        # Toolbar with layout presets
        self.current_root_splitter = None
        self._create_toolbar()

        # Default layout: 3 horizontal
        self.set_layout_3_horizontal()
        self.show_startup_notice_once()


    # --------------------------- shared input row ---------------------------

    def _create_input_row(self):
        self.input_edit = BroadcastLineEdit(self.views)
        # Make it taller + easier to read
        self.input_edit.setMinimumHeight(46)
        f = self.input_edit.font()
        f.setPointSize(14)
        self.input_edit.setFont(f)

        self.input_edit.setPlaceholderText(
            "Type here – keystrokes (including Enter) go live to all 3 panes. "
            "Click each site’s input once so it has focus."
        )

        hbox = QHBoxLayout()
        hbox.setContentsMargins(4, 4, 4, 4)
        hbox.addWidget(self.input_edit)

        # Add input bar as last item => bottom of window
        self.vlayout.addLayout(hbox)

    # ------------------------------- toolbar -------------------------------

    def _create_toolbar(self):
        toolbar = QToolBar("Layouts")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        act_horz = QAction("3 Horizontal", self)
        act_horz.triggered.connect(self.set_layout_3_horizontal)
        toolbar.addAction(act_horz)

        act_vert = QAction("3 Vertical", self)
        act_vert.triggered.connect(self.set_layout_3_vertical)
        toolbar.addAction(act_vert)

        act_1plus2 = QAction("1 + 2 Grid", self)
        act_1plus2.triggered.connect(self.set_layout_1_plus_2)
        toolbar.addAction(act_1plus2)

    # ------------------------------- layouts -------------------------------

    def _set_root_splitter(self, splitter: QSplitter):
        # Remove old splitter from the container
        if self.current_root_splitter is not None:
            self.splitter_layout.removeWidget(self.current_root_splitter)
            self.current_root_splitter.setParent(None)

        self.current_root_splitter = splitter
        self.splitter_layout.addWidget(splitter)

    def set_layout_3_horizontal(self):
        """Three panes side-by-side horizontally."""
        v1, v2, v3 = self.views
        root = QSplitter(Qt.Horizontal)
        root.addWidget(v1)
        root.addWidget(v2)
        root.addWidget(v3)
        root.setSizes([1, 1, 1])
        self._set_root_splitter(root)

    def set_layout_3_vertical(self):
        """Three panes stacked vertically."""
        v1, v2, v3 = self.views
        root = QSplitter(Qt.Vertical)
        root.addWidget(v1)
        root.addWidget(v2)
        root.addWidget(v3)
        root.setSizes([1, 1, 1])
        self._set_root_splitter(root)

    def set_layout_1_plus_2(self):
        """Left: pane 0 big. Right: panes 1 and 2 stacked."""
        v1, v2, v3 = self.views

        right = QSplitter(Qt.Vertical)
        right.addWidget(v2)
        right.addWidget(v3)
        right.setSizes([1, 1])

        root = QSplitter(Qt.Horizontal)
        root.addWidget(v1)
        root.addWidget(right)
        root.setSizes([2, 1])  # left a bit wider
        self._set_root_splitter(root)

    def show_startup_notice_once(self):
        settings = QSettings("Ai Freesta", "Ai Freesta")  # org, app name
        if settings.value("hide_notice", False, type=bool):
            return

        msg = QMessageBox(self)
        msg.setWindowTitle("Ai Freesta")
        msg.setIcon(QMessageBox.Information)
        msg.setText("Clear all the tab notifications and pop-ups before typing.")
        msg.setInformativeText("Tip: Click inside each tab’s input box once to focus it.")

        cb = QCheckBox("Don't show again")
        msg.setCheckBox(cb)

        msg.exec()

        if cb.isChecked():
            settings.setValue("hide_notice", True)


def main():
    app = QApplication(sys.argv)
    window = ThreePaneWindow(START_URLS)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
