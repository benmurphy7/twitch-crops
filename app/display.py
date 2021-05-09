import sys

from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import Qt, QProcess
from PyQt5.QtGui import QMovie
from PyQt5.QtWidgets import QApplication

from common import util, config
from data import analyze, collect, images, logs


class Ui(QtWidgets.QMainWindow):
    def __init__(self):
        super(Ui, self).__init__()
        uic.loadUi(config.ui_template, self)
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
            self.lengthLabel.setText(util.space_timestamp(collect.video_info.duration))
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
                self.process.finished.connect(self.process_finished)
                self.process.start(sys.executable, [config.download_script, self.video_id])
                self.set_harvest_text(self.video_id)
        except Exception as e:
            print(e)

    def handle_stderr(self):
        try:
            data = self.process.readAllStandardError()
            stderr = bytes(data).decode("utf8")
            # self.update_status(stderr)
            print(stderr)
        except Exception as e:
            print(e)

    def handle_stdout(self):
        try:
            data = self.process.readAllStandardOutput()
            stdout = bytes(data).decode("utf8")
            if "%" in stdout:
                self.update_status("Downloading [{}] - {}".format(self.process_id, stdout.split()[-1]))
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
        status = "Download complete: "
        if not logs.chat_log_exists(self.process_id):
            status = "Chat data currently unavailable: "
        self.update_status(status + self.process_id)

    def enable_download(self, text):
        self.harvestBtn.setText(text)
        self.harvestBtn.setEnabled(self.process is None)

    def is_downloading(self, video_id):
        return self.process is not None and self.process_id == video_id

    def set_harvest_text(self, video_id):
        try:
            log_exists = logs.chat_log_exists(video_id)
            if log_exists or self.is_downloading(video_id):
                self.harvestBtn.setText("Analyze")
                self.harvestBtn.setEnabled(True)
            else:
                self.enable_download("Download")

            if logs.cursor_update(video_id) and self.process is None:
                self.enable_download("Sync")

            self.harvestBtn.repaint()

        except Exception as e:
            print(e)

    def harvest(self):
        self.harvestBtn.setDisabled(True)
        self.harvestBtn.repaint()
        filters = self.get_filter_list()
        if self.harvestBtn.text() == "Download":
            self.update_status("Downloading [{}] ...".format(self.video_id))
            self.download_process()
        elif self.harvestBtn.text() == "Sync":
            self.update_status("Syncing latest changes...")
            self.download_process()
        else:
            if not logs.chat_log_exists(self.video_id):
                self.harvestBtn.setDisabled(False)
                self.harvestBtn.repaint()
                return
            self.update_status("Analyzing...")
            data, filters, invalid = logs.parse_vod_log(self.video_id, self.chat_emotes, filters,
                                                        int(self.windowSize.text()))
            self.harvestBtn.setDisabled(False)
            self.harvestBtn.repaint()
            if invalid is None:
                self.update_status("")
                analyze.plot_video_data(self.video_id, data, filters, int(self.showMax.text()),
                                        int(self.linkOffset.text()))
            else:
                self.update_status("Error: ' {} ' is not a valid filter".format(invalid))

    def get_filter_list(self):
        filter_list = []
        filters = self.filterText.toPlainText().split()
        # Remove duplicates
        [filter_list.append(x) for x in filters if x not in filter_list]
        return filter_list

    def update_status(self, message):
        self.statusLabel.repaint()
        self.statusLabel.setText(message)
        self.statusLabel.repaint()
        app.processEvents()

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
        cols = 8
        x, y = 0, 0
        for name in names:
            movie = QMovie(images.get_path(chat_emotes[name]))
            label = QtWidgets.QLabel()
            label.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
            label.setMovie(movie)

            # TODO: Silence libpng warning, or remove incorrect sRGB profiles
            movie.start()

            text = QtWidgets.QLabel()
            text.setText(util.get_normal_name(name))
            text.setTextInteractionFlags(Qt.TextSelectableByMouse)

            emote_area.addWidget(label, y, x)
            emote_area.addWidget(text, y, x + 1)

            x += 2
            if x >= cols:
                x = 0
                y += 1


window: Ui = None
app: QApplication = None


def create_qt_window():
    global window
    global app

    app = QtWidgets.QApplication(sys.argv)
    window = Ui()
    window.show()
    sys.exit(app.exec_())
