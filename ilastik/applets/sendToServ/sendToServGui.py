import os

from PyQt5 import uic
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtWidgets import QVBoxLayout, QSpacerItem, QSizePolicy, QDialogButtonBox, QLabel, QTextEdit, QSlider
from PyQt5.QtGui import QColor, QTextCursor

from ilastik.applets.layerViewer.layerViewerGui import LayerViewerGui
from .serverProgressProber import ServerProgressProber
from .communicateWithServer import CommunicateWithServer
from volumina.api import ColortableLayer, LazyflowSource
import h5py
import tempfile
import threading
import numpy as np


class SendToServGui(LayerViewerGui):
    BASE_THRESHOLD_VALUE = 0
    # Time between each probe call to fetch server status
    PROBING_RATE = 5

    def appletDrawer(self):
        return self._drawer

    def __init__(self, parentApplet, topLevelOperatorView):
        """
        """
        self.topLevelOperatorView = topLevelOperatorView
        super(SendToServGui, self).__init__(parentApplet, self.topLevelOperatorView)
        self.applet = self.topLevelOperatorView.parent.parent.sendToServApplet
        self._colorTable16 = self._createDefault16ColorColorTable()

    def initAppletDrawerUi(self):
        # Load the ui file (find it in our own directory)
        localDir = os.path.split(__file__)[0]
        self._drawer = uic.loadUi(localDir + "/drawer.ui")

        buttonbox = QDialogButtonBox(Qt.Horizontal, parent=self)
        self.status = QLabel("Ready to send image and labels")
        buttonbox.setStandardButtons(QDialogButtonBox.Ok)
        buttonbox.accepted.connect(self.accept)

        self.thresholdLabel = QLabel('Treshold: ' + str(self.BASE_THRESHOLD_VALUE / 10.))

        self.thresholdWidget = QSlider(Qt.Horizontal)
        self.thresholdWidget.setValue(self.BASE_THRESHOLD_VALUE / 10.)
        self.thresholdWidget.valueChanged.connect(self.changeThreshold)
        self.thresholdWidget.setMaximum(750)
        self.thresholdWidget.setMinimum(-750)

        # Server progress text field
        self.serverProgress = QTextEdit()
        # fs = self.serverProgress.fontPointSize()
        # print('font size {}'.format(fs))
        # self.serverProgress.setFontPointSize(fs - 3)
        self.serverProgress.setFontPointSize(10)
        self.serverProgress.setMinimumSize(QSize(200, 300))
        self.serverProgress.setReadOnly(True)

        # Add widget to a layout
        layout = QVBoxLayout()
        layout.setSpacing(0)

        layout.addWidget(buttonbox)
        layout.addWidget(self.status)
        layout.addSpacing(50)
        layout.addWidget(self.serverProgress)
        layout.addWidget(self.thresholdLabel)
        layout.addWidget(self.thresholdWidget)
        layout.addSpacerItem(QSpacerItem(0, 0, vPolicy=QSizePolicy.Expanding))

        # Apply layout to the drawer
        self._drawer.setLayout(layout)

    def changeThreshold(self):
        resultArray = self.topLevelOperatorView.Output.value
        thresholded = np.copy(resultArray)
        th = self.thresholdWidget.value() / 10.
        thresholded[resultArray < th] = 1
        thresholded[resultArray >= th] = 2
        thresholded = thresholded.astype('uint8')
        self.topLevelOperatorView.OutputThreshold.setValue(thresholded)
        self.thresholdLabel.setText('Treshold: ' + str(self.thresholdWidget.value() / 10.))

    def updateStatus(self, line, isPermanent):
        """
        called by threads to update the text of the label (displayed on the left of the UI). Modifying the labels directly
        from withing a thread is not an option, because PyQt widgets are not thread-safe.
        line : line to append
        isPermanent : True if line is supposed to stay. False if it's supposed to be deleted after the next label update.
        """
        if(isPermanent):
            self.currentText = self.status.text() + line
            self.status.setText(self.currentText)
        else:
            self.status.setText(self.currentText + line)

    def setOutput(self):
        """
        called when communication with server is over and was successful, sets the server response as the
        result.
        """
        mode = self.topLevelOperatorView.InputSelectedMode.value
        if mode == 'testOldData':
            # Recover the image from the server and display it
            # First dump it on disk, then load and force 3D view
            tmpDir = tempfile.gettempdir()
            tmpDir = os.path.join(tmpDir, 'contextFeaturesResult')
            tmpFile = os.path.join(tmpDir, 'tmp.h5')
            with h5py.File(tmpFile, 'w', driver=None) as h5:
                h5.create_dataset('data', data=self.result[2])

            self.applet.workflow.addImageStatic(tmpFile)
            for i in range(3):
                self.editor.imageViews[i].setHudVisible(True)

        self.topLevelOperatorView.Output.setValue(self.result[0])
        self.topLevelOperatorView.OutputThreshold.setValue(self.result[1])
        for layer in self.layerstack:
            if 'Raw Input' in layer.name:
                layer.opacity = 0.8
            elif 'Thresholded' in layer.name:
                layer.visible = True
                layer.opacity = 1.0
        self.status.setText(self.status.text()+ "\nDone.")

    def killProbe(self):
        """
        stops the constant probing that takes place when a request is being processed.
        """
        self.thread_log.stop()

    def updateServerProgress(self, txt):
        """
        Called by the prober everytime the status is updated (PROBING_RATE). Sets the text in the white field.
        :param txt: The text to display
        """
        # print("---------------------UPDATING TEXT FIELD" + txt)
        self.serverProgress.setText(txt)
        self.serverProgress.moveCursor(QTextCursor.End)

    def handleFailureCallback(self):
        """
        called by handlefailure once the timer is over.
        """
        self.status.setText("An error occurred. \n Check log below for more details")
        self.killProbe()

    def handleFailure(self):
        """
        Called in case the server (or the communication with it) ran into a problem
        """
        # Timer to let the prober probe one last time.
        threading.Timer(self.PROBING_RATE, self.handleFailureCallback()).start()

    def accept(self):
        """
        code executed when the button is pressed
        """
        modelNameAndArgs = self.topLevelOperatorView.InputSelectedModelNameAndArgs.value
        dataSetName = self.topLevelOperatorView.InputSelectedDatasetName.value
        mode = self.topLevelOperatorView.InputSelectedMode.value

        if mode == "train":
            # Containers of the numpy arrays containing data
            # Obtained via labelArray.value for example
            labelArray = self.topLevelOperatorView.InputLabel
        creds = self.topLevelOperatorView.InputCreds
        imgArray = self.topLevelOperatorView.InputImage

        # Mutable object where the thread will store results
        self.result = [None, None, None]
        self.status.setText("Starting...")
        if mode == 'train':
            self.thread_server = CommunicateWithServer(creds, dataSetName, modelNameAndArgs, mode, imgArray, labelArray, self.result)
        else:
            self.thread_server = CommunicateWithServer(creds, dataSetName, modelNameAndArgs, mode, imgArray, None, self.result)
        self.thread_server.signal_is_finished.connect(self.setOutput)
        self.thread_server.signal_communication_ended.connect(self.killProbe)
        self.thread_server.signal_update_status.connect(self.updateStatus)
        self.thread_server.signal_failure.connect(self.handleFailure)
        self.thread_server.start()
        self.thread_log = ServerProgressProber(creds, dataSetName, modelNameAndArgs['name'], self.PROBING_RATE)
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
