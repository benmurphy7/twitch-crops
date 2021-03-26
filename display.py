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
        self.video_id = ""
        self.chat_emotes = {}
        self.clear_emote_area()
        self.process = None
        self.downloading = False

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
        self.update_status("Fetching stream info...")
        video_id = self.vodEntry.text()
        if len(video_id) != 9:
            self.invalid_id()
            return
        else:
            self.set_harvest_text(video_id)
            if self.video_id == video_id:
                pass
                #self.update_status("Already viewing VOD ID: " + self.video_id)
            else:
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

                missing = images.missing_emotes(chat_emotes)
                to_download = len(missing)
                try:
                    for count, emote in enumerate(missing):
                        images.get_image(chat_emotes[emote])
                        self.update_status("Downloading image {}/{}".format(count+1,to_download))
                        QApplication.processEvents()

                except Exception as e:
                    print(e)

                self.display_emotes(chat_emotes)

        # Simulated wait for action completion
        #QTimer.singleShot(5000, lambda: self.updateBtn.setEnabled(True))
        self.updateBtn.setDisabled(False)
        if self.process is None:
            self.harvestBtn.setDisabled(False)
        self.update_status("")

    def download_process(self):
        try:
            if self.process is None:  # No process running.
                self.downloading = True
                self.process = QProcess()  # Keep a reference to the QProcess (e.g. on self) while it's running.
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
        self.update_status("")

    def set_harvest_text(self, video_id):
        if not main.chat_log_exists(video_id):
            self.harvestBtn.setText("Download")
        else:
            self.harvestBtn.setText("Analyze")
        self.harvestBtn.repaint()

    def harvest(self):
        self.harvestBtn.setDisabled(True)
        self.harvestBtn.repaint()
        filters = self.filterText.toPlainText().split()
        if not main.chat_log_exists(self.video_id):
            self.update_status("Downloading:")
            self.download_process()
        if self.process is None:
            data = main.parse_vod_log(self.video_id, self.chat_emotes, filters)
            self.downloading = False
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

#TODO: Parallel request threads for image downloading
#TODO: Handle different emote images with same name (use emoteID)
#TODO: ALlow analysis of existing logs while download process is running
