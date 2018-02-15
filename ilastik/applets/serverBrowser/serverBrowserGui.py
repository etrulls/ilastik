from PyQt5.QtCore import Qt, QSize
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QComboBox, QWidget, QVBoxLayout, QSpacerItem, QSizePolicy, QLineEdit, QLabel, QPushButton

from ilastik.applets.layerViewer.layerViewerGui import LayerViewerGui

from .datasetDownloader import DatasetDownloader
import urllib3
import ssl


class ServerBrowserGui(LayerViewerGui):

    DEFAULT_STUMPS_NBR = "2000"
    DEFAULT_MIRRORING = "25"
    DEFAULT_INSIDE_MASK_IGNORE = "0"
    DEFAULT_OUTSIDE_MASK_IGNORE = "0"

    def appletDrawer(self):
        return self._drawer

    def __init__(self, parentApplet, topLevelOperatorView):
        super(ServerBrowserGui, self).__init__(parentApplet, topLevelOperatorView)
        self.topLevelOperatorView = topLevelOperatorView
        self.parentApplet = parentApplet
        self.applet = self.topLevelOperatorView.parent.parent.serverBrowserApplet

    def initAppletDrawerUi(self):
        self._drawer= QWidget(parent=self)

        self.actionText = QLabel() # will indicate what actions will be taken based on the current selection

        dataSetLabel = QLabel("Dataset: ")
        self.datasetComboBox = QComboBox()
        self.datasetComboBox.setMaximumSize(QSize(200, 30))
        if self.topLevelOperatorView.InputDataList.value.size == 1: #if there is only one string in the list, addItems will cut it into chars.
            self.datasetComboBox.addItem(self.topLevelOperatorView.InputDataList.value)
        else:
            self.datasetComboBox.addItems(self.topLevelOperatorView.InputDataList.value)
        self.baseDatasetSize = self.topLevelOperatorView.InputDataList.value.size
        self.datasetComboBox.currentIndexChanged.connect(self.reactOnSelection)

        #dataset horizontal box
        self.datasetLayout = QHBoxLayout()
        self.newDatasetName = QLineEdit()
        self.newDatasetName.setMaximumSize(QSize(200, 30))
        self.newDatasetName.textChanged.connect(self.checkValidDatasetName)
        self.addDatasetButton = QPushButton("Add")
        self.addDatasetButton.setMaximumSize(QSize(60,30))
        self.addDatasetButton.clicked.connect(self.addDataset)
        self.addDatasetButton.setDisabled(True)
        self.datasetLayout.addWidget(self.newDatasetName)
        self.datasetLayout.addWidget(self.addDatasetButton)

        #data selection from disk horizontal box
        self.selectFromDiskFrame = QFrame() #layouts can't be hidden, so we need to wrap them in a selectFromDiskFrame.
        self.selectFromDiskLayout = QHBoxLayout()
        self.selectFileButton = QPushButton("Add file")
        self.selectFileButton.setMaximumSize(QSize(100,30))
        self.selectFileButton.clicked.connect(self.getFileFromDisk)
        self.selectFromDiskLayout.addWidget(self.selectFileButton)
        self.selectFromDiskFrame.setLayout(self.selectFromDiskLayout)
        self.selectFromDiskFrame.hide()

        # data downloading/erasing horizontal box
        self.selectFromServerFrame = QFrame()
        self.selectFromServerLayout = QHBoxLayout()
        self.selectFromServerButton = QPushButton("Download and use")
        self.selectFromServerButton.setMaximumSize(QSize(150,30))
        self.selectFromServerButton.clicked.connect(self.downloadDataset)
        self.deleteDatasetButton = QPushButton("Delete")
        self.deleteDatasetButton.setMaximumSize(QSize(60,30))
        self.deleteDatasetButton.clicked.connect(self.deleteDatasetFromServ)
        self.selectFromServerLayout.addWidget(self.selectFromServerButton)
        self.selectFromServerLayout.addWidget(self.deleteDatasetButton)
        self.selectFromServerFrame.setLayout(self.selectFromServerLayout)
        self.selectFromServerFrame.hide()

        self.downloadStatus = QLabel("Preparing for download...")

        modelLabel = QLabel("Model: ")
        self.modelComboBox = QComboBox()
        self.modelComboBox.setMaximumSize(QSize(200, 30))
        if self.topLevelOperatorView.InputModelList.value.size == 1:
            self.modelComboBox.addItem(self.topLevelOperatorView.InputModelList.value)
        else:
            self.modelComboBox.addItems(self.topLevelOperatorView.InputModelList.value)
        self.baseModelSize = self.topLevelOperatorView.InputModelList.value.size
        self.modelComboBox.currentIndexChanged.connect(self.reactOnSelection)

        # model horizontal box
        self.modelLayout = QHBoxLayout()
        self.newModelName = QLineEdit()
        self.newModelName.setMaximumSize(QSize(200,30))
        self.newModelName.textChanged.connect(self.checkValidModelName)
        self.addModelButton = QPushButton("Add")
        self.addModelButton.setMaximumSize(QSize(60, 30))
        self.addModelButton.setDisabled(True)
        self.addModelButton.clicked.connect(self.addModel)
        self.modelLayout.addWidget(self.newModelName)
        self.modelLayout.addWidget(self.addModelButton)

        self.deleteModelButton = QPushButton("Delete")
        self.deleteModelButton.setMaximumSize(QSize(60,30))
        self.deleteModelButton.clicked.connect(self.deleteModelFromServ)

        #The parameter below is used for both testing and training. We will thus always display it
        self.dataMirrorLayout = QHBoxLayout()
        dataMirrorLabel = QLabel("Data mirroring :")
        dataMirrorLabel.setMaximumSize(QSize(190,30))
        self.dataMirrorValue = QLineEdit()
        self.dataMirrorValue.setMaximumSize(QSize(50,30))
        self.dataMirrorValue.setText(self.DEFAULT_MIRRORING)
        self.dataMirrorLayout.addWidget(dataMirrorLabel)
        self.dataMirrorLayout.addWidget(self.dataMirrorValue, 0, Qt.AlignLeft)

        #Training specific parameters.
        self.modelParametersFrame = QFrame()
        self.modelParametersLayout = QVBoxLayout()
        self.modelParametersFrame.setLayout(self.modelParametersLayout)

        self.numStumpsLayout = QHBoxLayout()
        numStumpsLabel = QLabel("Number of stumps :")
        numStumpsLabel.setMaximumSize(QSize(190,30))
        self.numStumpsValue = QLineEdit()
        self.numStumpsValue.setMaximumSize(QSize(50,30))
        self.numStumpsValue.setText(self.DEFAULT_STUMPS_NBR)
        self.numStumpsLayout.addWidget(numStumpsLabel)
        self.numStumpsLayout.addWidget(self.numStumpsValue, 0, Qt.AlignLeft)
        self.modelParametersLayout.addLayout(self.numStumpsLayout)

        self.insidePixelLayout = QHBoxLayout()
        insidePixelLabel = QLabel("Pixels ignored inside mask :")
        insidePixelLabel.setMaximumSize(QSize(190,30))
        self.insidePixelValue = QLineEdit()
        self.insidePixelValue.setMaximumSize(QSize(50,30))
        self.insidePixelValue.setText(self.DEFAULT_INSIDE_MASK_IGNORE)
        self.insidePixelLayout.addWidget(insidePixelLabel)
        self.insidePixelLayout.addWidget(self.insidePixelValue, 0, Qt.AlignLeft)
        self.modelParametersLayout.addLayout(self.insidePixelLayout)

        self.outsidePixelLayout = QHBoxLayout()
        outsidePixelLabel = QLabel("Pixels ignored outside mask :")
        outsidePixelLabel.setMaximumSize(QSize(190,30))
        self.outsidePixelValue = QLineEdit()
        self.outsidePixelValue.setMaximumSize(QSize(50,30))
        self.outsidePixelValue.setText(self.DEFAULT_OUTSIDE_MASK_IGNORE)
        self.outsidePixelLayout.addWidget(outsidePixelLabel)
        self.outsidePixelLayout.addWidget(self.outsidePixelValue, 0, Qt.AlignLeft)
        self.modelParametersLayout.addLayout(self.outsidePixelLayout)

        confirmLabel = QLabel("When ready, press the button below to confirm selection")
        self.confirmButton = QPushButton("Confirm")
        self.confirmButton.setMaximumSize(QSize(100, 30))
        self.confirmButton.clicked.connect(self.confirmSelection)
        self.selectedDatasetLabel = QLabel("Selected dataset : None")
        self.selectedModelLabel = QLabel("Selected model : None")

        # Add widgets and sublayouts to main layout
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.addWidget(self.actionText)
        layout.addSpacing(5)
        layout.addWidget(dataSetLabel)
        layout.addWidget(self.datasetComboBox)
        layout.addLayout(self.datasetLayout)
        layout.addWidget(self.selectFromDiskFrame)
        layout.addWidget(self.selectFromServerFrame)
        layout.addWidget(self.downloadStatus)
        self.downloadStatus.hide()
        layout.addWidget(modelLabel)
        layout.addWidget(self.modelComboBox)
        layout.addLayout(self.modelLayout)
        layout.addWidget(self.deleteModelButton, 0, Qt.AlignCenter)
        layout.addLayout(self.dataMirrorLayout)
        layout.addWidget(self.modelParametersFrame)
        layout.addSpacing(30)
        layout.addWidget(confirmLabel)
        layout.addWidget(self.confirmButton)
        layout.addSpacing(15)
        layout.addWidget(self.selectedDatasetLabel)
        layout.addWidget(self.selectedModelLabel)
        layout.addSpacerItem(QSpacerItem(0, 0, vPolicy=QSizePolicy.Expanding))

        # Apply layout to the drawer
        self._drawer.setLayout(layout)
        self.reactOnSelection()

    def reactOnSelection(self):
        """
        Will hide/show widgets, layouts and frames depending on the current selection
        """
        if self.modelComboBox.currentIndex() == -1:
            self.actionText.setText("No existing image and/or model detected \nplease add one before proceeding")
            self.confirmButton.setDisabled(True)
            self.deleteModelButton.hide()
            self.modelParametersFrame.hide()
            if self.datasetComboBox.currentIndex() >= self.baseDatasetSize:
                self.selectFromDiskFrame.show()
                self.selectFromServerFrame.hide()
            elif self.datasetComboBox.currentIndex() > -1:
                self.selectFromServerFrame.show()
                self.selectFromDiskFrame.hide()
        elif self.datasetComboBox.currentIndex() >= self.baseDatasetSize:
            self.confirmButton.setEnabled(True)
            self.selectFromDiskFrame.show()
            self.selectFromServerFrame.hide()
            if self.modelComboBox.currentIndex() >= self.baseModelSize:
                self.deleteModelButton.hide()
                self.modelParametersFrame.show()
                self.actionText.setText("Current selection: new image and model \nInstructions: select file from disk and proceed to label")
            else:
                self.deleteModelButton.show()
                self.modelParametersFrame.hide()
                self.actionText.setText("Current selection: new image, old model \nInstructions: select file from disk, labelling will be skipped.")
        else:
            self.confirmButton.setEnabled(True)
            self.selectFromDiskFrame.hide()
            self.selectFromServerFrame.show()
            if self.modelComboBox.currentIndex() >= self.baseModelSize:
                self.deleteModelButton.hide()
                self.modelParametersFrame.show()
                self.actionText.setText("Current selection: old image, new model \nInstructions: Download selected image and proceed to label it")
                self.selectFromServerButton.show()
            else:
                self.deleteModelButton.show()
                self.modelParametersFrame.hide()
                self.actionText.setText("Current selection: old image and model \nInstructions: Labelling and image importation will be skipped")
                self.selectFromServerButton.hide()

    def addTextToComboBox(self, comboBox, text):
        """
        adds text to ComboBox and sets it as the new index.
        """
        comboBox.addItem(text)
        idx = comboBox.findText(text, Qt.MatchFixedString)
        if idx >=0:
            comboBox.setCurrentIndex(idx)

    def getFileFromDisk(self):
        self.applet.workflow.addImageFromDisk()

        #semi-hack, allows browsing the data in 3D after replacing the 2D palceholder
        for i in range(3):
            self.editor.imageViews[i].setHudVisible(True)

    def addDataset(self):
        """
        called when the "add" button of the dataset field is pressed
        """
        self.addTextToComboBox(self.datasetComboBox, self.newDatasetName.text())
        self.newDatasetName.clear()

    def addModel(self):
        """
        called when the "add" button of the model field is pressed
        """
        self.addTextToComboBox(self.modelComboBox, self.newModelName.text())
        self.newModelName.clear()

    def refreshInfo(self):
        """
        Refreshes the user infos entered in the login applet.
        """
        self.username = self.topLevelOperatorView.InputCreds.value['username']
        self.password = self.topLevelOperatorView.InputCreds.value['password']
        self.server = self.topLevelOperatorView.InputCreds.value['server']
        self.port = self.topLevelOperatorView.InputCreds.value['port']

    def setDownloadedImage(self):
        self.downloadStatus.hide()
        self.downloadStatus.setText("Preparing for download...")
        self.applet.workflow.addImageStatic(self.result[0])
        #semi-hack, allows browsing the data in 3D after replacing the 2D palceholder
        for i in range(3):
            self.editor.imageViews[i].setHudVisible(True)

    def updateStatus(self, line):
        """
        called by threads to update the text of the label (displayed on the left of the UI). Modifying the labels directly
        from withing a thread is not an option, because PyQt widgets are not thread-safe.
        line : line to append
        isPermanent : True if line is supposed to stay. False if it's supposed to be deleted after the next label update.
        """
        self.downloadStatus.setText(line)

    def downloadDataset(self):
        self.refreshInfo()
        # Mutable object to store thread result
        self.result = [None]
        datasetName = self.datasetComboBox.currentText()
        self.thread = DatasetDownloader(self.username, self.password, datasetName, self.server, self.port, self.result)
        # self.connect(self.thread, SIGNAL('finished'), self.setDownloadedImage)
        # self.connect(self.thread, SIGNAL('update status'), self.updateStatus)
        # self.thread.signal_finished.connect(self.setDownloadedImage)
        # self.thread.signal_update(self.updateStatus)
        self.thread.signal_has_update.connect(self.updateStatus)
        self.thread.signal_is_finished.connect(self.setDownloadedImage)
        self.thread.start()
        self.downloadStatus.show()

    def deleteDatasetFromServ(self):
        """
        sends a request to remove the currently selected dataset from the server,
        removes the model from the combobox if result code is 200
        """
        self.refreshInfo()
        datasetName = self.datasetComboBox.currentText()
        request = urllib3.Request('https://iccvlabsrv' + self.server + '.iccluster.epfl.ch:' + self.port + '/api/deleteDataset')
        gcontext = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        request.add_header('username', self.username)
        request.add_header('password', self.password)
        request.add_header('dataset-name', datasetName)
        result = urllib3.urlopen(request, context=gcontext)
        if result.getcode() == 200:
            self.datasetComboBox.removeItem(self.datasetComboBox.findText(datasetName, Qt.MatchFixedString))
            self.baseDatasetSize = self.baseDatasetSize - 1

    def deleteModelFromServ(self):
        """
        sends a request to remove the currently selected model from the server,
        removes the model from the combobox if result code is 200
        """
        self.refreshInfo()
        modelName = self.modelComboBox.currentText()
        request = urllib3.Request('https://iccvlabsrv' + self.server + '.iccluster.epfl.ch:' + self.port + '/api/deleteModel')
        gcontext = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        request.add_header('username', self.username)
        request.add_header('password', self.password)
        request.add_header('model-name', modelName)
        result = urllib3.urlopen(request, context=gcontext)
        if result.getcode()==200:
            self.modelComboBox.removeItem(self.modelComboBox.findText(modelName, Qt.MatchFixedString))
            self.baseModelSize = self.baseModelSize - 1

    def noIllegalChars(self, word):
        return str.isalnum(str(word)) and len(word)>0

    def checkValidDatasetName(self):
        if self.noIllegalChars(self.newDatasetName.text()):
            self.addDatasetButton.setDisabled(False)
        else:
            self.addDatasetButton.setDisabled(True)

    def checkValidModelName(self):
        if self.noIllegalChars(self.newModelName.text()):
            self.addModelButton.setDisabled(False)
        else:
            self.addModelButton.setDisabled(True)

    def confirmSelection(self):
        """
        sets the output in the slots for the following applets and updates the "selected X" labels.
        Also decides which steps are next (labelling, testing, training...)
        """
        modelDict = {'name': self.modelComboBox.currentText(), 'numStumps': int(self.numStumpsValue.text()),
                     'mirror': int(self.dataMirrorValue.text()), 'insidePixel': int(self.insidePixelValue.text()),
                     'outsidePixel': int(self.outsidePixelValue.text())}
        self.topLevelOperatorView.OutputSelectedDatasetName.setValue(self.datasetComboBox.currentText())
        self.topLevelOperatorView.OutputSelectedModelNameAndArgs.setValue(modelDict)
        self.selectedDatasetLabel.setText("Selected dataset: " + self.datasetComboBox.currentText())
        self.selectedModelLabel.setText("Selected model: " + self.modelComboBox.currentText())
        if self.datasetComboBox.currentIndex() >= self.baseDatasetSize:
            if self.modelComboBox.currentIndex() >= self.baseModelSize:
                #new model and data => need to label and train
                self.topLevelOperatorView.OutputSelectedMode.setValue("train")
            else:
                #new data, old model => test, no labelling required
                self.topLevelOperatorView.OutputSelectedMode.setValue("test")
        else:
            if self.modelComboBox.currentIndex() >= self.baseModelSize:
                #old data, new model => need to label and train (no need to send data again)
                #TODO add function on server to send only labels and not data (upload optimization, for now let's just treat it like regular training and send the data)
                self.topLevelOperatorView.OutputSelectedMode.setValue("train")
            else:
                #old data, old model => test, no labelling required
                self.topLevelOperatorView.OutputSelectedMode.setValue("testOldData")
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
