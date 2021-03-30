import sys
import warnings

from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import Qt, QProcess
from PyQt5.QtGui import QMovie

import analyze
import collect
import images
import log
import util


class Ui(QtWidgets.QMainWindow):
    def __init__(self):
        super(Ui, self).__init__()
        uic.loadUi('BasicForm.ui', self)
        self.updateBtn.clicked.connect(self.update_stream_info)
        self.harvestBtn.clicked.connect(self.harvest)
        self.statusLabel.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.video_id = ""
        self.chat_emotes = {}
        self.clear_emote_area()
        self.process = None
        self.process_id = ""

    def disable_button(self, button):
        button.setDisabled(False)
        button.repaint()

    def invalid_id(self):
        self.update_status("Invalid VOD ID!")
        self.updateBtn.setDisabled(False)
        self.updateBtn.repaint()

    def update_stream_info(self):
        self.updateBtn.setDisabled(True)
        self.updateBtn.repaint()
        video_id = self.vodEntry.text()
        if not video_id or not collect.update_video_info(video_id):
            self.invalid_id()
            return
        else:
            self.harvestBtn.setDisabled(True)
            self.harvestBtn.repaint()
            self.update_status("Fetching stream info...")
            self.video_id = video_id
            chat_emotes = collect.get_available_emotes()
            if chat_emotes is None:
                self.invalid_id()
                return

            self.titleLabel.setText(collect.video_info.title)
            self.channelLabel.setText(collect.video_info.user_name)
            self.lengthLabel.setText(collect.video_info.duration)
            self.chat_emotes = chat_emotes

            urls = images.missing_emotes(chat_emotes)

            try:
                if urls:
                    self.update_status("Downloading images...")
                    images.get_images(urls)
            except Exception as e:
                print(e)

            self.display_emotes(chat_emotes)
            self.update_status("")

        self.set_harvest_text(self.video_id)
        self.updateBtn.setDisabled(False)

    def download_process(self):
        try:
            if self.process is None:
                self.process = QProcess()
                self.process_id = self.video_id
                self.process.readyReadStandardOutput.connect(self.handle_stdout)
                self.process.readyReadStandardError.connect(self.handle_stderr)
                self.process.stateChanged.connect(self.handle_state)
                self.process.finished.connect(self.process_finished)  # Clean up once complete.
                self.process.start(sys.executable, ["download.py", self.video_id])
                self.set_harvest_text(self.video_id)
        except Exception as e:
            print(e)

    def handle_stderr(self):
        try:
            data = self.process.readAllStandardError()
            stderr = bytes(data).decode("utf8")
            #self.update_status(stderr)
            print(stderr)
        except Exception as e:
            print(e)

    def handle_stdout(self):
        try:
            data = self.process.readAllStandardOutput()
            stdout = bytes(data).decode("utf8")
            if "%" in stdout:
                self.update_status("Downloading: " + stdout.split()[-1])
        except Exception as e:
            print(e)

    def handle_state(self, state):
        states = {
            QProcess.NotRunning: 'Not running',
            QProcess.Starting: 'Starting',
            QProcess.Running: 'Running',
        }
        state_name = states[state]

    def process_finished(self):
        self.process = None
        self.harvestBtn.setDisabled(False)
        self.set_harvest_text(self.video_id)
        self.update_status("Downloaded video: " + self.process_id)

    def enable_download(self, text):
        self.harvestBtn.setText(text)
        self.harvestBtn.setEnabled(self.process is None)

    def is_downloading(self, video_id):
        return self.process is not None and self.process_id == video_id

    def set_harvest_text(self, video_id):
        try:
            log_exists = log.chat_log_exists(video_id)
            if log_exists or self.is_downloading(video_id):
                self.harvestBtn.setText("Analyze")
                self.harvestBtn.setEnabled(True)
            else:
                self.enable_download("Download")

            if log.cursor_update(video_id) and self.process is None:
                self.enable_download("Sync")

            self.harvestBtn.repaint()
        except Exception as e:
            print(e)

    def harvest(self):
        self.harvestBtn.setDisabled(True)
        self.harvestBtn.repaint()
        filters = self.filterText.toPlainText().split()
        if self.harvestBtn.text() == "Download":
            self.update_status("Downloading:")
            self.download_process()
        elif self.harvestBtn.text() == "Sync":
            self.update_status("Syncing latest changes...")
            self.download_process()
        else:
            self.update_status("Analyzing...")
            data, invalid = log.parse_vod_log(self.video_id, self.chat_emotes, filters, int(self.windowSize.text()))
            self.harvestBtn.setDisabled(False)
            self.harvestBtn.repaint()
            if invalid is None:
                self.update_status("")
                analyze.plot_video_data(self.video_id, data, filters, int(self.showMax.text()), int(self.linkOffset.text()))
            else:
                self.update_status("Error: ' {} ' is not a valid filter".format(invalid))

    def update_status(self, message):
        self.statusLabel.repaint()
        self.statusLabel.setText(message)
        self.statusLabel.repaint()

    def clear_emote_area(self):
        emote_area = self.scrollAreaWidgetContents.layout()
        while emote_area.count():
            item = emote_area.takeAt(0)
            widget = item.widget()
            widget.setParent(None)
            widget.deleteLater()

        # Remove existing items in scroll area GridLayout
        for i in reversed(range(emote_area.count())):
            emote_area.itemAt(i).widget().setParent(None)

        self.scrollAreaWidgetContents.repaint()

    def display_emotes(self, chat_emotes):
        emote_area = self.scrollAreaWidgetContents.layout()
        self.clear_emote_area()
        names = sorted(chat_emotes.keys(), key=lambda s: s.lower())
        for name in names:
            movie = QMovie(images.get_path(chat_emotes[name]))
            label = QtWidgets.QLabel()
            label.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
            label.setMovie(movie)
            # Ignore isn't working...
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                movie.start()
            text = QtWidgets.QLabel()
            text.setText(util.get_normal_name(name))
            text.setTextInteractionFlags(Qt.TextSelectableByMouse)

            emote_area.addWidget(label)
            emote_area.addWidget(text)

def create_qt_window():
    app = QtWidgets.QApplication(sys.argv)  # Create an instance of QtWidgets.QApplication
    window = Ui()
    window.show()
    sys.exit(app.exec_())