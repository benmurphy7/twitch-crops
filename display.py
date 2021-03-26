import sys

from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import Qt, QProcess
from PyQt5.QtGui import QMovie
from PyQt5.QtWidgets import QApplication

import collect
import images
import main


class Ui(QtWidgets.QMainWindow):
    def __init__(self):
        super(Ui, self).__init__() # Call the inherited classes __init__ method
        uic.loadUi('BasicForm.ui', self) # Load the .ui file
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
        self.harvestBtn.setDisabled(True)
        self.harvestBtn.repaint()
        video_id = self.vodEntry.text()
        if len(video_id) != 9:
            self.invalid_id()
            return
        else:
            if self.video_id == video_id:
                pass
            else:
                self.update_status("Fetching stream info...")
                self.video_id = video_id
                chat_emotes, video_title, channel = collect.get_available_emotes(video_id)
                if channel == "" and video_title == "":
                    self.invalid_id()
                    return
                main.video_title = video_title
                main.channel = channel
                main.video_id = video_id

                self.titleLabel.setText(video_title)
                self.channelLabel.setText(channel)
                self.chat_emotes = chat_emotes

                urls = images.missing_emotes(chat_emotes)

                try:
                    if len(urls) > 0:
                        self.update_status("Downloading images...")
                        images.get_images(urls)
                except Exception as e:
                    print(e)

                self.display_emotes(chat_emotes)
                self.update_status("")

        self.set_harvest_text(video_id)
        self.updateBtn.setDisabled(False)

    def download_process(self):
        try:
            if self.process is None:  # No process running.
                self.process = QProcess()  # Keep a reference to the QProcess (e.g. on self) while it's running.
                self.process_id = self.video_id
                self.process.readyReadStandardOutput.connect(self.handle_stdout)
                self.process.readyReadStandardError.connect(self.handle_stderr)
                self.process.stateChanged.connect(self.handle_state)
                self.process.finished.connect(self.process_finished)  # Clean up once complete.
                self.process.start("tcd", ['--video', self.video_id, '--format', 'irc', '--output', main.download_dir])
        except Exception as e:
            print(e)

    def handle_stderr(self):
        try:
            data = self.process.readAllStandardError()
            stderr = bytes(data).decode("utf8")
            self.update_status(stderr)
        except Exception as e:
            print(e)

    def handle_stdout(self):
        try:
            data = self.process.readAllStandardOutput()
            stdout = bytes(data).decode("utf8")
            if "%" not in stdout:
                print("TCD output: " + stdout)
            else:
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

    def set_harvest_text(self, video_id):
        if not main.chat_log_exists(video_id):
            self.harvestBtn.setText("Download")
            self.harvestBtn.setEnabled(self.process is None)
        else:
            self.harvestBtn.setText("Analyze")
            self.harvestBtn.setEnabled(True)
        self.harvestBtn.repaint()

    def harvest(self):
        self.harvestBtn.setDisabled(True)
        self.harvestBtn.repaint()
        filters = self.filterText.toPlainText().split()
        if not main.chat_log_exists(self.video_id):
            self.update_status("Downloading:")
            self.download_process()
        else:
            self.update_status("Analyzing...")
            data = main.parse_vod_log(self.video_id, self.chat_emotes, filters)
            self.update_status("")
            self.harvestBtn.setDisabled(False)
            self.harvestBtn.repaint()
            main.plot_video_data(self.video_id, data, 50)

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
            movie.start()

            text = QtWidgets.QLabel()
            text.setText(name)
            text.setTextInteractionFlags(Qt.TextSelectableByMouse)

            emote_area.addWidget(label)
            emote_area.addWidget(text)

def create_qt_window():
    app = QtWidgets.QApplication(sys.argv)  # Create an instance of QtWidgets.QApplication
    window = Ui()
    window.show()
    sys.exit(app.exec_())

#TODO: ALlow analysis of existing logs while download process is running
