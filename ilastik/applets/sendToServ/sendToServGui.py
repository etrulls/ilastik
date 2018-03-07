import os

from PyQt5 import uic
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtWidgets import QVBoxLayout, QSpacerItem, QSizePolicy, QPushButton, QLabel, QTextEdit, QSlider
from PyQt5.QtGui import QColor, QTextCursor

from ilastik.applets.layerViewer.layerViewerGui import LayerViewerGui
from .serverProgressProber import ServerProgressProber
from .serverUsageProber import ServerUsageProber
from .communicateWithServer import CommunicateWithServer
from volumina.api import ColortableLayer, LazyflowSource
import h5py
import tempfile
import threading
import numpy as np


class SendToServGui(LayerViewerGui):
    # Default value to threshold the output (should send something instead?)
    THRESHOLD_DEFAULT = 0
    THRESHOLD_SCALING = 100

    # Time between each probe call to fetch server status
    LOG_PROBE_DELAY = 5
    USAGE_PROBE_DELAY = 5

    def appletDrawer(self):
        return self._drawer

    def __init__(self, parentApplet, topLevelOperatorView):
        self.topLevelOperatorView = topLevelOperatorView
        super(SendToServGui, self).__init__(parentApplet, self.topLevelOperatorView)
        self.applet = self.topLevelOperatorView.parent.parent.sendToServApplet
        self._colorTable16 = self._createDefault16ColorColorTable()

    def initAppletDrawerUi(self):
        # Load ui file
        localDir = os.path.split(__file__)[0]
        self._drawer = uic.loadUi(localDir + "/drawer.ui")

        # Start a probe to get server usage and keep it running
        self.labelUsage = QLabel("Server load: N/A\nMemory: N/A")
        creds = self.topLevelOperatorView.InputCreds
        self.thread_usage = ServerUsageProber(creds, self.USAGE_PROBE_DELAY)
        self.thread_usage.signal_server_usage.connect(self.updateServerUsage)
        self.thread_usage.start()

        self.status = QLabel("Status: Ready to send")
        self.button = QPushButton("Send request")
        self.button.setMaximumSize(QSize(120, 40))
        self.button.clicked.connect(self.sendRequest)

        self.thresholdLabel = QLabel('Binarization threshold: ' + str(self.THRESHOLD_DEFAULT / self.THRESHOLD_SCALING))
        self.thresholdWidget = QSlider(Qt.Horizontal)
        self.thresholdWidget.setValue(self.THRESHOLD_DEFAULT)
        self.thresholdWidget.valueChanged.connect(self.changeThreshold)
        self.thresholdWidget.setMaximum(750)
        self.thresholdWidget.setMinimum(-750)
        self.thresholdWidget.setDisabled(True)

        # Server progress text field
        self.serverProgress = QTextEdit()
        # fs = self.serverProgress.fontPointSize()
        # print('font size {}'.format(fs))
        # self.serverProgress.setFontPointSize(fs - 3)
        # Cannot do relative size, unfortunately?
        self.serverProgress.setFontPointSize(10)
        self.serverProgress.setMinimumSize(QSize(200, 250))
        self.serverProgress.setReadOnly(True)

        # Layout
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.addWidget(self.button)
        layout.addSpacing(10)
        layout.addWidget(self.labelUsage)
        layout.addWidget(self.status)
        layout.addSpacing(10)
        layout.addWidget(self.serverProgress)
        layout.addSpacing(10)
        layout.addWidget(self.thresholdLabel)
        layout.addWidget(self.thresholdWidget)
        layout.addStretch(1)

        # Apply layout to the drawer
        self._drawer.setLayout(layout)

    def changeThreshold(self):
        resultArray = self.topLevelOperatorView.Output.value
        thresholded = np.full(resultArray.shape, 2, dtype=np.uint8)
        th = self.thresholdWidget.value() / self.THRESHOLD_SCALING
        thresholded[resultArray < th] = 1
        # thresholded[resultArray >= th] = 2
        self.topLevelOperatorView.OutputThreshold.setValue(thresholded)
        self.thresholdLabel.setText('Binarization threshold: ' + str(self.thresholdWidget.value() / self.THRESHOLD_SCALING))

    def updateStatus(self, line, isPermanent):
        """
        Called by threads to update the text of the label (displayed on the left of the UI).
        Reminder: PyQt widgets are not thread-safe.
        - line : line to append.
        - isPermanent : True if line is supposed to stay. False if it's supposed to be deleted after the next label update.
        """
        if(isPermanent):
            self.status.setText(self.status.text() + line)
        else:
            self.status.setText(line)

    def setOutput(self):
        """
        Called when communication with server is over (success).
        Sets the server response as the result.
        """
        # mode = self.topLevelOperatorView.InputSelectedMode.value
        # if mode == 'testOldData':
        #     # Recover the image from the server and display it
        #     # First dump it on disk, then load and force 3D view
        #     # Delete it if it exists (files are not closing properly?)
        #     tmpDir = tempfile.gettempdir()
        #     tmpDir = os.path.join(tmpDir, 'contextFeaturesResult')
        #     tmpFile = os.path.join(tmpDir, 'tmp.h5')
        #     if os.path.isfile(tmpFile):
        #         os.remove(tmpFile)
        #     with h5py.File(tmpFile, 'w', driver=None) as h5:
        #         h5.create_dataset('data', data=self.result[2])
        # 
        #     self.applet.workflow.addImageStatic(tmpFile)
        #     for i in range(3):
        #         self.editor.imageViews[i].setHudVisible(True)

        self.topLevelOperatorView.Output.setValue(self.result[0])
        self.topLevelOperatorView.OutputThreshold.setValue(self.result[1])
        for layer in self.layerstack:
            if 'Raw Input' in layer.name:
                layer.opacity = 0.8
            elif 'Thresholded' in layer.name:
                layer.visible = True
                layer.opacity = 1.0
        # self.status.setText(self.status.text() + "\nFinished!")
        self.status.setText("Finished!")

        # Re-enable button
        self.button.setDisabled(True)

        # Enable thresholding widget
        lims = [self.result[0].min(), self.result[0].max()]
        print('Prediction limits [{},{}]'.format(lims[0], lims[1]))
        self.thresholdWidget.setMinimum(lims[0] * self.THRESHOLD_SCALING)
        self.thresholdWidget.setMaximum(lims[1] * self.THRESHOLD_SCALING)
        self.thresholdWidget.setEnabled(True)
        # self.thresholdWidget.setValue(sum(lims) / len(lims) * self.THRESHOLD_SCALING)
        # self.thresholdLabel.setText('Treshold: ' + str(self.thresholdWidget.value() / 10.))
        self.changeThreshold()

    def killProbe(self):
        """
        Stops server probing while a request is running.
        """
        self.thread_log.stop()
        # self.thread_usage.stop()

    def updateServerProgress(self, txt):
        """
        Called by the prober to update the status, periodically.
        """
        # Update text
        self.serverProgress.setText(txt)

        # Move to the end so it scrolls automatically
        self.serverProgress.moveCursor(QTextCursor.End)

    def updateServerUsage(self, txt):
        """
        Called by the prober to update server usage, periodically.
        """
        self.labelUsage.setText(txt)

    def handleFailureCallback(self):
        """
        Called by handlefailure once the timer is over.
        """
        self.status.setText("An error occurred! Stopping...")
        self.killProbe()

    def handleFailure(self):
        """
        Called if the server (or the communication probe) ran into a problem
        """
        # Timer to let the prober probe one last time.
        threading.Timer(self.USAGE_PROBE_DELAY, self.handleFailureCallback()).start()

        # Re-enable button
        self.button.setDisabled(True)

    def sendRequest(self):
        """
        Send request to server.
        """
        # Disable button
        self.button.setDisabled(True)

        serviceName = self.topLevelOperatorView.InputSelectedServiceName.value
        modelNameAndArgs = self.topLevelOperatorView.InputSelectedModelNameAndArgs.value
        datasetName = self.topLevelOperatorView.InputSelectedDatasetName.value
        mode = self.topLevelOperatorView.InputSelectedMode.value

        if mode == "train":
            # Containers of the numpy arrays containing data
            # Obtained via labelArray.value for example
            labelArray = self.topLevelOperatorView.InputLabel
        creds = self.topLevelOperatorView.InputCreds
        imgArray = self.topLevelOperatorView.InputImage

        # Mutable object to store results from an external thread
        self.result = [None, None, None]
        self.status.setText("Starting...")
        self.thread_server = CommunicateWithServer(creds, serviceName, datasetName, modelNameAndArgs, mode, imgArray, labelArray if mode == 'train' else None, self.result)
        self.thread_server.signal_is_finished.connect(self.setOutput)
        self.thread_server.signal_communication_ended.connect(self.killProbe)
        self.thread_server.signal_update_status.connect(self.updateStatus)
        self.thread_server.signal_failure.connect(self.handleFailure)
        self.thread_server.start()
        self.thread_log = ServerProgressProber(creds, serviceName, datasetName, modelNameAndArgs['name'], self.LOG_PROBE_DELAY)
        self.thread_log.signal_server_log.connect(self.updateServerProgress)
        self.thread_log.start()

    def setupLayers(self):
        """
        Overridden from LayerViewerGui.
        Create a list of all layer objects that should be displayed.
        """
        layers = []

        # Show the raw input data
        inputImageSlot = self.topLevelOperatorView.InputImage
        if inputImageSlot.ready():
            inputLayer = self.createStandardLayerFromSlot(inputImageSlot)
            inputLayer.name = "Raw Input"
            inputLayer.visible = True
            inputLayer.opacity = 1.0
            layers.append(inputLayer)

        outputImageSlot = self.topLevelOperatorView.Output
        if outputImageSlot.ready():
            outputLayer = self.createStandardLayerFromSlot(outputImageSlot)
            outputLayer.name = "Result"
            outputLayer.visible = False
            outputLayer.opacity = 1.0
            layers.append(outputLayer)

        outputThresholdSlot = self.topLevelOperatorView.OutputThreshold
        if outputThresholdSlot.ready():
            # thresholdLayer = self.createStandardLayerFromSlot(outputThresholdSlot)
            thresholdLayer = ColortableLayer(LazyflowSource(outputThresholdSlot),
                                             colorTable=self._colorTable16)
            thresholdLayer.name = "Thresholded"
            thresholdLayer.visible = False
            thresholdLayer.opacity = 1.0
            layers.append(thresholdLayer)

        return layers

    def _createDefault16ColorColorTable(self):
        colors = []

        # Transparent for the zero label
        colors.append(QColor(0, 0, 0, 0))

        # ilastik v0.5 colors
        colors.append(QColor(Qt.red))
        colors.append(QColor(Qt.green))
        colors.append(QColor(Qt.yellow))
        colors.append(QColor(Qt.blue))
        colors.append(QColor(Qt.magenta))
        colors.append(QColor(Qt.darkYellow))
        colors.append(QColor(Qt.lightGray))

        # Additional colors
        colors.append(QColor(255, 105, 180))  # hot pink
        colors.append(QColor(102, 205, 170))  # dark aquamarine
        colors.append(QColor(165, 42, 42))  # brown
        colors.append(QColor(0, 0, 128))      # navy
        colors.append(QColor(255, 165, 0))    # orange
        colors.append(QColor(173, 255, 47))  # green-yellow
        colors.append(QColor(128, 0, 128))     # purple
        colors.append(QColor(240, 230, 140))  # khaki

        assert len(colors) == 16

        return [c.rgba() for c in colors]
        return colors
