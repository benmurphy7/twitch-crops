import copy
import sys
import time

from PyQt5 import uic
from PyQt5.QtCore import Qt, QProcess, QTimer, QObject, pyqtSignal, QThread, qInstallMessageHandler
from PyQt5.QtGui import QMovie
from PyQt5.QtWidgets import QApplication, QVBoxLayout, QFrame, QLabel, QMainWindow

from common import util, config
from data import analyze, collect, images, logs


class Ui(QMainWindow):
    def __init__(self):
        super(Ui, self).__init__()
        uic.loadUi(config.ui_template, self)
        self.video_id = ""
        self.chat_emotes = {}
        self.clear_emote_area()
        self.process = None
        self.process_id = ""
        self.update_id = False
        self.lock_emotes = False
        self.downloading = False

        self.thread = None
        self.worker = None

        self.search_timer = QTimer()
        self.search_timer_length = 0
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.display_emotes)

        self.updateBtn.clicked.connect(self.update_stream_info)
        self.harvestBtn.clicked.connect(self.harvest)
        self.emoteSearch.textChanged.connect(self.set_search_timer)
        self.statusLabel.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.update_ids()
        self.vodEntry.activated.connect(self.update_stream_info)
        self.vodEntry.setCurrentText('')

        self.singleEmotesCheckbox

        qInstallMessageHandler(self.handle_msg)

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
        video_id = self.vodEntry.currentText()
        self.lock_emotes = True
        self.emoteSearch.setText("")
        if not video_id or not collect.update_video_info(video_id):
            self.invalid_id()
            return
        else:
            self.harvestBtn.setDisabled(True)
            self.harvestBtn.repaint()
            self.update_status("Fetching stream info ...")
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
                    self.update_status("Downloading images ...")
                    images.get_images(urls)
            except Exception as e:
                print(e)

            self.lock_emotes = False
            self.display_emotes()
            self.update_status("")

        self.set_harvest_text(self.video_id)
        self.updateBtn.setDisabled(False)

    def download_process(self):
        try:
            if not self.downloading:
                if collect.update_video_info(self.video_id):
                    if not logs.chat_log_exists(self.video_id) or logs.cursor_update(self.video_id):
                        self.downloading = True
                        self.process_id = self.video_id
                        self.update_id = True

                        self.thread = QThread(parent=self)
                        self.worker = Worker()

                        self.worker.moveToThread(self.thread)

                        self.thread.started.connect(self.worker.run)
                        self.worker.progress.connect(self.update_status)
                        self.worker.finished.connect(self.process_finished)

                        self.thread.start()
                        self.set_harvest_text(self.video_id)

                        while self.update_id:
                            time.sleep(0.5)
                            if logs.chat_log_exists(self.process_id):
                                self.update_ids()
                                self.update_id = False

        except Exception as e:
            print(e)

    def handle_msg(msg_type, idx, msg_log_context, msg_string):
        pass

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
                if self.update_id:
                    self.update_ids()
                    self.update_id = False

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
        self.downloading = False
        self.harvestBtn.setDisabled(False)
        self.set_harvest_text(self.video_id)
        status = "Download complete: "
        if not logs.chat_log_exists(self.process_id):
            status = "Chat data currently unavailable: "
        self.update_status(status + "[ {} ]".format(self.process_id))

        self.thread.quit
        self.worker.deleteLater
        self.thread.deleteLater

    def enable_download(self, text):
        self.harvestBtn.setText(text)
        self.harvestBtn.setEnabled(self.downloading is False)

    def is_downloading(self, video_id):
        return self.downloading and self.process_id == video_id

    def update_ids(self):
        self.vodEntry.clear()
        self.vodEntry.addItems([s.strip(".log") for s in logs.get_existing_logs()])

    def set_harvest_text(self, video_id):
        try:
            log_exists = logs.chat_log_exists(video_id)
            if log_exists or self.is_downloading(video_id):
                self.harvestBtn.setText("Analyze")
                self.harvestBtn.setEnabled(True)
            else:
                self.enable_download("Download")

            if self.downloading is False and logs.cursor_update(video_id):
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
            self.update_status("Syncing latest changes ...")
            self.download_process()
        else:
            if not logs.chat_log_exists(self.video_id):
                self.harvestBtn.setDisabled(False)
                self.harvestBtn.repaint()
                return
            self.update_status("Analyzing ...")
            data, valid, invalid, stats = logs.parse_vod_log(self.video_id, self.chat_emotes, filters,
                                                        int(self.windowSize.text()))
            self.harvestBtn.setDisabled(False)
            self.harvestBtn.repaint()
            if invalid is None:
                self.update_status("")
                analyze.plot_video_data(collect.video_info, data, valid, stats, int(self.showMax.text()),
                                        int(self.linkOffset.text()))
            else:
                self.update_status("Error: ' {} ' is not a valid filter".format(invalid))

    def get_filter_list(self):
        filter_list = []
        filters = self.filterText.toPlainText().split()
        # Remove duplicates
        [filter_list.append(x) for x in filters if x not in filter_list]
        return filter_list

    def set_search_timer(self):
        self.search_timer.start(self.search_timer_length)

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

    def display_emotes(self):
        if not self.lock_emotes:
            emote_area = self.scrollAreaWidgetContents.layout()
            self.clear_emote_area()
            names = sorted(self.chat_emotes.keys(), key=lambda s: s.lower())
            cols = 4
            x, y = 0, 0
            for name in names:
                if self.emoteSearch.text().lower() in name.lower():

                    vbox = QVBoxLayout()
                    vbox.setAlignment(Qt.AlignCenter)
                    frame = QFrame()
                    frame.setLayout(vbox)

                    movie = QMovie(images.get_path(self.chat_emotes[name]))
                    gif = QLabel()
                    gif.setAlignment(Qt.AlignHCenter)
                    gif.setMovie(movie)
                    movie.start()

                    text = QLabel(util.wrap_text(name))
                    text.setAlignment(Qt.AlignHCenter)
                    text.setTextInteractionFlags(Qt.TextSelectableByMouse)

                    vbox.addWidget(gif)
                    vbox.addWidget(text)

                    emote_area.addWidget(frame, y, x)

                    x += 1
                    if x >= cols:
                        x = 0
                        y += 1


class Worker(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(str)

    def run(self):
        logs.download_log(copy.deepcopy(collect.video_info), self.progress)
        self.finished.emit()


window: Ui = None
app: QApplication = None


def create_qt_window():
    global window
    global app

    app = QApplication(sys.argv)
    window = Ui()
    window.show()
    sys.exit(app.exec_())
