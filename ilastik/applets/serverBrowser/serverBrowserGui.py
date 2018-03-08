from PyQt5.QtCore import Qt, QSize
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QComboBox, QWidget, QVBoxLayout, QSpacerItem, QSizePolicy, QLineEdit, QLabel, QPushButton, QGroupBox, QRadioButton, QMessageBox, QSpinBox

from ilastik.applets.layerViewer.layerViewerGui import LayerViewerGui

from .datasetDownloader import DatasetDownloader
import urllib
import urllib.request
import ssl


class ServerBrowserGui(LayerViewerGui):

    # Model parameters: [default, min, max]
    DEFS_MIRROR = [20, 0, 50]
    DEFS_CCBOOST_STUMPS = [2000, 100, 10000]
    DEFS_CCBOOST_MASK_IN = [0, 0, 50]
    DEFS_CCBOOST_MASK_OUT = [0, 0, 50]

    def appletDrawer(self):
        return self._drawer

    def __init__(self, parentApplet, topLevelOperatorView):
        super(ServerBrowserGui, self).__init__(parentApplet, topLevelOperatorView)
        self.topLevelOperatorView = topLevelOperatorView
        self.parentApplet = parentApplet
        self.applet = self.topLevelOperatorView.parent.parent.serverBrowserApplet

    def initAppletDrawerUi(self):
        self._drawer= QWidget(parent=self)

        self.confirmed_data = None
        self.confirmed_model = None
        self.is_train = None
        self.is_new = None

        # 1. Data
        self.datasetLayout = QVBoxLayout()
        self.datasetBox = QGroupBox("Data")
        self.datasetBox.setLayout(self.datasetLayout)

        self.dataOption1Base = "Use dataset on server:"
        self.dataOption1 = QRadioButton(self.dataOption1Base)
        self.dataOption2 = QRadioButton("Upload a new dataset:")
        self.dataOption2.setChecked(True)

        self.datasetComboBox = QComboBox()
        self.datasetComboBox.setMaximumSize(QSize(200, 30))
        for e in self.topLevelOperatorView.InputDataList.value:
            self.datasetComboBox.addItem(e, e.split(" ")[0])
        self.datasetComboBox.setDisabled(True)
        self.datasetLayout.addWidget(self.dataOption1)
        self.datasetLayout.addWidget(self.datasetComboBox)
        self.reuseDatasetButton = QPushButton("Download")
        self.reuseDatasetButton.setMaximumSize(QSize(100, 30))
        self.reuseDatasetButton.setDisabled(True)
        self.deleteDatasetButton = QPushButton("Delete")
        self.deleteDatasetButton.setMaximumSize(QSize(80, 30))
        self.deleteDatasetButton.setStyleSheet("QPushButton {color: red;}")
        if self.datasetComboBox.count() > 0:
            self.deleteDatasetButton.setEnabled(True)
        else:
            self.dataOption1.setDisabled(True)
            self.deleteDatasetButton.setDisabled(True)
        self.horbox1 = QHBoxLayout()
        self.horbox1.addWidget(self.reuseDatasetButton)
        self.horbox1.addWidget(self.deleteDatasetButton)
        self.horbox1.setSpacing(0)
        self.horbox1.addStretch(1)
        self.datasetLayout.addLayout(self.horbox1)
        self.dataOption1.toggled.connect(self.toggleOption1)
        self.dataOption2.toggled.connect(self.toggleOption2)
        self.reuseDatasetButton.clicked.connect(self.downloadDataset)
        self.deleteDatasetButton.clicked.connect(self.deleteDatasetFromServ)

        self.newDatasetName = QLineEdit()
        self.newDatasetName.setMaximumSize(QSize(150, 30))
        self.dataWarning = QLabel("Use chunked HDF5 for best compatibility.")
        self.dataWarning.setStyleSheet("QLabel {font-size: 10pt;}")
        self.addDatasetButton = QPushButton("Validate")
        self.addDatasetButton.setMaximumSize(QSize(80, 30))
        self.addDatasetButton.setEnabled(True)
        self.selectFileButton = QPushButton("Select file")
        self.selectFileButton.setMaximumSize(QSize(110, 30))
        self.selectFileButton.setDisabled(True)
        self.addDatasetButton.clicked.connect(self.checkValidDatasetName)
        self.newDatasetName.textChanged.connect(self.disableUploadButton)
        self.selectFileButton.clicked.connect(self.getFileFromDisk)

        self.horbox2 = QHBoxLayout()
        self.horbox2.addWidget(self.addDatasetButton)
        self.horbox2.addWidget(self.selectFileButton)
        self.horbox2.setSpacing(0)
        self.horbox2.addStretch(1)
        self.datasetLayout.addWidget(self.dataOption2)
        self.datasetLayout.addWidget(self.newDatasetName)
        self.datasetLayout.addWidget(self.dataWarning)
        self.datasetLayout.addLayout(self.horbox2)

        # 2. List of services
        # Indicate actions that will be taken based on the current selection
        self.serviceBoxLayout = QVBoxLayout()
        self.serviceBoxLayout.setSpacing(0)
        self.serviceBox = QGroupBox("Service")
        self.serviceComboBox = QComboBox()
        self.serviceComboBox.setMaximumSize(QSize(200, 30))
        self.service_list = self.topLevelOperatorView.InputServiceList.value
        for e in self.topLevelOperatorView.InputServiceList.value:
            self.serviceComboBox.addItem(e)
        self.baseServiceSize = self.topLevelOperatorView.InputServiceList.value.size
        self.serviceBox.setLayout(self.serviceBoxLayout)
        self.serviceComboBox.currentIndexChanged.connect(self.toggleModelBox)

        self.serviceBoxLayoutH = QHBoxLayout()
        self.serviceBoxLayoutH.setSpacing(0)
        self.serviceBoxLayoutH.addWidget(self.serviceComboBox)
        # self.serviceBoxLayoutH.addWidget(self.serviceButton)
        self.serviceBoxLayoutH.addStretch(1)
        self.serviceBoxLayout.addLayout(self.serviceBoxLayoutH)

        # 3. Model and parameters. Three framesL
        self.modelBox = QGroupBox("Model")
        self.modelLayout = QVBoxLayout()
        self.modelBox.setLayout(self.modelLayout)

        # 3a. Must select a service first: just a warning
        # self.noModelFrame = QWidget()
        # self.noModelFrame.hide()
        # self.modelLayout.addWidget(self.noModelFrame)
        # self.noModelLayout = QVBoxLayout()
        # self.noModelFrame.setLayout(self.noModelLayout)
        # self.noModelLayout.setContentsMargins(0, 0, 0, 0)
        # self.noModelLabel = QLabel("Must select a service first.")
        # self.noModelLayout.addWidget(self.noModelLabel)

        # 3b. Pretrained model: select which
        self.ccboostTestFrame = QFrame()
        self.ccboostTestFrame.hide()
        self.modelLayout.addWidget(self.ccboostTestFrame)
        self.ccboostTestLayout = QVBoxLayout()
        self.ccboostTestFrame.setLayout(self.ccboostTestLayout)
        self.ccboostTestLayout.setContentsMargins(0, 0, 0, 0)
        self.modelLabelTrained = QLabel("Select a trained model:")
        self.ccboostTestLayout.addWidget(self.modelLabelTrained)

        self.ccboostModelComboBox = QComboBox()
        self.ccboostModelComboBox.setMaximumSize(QSize(200, 30))
        for e in self.topLevelOperatorView.InputCCboostModelList.value:
            self.ccboostModelComboBox.addItem(e)
        self.ccboostTestLayout.addWidget(self.ccboostModelComboBox)

        self.horboxSelectModel = QHBoxLayout()
        self.ccboostSelectModelButton = QPushButton("Select")
        self.ccboostSelectModelButton.setMaximumSize(QSize(80, 30))
        self.deleteModelButton = QPushButton("Delete")
        self.deleteModelButton.setMaximumSize(QSize(80, 30))
        self.deleteModelButton.setStyleSheet("QPushButton {color: red;}")
        if len(self.topLevelOperatorView.InputCCboostModelList.value) == 0:
            self.ccboostSelectModelButton.setDisabled(True)
            self.deleteModelButton.setDisabled(True)
        self.horboxSelectModel.addWidget(self.ccboostSelectModelButton)
        self.horboxSelectModel.addWidget(self.deleteModelButton)
        self.horboxSelectModel.addStretch(1)
        self.ccboostTestLayout.addLayout(self.horboxSelectModel)
        self.ccboostSelectModelButton.clicked.connect(self.selectModelFromServ)
        self.deleteModelButton.clicked.connect(self.deleteModelFromServ)

        # Data mirroring
        self.ccboostTestRow1 = QHBoxLayout()
        self.ccboostTestMirrorLabel = QLabel("Data mirroring (edges): ")
        self.ccboostTestMirrorLabel.setMaximumSize(QSize(190, 30))
        self.ccboostTestMirrorValue = QSpinBox()
        self.ccboostTestMirrorValue.setMaximumSize(QSize(60, 30))
        self.ccboostTestMirrorValue.setRange(self.DEFS_MIRROR[1], self.DEFS_MIRROR[2])
        self.ccboostTestMirrorValue.setValue(self.DEFS_MIRROR[0])
        self.ccboostTestRow1.addWidget(self.ccboostTestMirrorLabel)
        self.ccboostTestRow1.addWidget(self.ccboostTestMirrorValue)
        self.ccboostTestLayout.addLayout(self.ccboostTestRow1)
        self.ccboostTestRow1.setSpacing(0)
        self.ccboostTestRow1.addStretch(1)

        # 3c. Train a new model: needs parameters
        # Not using this actually! Defaults to ccboost/train
        self.ccboostTrainFrame = QFrame()
        self.ccboostTrainFrame.show()
        self.modelLayout.addWidget(self.ccboostTrainFrame)
        self.ccboostTrainLayout = QVBoxLayout()
        self.ccboostTrainFrame.setLayout(self.ccboostTrainLayout)
        self.ccboostTrainLayout.setContentsMargins(0, 0, 0, 0)
        self.modelLabelNew = QLabel("Configure a new model:")
        self.ccboostTrainLayout.addWidget(self.modelLabelNew)

        # Model name
        self.ccboostTrainRow0 = QHBoxLayout()
        self.ccboostNewModelLabel = QLabel("Name: ")
        self.ccboostNewModelLabel.setMaximumSize(QSize(190, 30))
        self.newModelName = QLineEdit()
        self.newModelName.setMaximumSize(QSize(200, 30))
        # self.newModelName.setEnabled(True)
        self.ccboostTrainRow0.addWidget(self.ccboostNewModelLabel)
        self.ccboostTrainRow0.addWidget(self.newModelName)
        self.ccboostTrainLayout.addLayout(self.ccboostTrainRow0)
        self.ccboostTrainRow0.setSpacing(0)
        self.ccboostTrainRow0.addStretch(1)

        # Data mirroring
        self.ccboostTrainRow1 = QHBoxLayout()
        self.ccboostTrainMirrorLabel = QLabel("Data mirroring (edges): ")
        self.ccboostTrainMirrorLabel.setMaximumSize(QSize(190, 30))
        self.ccboostTrainMirrorValue = QSpinBox()
        self.ccboostTrainMirrorValue.setMaximumSize(QSize(60, 30))
        self.ccboostTrainMirrorValue.setRange(self.DEFS_MIRROR[1], self.DEFS_MIRROR[2])
        self.ccboostTrainMirrorValue.setValue(self.DEFS_MIRROR[0])
        self.ccboostTrainRow1.addWidget(self.ccboostTrainMirrorLabel)
        self.ccboostTrainRow1.addWidget(self.ccboostTrainMirrorValue)
        self.ccboostTrainLayout.addLayout(self.ccboostTrainRow1)
        self.ccboostTrainRow1.setSpacing(0)
        self.ccboostTrainRow1.addStretch(1)

        # Number of stumps
        self.ccboostTrainRow2 = QHBoxLayout()
        self.ccboostNumStumpsLabel = QLabel("Number of stumps: ")
        self.ccboostNumStumpsLabel.setMaximumSize(QSize(190, 30))
        self.ccboostNumStumpsValue = QSpinBox()
        self.ccboostNumStumpsValue.setMaximumSize(QSize(80, 30))
        self.ccboostNumStumpsValue.setRange(self.DEFS_CCBOOST_STUMPS[1], self.DEFS_CCBOOST_STUMPS[2])
        self.ccboostNumStumpsValue.setValue(self.DEFS_CCBOOST_STUMPS[0])
        # self.ccboostNumStumpsValue.setDisabled(True)
        self.ccboostTrainRow2.addWidget(self.ccboostNumStumpsLabel)
        self.ccboostTrainRow2.addWidget(self.ccboostNumStumpsValue)
        self.ccboostTrainLayout.addLayout(self.ccboostTrainRow2)
        self.ccboostTrainRow2.setSpacing(0)
        self.ccboostTrainRow2.addStretch(1)

        # Ignore pixels inside mask
        self.ccboostTrainRow3 = QHBoxLayout()
        self.ccboostInsidePixelLabel = QLabel("Ignored pixels (inside): ")
        self.ccboostInsidePixelLabel.setMaximumSize(QSize(190, 30))
        self.ccboostInsidePixelValue = QSpinBox()
        self.ccboostInsidePixelValue.setMaximumSize(QSize(60, 30))
        self.ccboostInsidePixelValue.setRange(self.DEFS_CCBOOST_MASK_IN[1], self.DEFS_CCBOOST_MASK_IN[2])
        self.ccboostInsidePixelValue.setValue(self.DEFS_CCBOOST_MASK_IN[0])
        # self.ccboostInsidePixelValue.setDisabled(True)
        self.ccboostTrainRow3.addWidget(self.ccboostInsidePixelLabel)
        self.ccboostTrainRow3.addWidget(self.ccboostInsidePixelValue)
        self.ccboostTrainLayout.addLayout(self.ccboostTrainRow3)
        self.ccboostTrainRow3.setSpacing(0)
        self.ccboostTrainRow3.addStretch(1)

        # Ignore pixels outside mask
        self.ccboostTrainRow4 = QHBoxLayout()
        self.ccboostOutsidePixelLabel = QLabel("Ignored pixels (outside): ")
        self.ccboostOutsidePixelLabel.setMaximumSize(QSize(190, 30))
        self.ccboostOutsidePixelValue = QSpinBox()
        self.ccboostOutsidePixelValue.setMaximumSize(QSize(60, 30))
        self.ccboostOutsidePixelValue.setRange(self.DEFS_CCBOOST_MASK_OUT[1], self.DEFS_CCBOOST_MASK_OUT[2])
        self.ccboostOutsidePixelValue.setValue(self.DEFS_CCBOOST_MASK_OUT[0])
        # self.ccboostOutsidePixelValue.setDisabled(True)
        self.ccboostTrainRow4.addWidget(self.ccboostOutsidePixelLabel)
        self.ccboostTrainRow4.addWidget(self.ccboostOutsidePixelValue)
        self.ccboostTrainLayout.addLayout(self.ccboostTrainRow4)
        self.ccboostTrainRow4.setSpacing(0)
        self.ccboostTrainRow4.addStretch(1)

        # Model settings confirmation button
        self.addModelButton = QPushButton("Set parameters")
        self.addModelButton.setMaximumSize(QSize(120, 30))
        # self.addModelButton.setDisabled(True)
        self.ccboostTrainLayout.addWidget(self.addModelButton)
        self.addModelButton.clicked.connect(self.checkValidModelParams)

        # 3d. GAD mouse: no delete button
        self.unetGadTestFrame = QFrame()
        self.unetGadTestFrame.hide()
        self.modelLayout.addWidget(self.unetGadTestFrame)
        self.unetGadTestLayout = QVBoxLayout()
        self.unetGadTestFrame.setLayout(self.unetGadTestLayout)
        self.unetGadTestLayout.setContentsMargins(0, 0, 0, 0)
        self.modelLabelTrained = QLabel("Select a trained model:")
        self.unetGadTestLayout.addWidget(self.modelLabelTrained)

        self.unetGadModelComboBox = QComboBox()
        self.unetGadModelComboBox.setMaximumSize(QSize(200, 30))
        for e in self.topLevelOperatorView.InputUnetGadModelList.value:
            self.unetGadModelComboBox.addItem(e)
        self.unetGadTestLayout.addWidget(self.unetGadModelComboBox)

        # GPU/CPU
        self.unetGadTestRow0 = QHBoxLayout()
        self.unetGadGpuLabel = QLabel("GPU index (-1 for CPU)")
        self.unetGadGpuLabel.setMaximumSize(QSize(190, 30))
        self.unetGadGpuValue = QSpinBox()
        self.unetGadGpuValue.setMaximumSize(QSize(60, 30))
        self.unetGadGpuValue.setRange(-1, 16)
        self.unetGadGpuValue.setValue(0)
        self.unetGadTestRow0.addWidget(self.unetGadGpuLabel)
        self.unetGadTestRow0.addWidget(self.unetGadGpuValue)
        self.unetGadTestLayout.addLayout(self.unetGadTestRow0)
        self.unetGadTestRow0.setSpacing(0)
        self.unetGadTestRow0.addStretch(1)

        # GPU/CPU
        self.unetGadTestRow1 = QHBoxLayout()
        self.unetGadBatchsizeLabel = QLabel("Batch size")
        self.unetGadBatchsizeLabel.setMaximumSize(QSize(190, 30))
        self.unetGadBatchsizeValue = QSpinBox()
        self.unetGadBatchsizeValue.setMaximumSize(QSize(60, 30))
        self.unetGadBatchsizeValue.setRange(1, 32)
        self.unetGadBatchsizeValue.setValue(5)
        self.unetGadTestRow1.addWidget(self.unetGadBatchsizeLabel)
        self.unetGadTestRow1.addWidget(self.unetGadBatchsizeValue)
        self.unetGadTestLayout.addLayout(self.unetGadTestRow1)
        self.unetGadTestRow1.setSpacing(0)
        self.unetGadTestRow1.addStretch(1)

        # Buttons
        self.horboxSelectModel = QHBoxLayout()
        self.unetGadSelectModelButton = QPushButton("Select")
        self.unetGadSelectModelButton.setMaximumSize(QSize(80, 30))
        if len(self.topLevelOperatorView.InputUnetGadModelList.value) == 0:
            self.unetGadSelectModelButton.setDisabled(True)
        self.horboxSelectModel.addWidget(self.unetGadSelectModelButton)
        self.horboxSelectModel.addStretch(1)
        self.unetGadTestLayout.addLayout(self.horboxSelectModel)
        self.unetGadSelectModelButton.clicked.connect(self.selectModelFromServ)

        # Final check to unlock the next applet
        self.confirmLabel = QLabel("Current settings:")
        self.selectedServiceLabel = QLabel("Service: <b>{}</b>".format(self.serviceComboBox.currentText()))
        self.selectedDatasetLabel = QLabel("Dataset: <b>None</b>")
        self.selectedModelLabel = QLabel("Model: <b>None</b>")
        self.confirmButton = QPushButton("Confirm")
        self.confirmButton.setMaximumSize(QSize(100, 30))
        self.confirmButton.setDisabled(True)
        self.confirmButton.clicked.connect(self.confirmSelection)

        # Main layout
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.addWidget(self.datasetBox)
        layout.addWidget(self.serviceBox)
        layout.addWidget(self.modelBox)
        layout.addSpacing(5)
        layout.addWidget(self.confirmLabel)
        layout.addWidget(self.selectedDatasetLabel)
        layout.addWidget(self.selectedServiceLabel)
        layout.addWidget(self.selectedModelLabel)
        layout.addSpacing(5)
        layout.addWidget(self.confirmButton)
        layout.addStretch(1)

        # Apply layout to the drawer
        self._drawer.setLayout(layout)

    def toggleOption1(self):
        if self.dataOption1.isChecked():
            self.reuseDatasetButton.setEnabled(True)
            self.addDatasetButton.setDisabled(True)
            self.selectFileButton.setDisabled(True)
            self.datasetComboBox.setEnabled(True)

    def toggleOption2(self):
        if self.dataOption2.isChecked():
            self.reuseDatasetButton.setDisabled(True)
            self.addDatasetButton.setEnabled(True)
            self.selectFileButton.setDisabled(True)
            self.datasetComboBox.setDisabled(True)

    def disableUploadButton(self):
        # Need to call this every time the qlineedit changes (before validating the label)
        self.selectFileButton.setDisabled(True)

    def toggleModelBox(self):
        service_name = self.serviceComboBox.currentText()
        self.selectedServiceLabel.setText('Service: <b>"{}"</b>'.format(service_name))

        if service_name == 'CCboost (train)':
            self.ccboostTrainFrame.show()
            self.ccboostTestFrame.hide()
            self.unetGadTestFrame.hide()
            self.is_train = True
        elif service_name == 'CCboost (test)':
            self.ccboostTrainFrame.hide()
            self.ccboostTestFrame.show()
            self.unetGadTestFrame.hide()
            self.is_train = False
        elif service_name == 'U-Net GAD mouse (test)':
            self.ccboostTrainFrame.hide()
            self.ccboostTestFrame.hide()
            self.unetGadTestFrame.show()
            self.is_train = False
        else:
            self.warning('Unknown service. Incompatible client/server?')

    def getFileFromDisk(self):
        self.applet.workflow.addImageFromDisk()

        # Hacky, allows browsing the data in 3D after replacing the 2D palceholder
        for i in range(3):
            self.editor.imageViews[i].setHudVisible(True)

        self.confirmed_data = self.newDatasetName.text()
        self.is_new = True
        self.selectedDatasetLabel.setText('Dataset: <b>"{}"</b> (new)'.format(self.newDatasetName.text()))
        self.updateConfirmationState()

    def refresh(self):
        """
        Refreshes the user info entered in the login applet.
        """
        self.username = self.topLevelOperatorView.InputCreds.value['username']
        self.password = self.topLevelOperatorView.InputCreds.value['password']
        self.server = self.topLevelOperatorView.InputCreds.value['server']
        self.port = self.topLevelOperatorView.InputCreds.value['port']

    def updateConfirmationState(self):
        if self.confirmed_data and self.confirmed_model:
            self.confirmButton.setEnabled(True)
        else:
            self.confirmButton.setDisabled(True)

    def setDownloadedImage(self):
        self.applet.workflow.addImageStatic(self.result[0])

        # Hacky, allows browsing the data in 3D after replacing the 2D placeholder
        for i in range(3):
            self.editor.imageViews[i].setHudVisible(True)

        # Feedback
        dataset_name = self.datasetComboBox.itemData(self.datasetComboBox.currentIndex())
        self.confirmed_data = dataset_name
        self.is_new = False
        self.selectedDatasetLabel.setText('Dataset: <b>"{}"</b> (server)'.format(dataset_name))
        self.updateConfirmationState()

    def updateStatus(self, text):
        """
        Update label text from another thread.
        Cannot do it from the thread because PyQt widgets are not thread-safe.
        """
        self.dataOption1.setText(self.dataOption1Base + text)

    def downloadDataset(self):
        self.refresh()

        # Thread can take a while to start, signal that the operation is ongoing
        self.dataOption1.setText(self.dataOption1Base + " 0.0%")

        # Mutable object to store thread result
        self.result = [None]
        datasetName = self.datasetComboBox.itemData(self.datasetComboBox.currentIndex())
        self.thread = DatasetDownloader(self.username, self.password, datasetName, self.server, self.port, self.result)
        self.thread.signal_has_update.connect(self.updateStatus)
        self.thread.signal_is_finished.connect(self.setDownloadedImage)
        self.thread.start()

    def deleteDatasetFromServ(self):
        """
        Sends a request to delete a dataset from the server.
        Removes the entry from the combobox if the result code is 200.
        """
        self.refresh()

        dataset_name = self.datasetComboBox.itemData(self.datasetComboBox.currentIndex())
        request = urllib.request.Request(
            '{}:{}/api/deleteDataset'.format(self.server, self.port))
        request.add_header('username', self.username)
        request.add_header('password', self.password)
        request.add_header('dataset-name', dataset_name)
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        result = urllib.request.urlopen(request, context=context)

        if result.getcode() == 200:
            self.datasetComboBox.removeItem(self.datasetComboBox.findData(dataset_name))
            self.warning('Deleted dataset "{}"'.format(dataset_name))

            # Disable delete button if the list is empty
            if self.datasetComboBox.count() == 0:
                self.dataOption1.setDisabled(True)
                self.deleteDatasetButton.setDisabled(True)
        else:
            self.warning('Error (code {})'.format(result.getcode()))

    def selectModelFromServ(self):
        # Select for testing: can be multiple services
        service = self.serviceComboBox.currentText()
        if service in ['CCboost (train)', 'CCboost (test)']:
            model_name = self.ccboostModelComboBox.currentText()
        elif service == 'U-Net GAD mouse (test)':
            model_name = self.unetGadModelComboBox.currentText()
        else:
            self.warning('Unknown service. Incompatible client/server?')
        self.confirmed_model = model_name
        self.is_train = False
        self.selectedModelLabel.setText('Model: <b>"{}"</b> (server)'.format(model_name))
        self.updateConfirmationState()

    def deleteModelFromServ(self):
        """
        Send a request to delete a model from the server.
        Removes the entry from the combobox if the result code is 200.
        The only models we can delete for now are for CCboost, must expand this otherwise.
        """
        self.refresh()

        model_name = self.ccboostModelComboBox.currentText()
        request = urllib.request.Request(
            '{}:{}/api/deleteModel'.format(self.server, self.port))
        request.add_header('username', self.username)
        request.add_header('password', self.password)
        request.add_header('model-name', model_name)
        request.add_header('service-name', self.serviceComboBox.currentText())
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        result = urllib.request.urlopen(request, context=context)

        if result.getcode() == 200:
            self.ccboostModelComboBox.removeItem(self.ccboostModelComboBox.findText(model_name, Qt.MatchFixedString))
            self.warning('Deleted model "{}"'.format(model_name))

            # Disable delete button if the list is empty
            if self.ccboostModelComboBox.count() > 0:
                self.deleteModelButton.setDisabled(True)
        else:
            self.warning('Error (code {})'.format(result.getcode()))

    def cleanString(self, word):
        # Allow alphanumeric characters only
        # Html headers can be annoying (e.g. no underscores), so we play it safe
        return ''.join([c if c.isalnum() else '' for c in word])

    def warning(self, msg):
        msgBox = QMessageBox()
        msgBox.setText(msg)
        msgBox.exec_()

    def checkValidDatasetName(self):
        clean = self.cleanString(self.newDatasetName.text())

        # Replace string in QLineEdit if it has changed
        self.newDatasetName.setText(clean)

        # print([self.datasetComboBox.itemText(i) for i in range(self.datasetComboBox.count())])
        # print([self.datasetComboBox.itemData(i) for i in range(self.datasetComboBox.count())])

        if len(clean) == 0:
            self.warning("Dataset name is length 0 (alphanumerical characters only)".format(clean))
        elif self.datasetComboBox.findData(clean) != -1:
            self.warning("Dataset name ({}) is already in use".format(clean))
        else:
            self.selectFileButton.setEnabled(True)

    def checkValidModelParams(self):
        # Model name is common to all services
        # Other parameters should be numerical only or manually validated here
        model_name = self.cleanString(self.newModelName.text())

        # Replace string in QLineEdit if it has changed
        self.newModelName.setText(model_name)

        if len(model_name) == 0:
            self.warning("Model name is length 0 (alphanumerical characters only)".format(model_name))
        # elif model_name in self.topLevelOperatorView.InputCCboostModelList.value:
        elif self.ccboostModelComboBox.findData(model_name) != -1:
            self.warning("Model name ({}) is already in use".format(model_name))
        else:
            # Feedback
            self.confirmed_model = model_name
            self.is_train = True
            self.selectedModelLabel.setText('Model: <b>"{}"</b> (new)'.format(model_name))
            self.updateConfirmationState()

    def confirmSelection(self):
        """
        sets the output in the slots for the following applets and updates the "selected X" labels.
        Also decides which steps are next (labelling, testing, training...)
        """
        model_name = self.confirmed_model

        # Model parameters as a dictionary
        service = self.serviceComboBox.currentText()
        if service == 'CCboost (train)':
            modelDict = {
                'name': model_name,
                'ccboost_mirror': int(self.ccboostTrainMirrorValue.text()),
                'ccboost_num_stumps': int(self.ccboostNumStumpsValue.text()),
                'ccboost_inside_pixel': int(self.ccboostInsidePixelValue.text()),
                'ccboost_outside_pixel': int(self.ccboostOutsidePixelValue.text()),
            }
        elif service == 'CCboost (test)':
            modelDict = {
                'name': model_name,
                'ccboost_mirror': int(self.ccboostTestMirrorValue.text()),
            }
        elif service == 'U-Net GAD mouse (test)':
            modelDict = {
                'name': model_name,
                'gpu': int(self.unetGadGpuValue.text()),
                'batchsize': int(self.unetGadBatchsizeValue.text()),
            }
        else:
            self.warning('Unknown service. Incompatible client/server?')
        self.topLevelOperatorView.OutputSelectedModelNameAndArgs.setValue(modelDict)

        # self.topLevelOperatorView.OutputSelectedDatasetName.setValue(self.datasetComboBox.itemData(self.datasetComboBox.currentIndex()))
        self.topLevelOperatorView.OutputSelectedDatasetName.setValue(self.confirmed_data)

        # Service
        self.topLevelOperatorView.OutputSelectedServiceName.setValue(self.serviceComboBox.currentText())

        # Send data in body only if necessary -> TODO fix this, just sending everything for now
        if self.is_train:
            if self.is_new:
                self.topLevelOperatorView.OutputSelectedMode.setValue("train")
            else:
                self.topLevelOperatorView.OutputSelectedMode.setValue("train")
        else:
            if self.is_new:
                self.topLevelOperatorView.OutputSelectedMode.setValue("testWithData")
            else:
                self.topLevelOperatorView.OutputSelectedMode.setValue("testWithoutData")

        self.parentApplet.appletStateUpdateRequested()

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

        return layers
