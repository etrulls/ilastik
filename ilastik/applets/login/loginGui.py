from __future__ import absolute_import
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QSpacerItem, QSizePolicy, QLineEdit, QLabel, QPushButton, QHBoxLayout

from ilastik.applets.layerViewer.layerViewerGui import LayerViewerGui

import numpy as np
import urllib
import urllib.request
import ssl
from io import BytesIO


class LoginGui(LayerViewerGui):
    # DEFAULT_SERVER = "https://iccvlabsrv19.iccluster.epfl.ch"
    DEFAULT_SERVER = "https://iccluster133.iccluster.epfl.ch"
    DEFAULT_PORT = "6007"

    def appletDrawer(self):
        return self._drawer

    def __init__(self, parentApplet, topLevelOperatorView):
        """
        """
        self.topLevelOperatorView = topLevelOperatorView
        self.parentApplet = parentApplet
        super(LoginGui, self).__init__(parentApplet, self.topLevelOperatorView)
        self.applet = self.topLevelOperatorView.parent.parent.loginApplet

    def initAppletDrawerUi(self):
        self._drawer= QWidget(parent=self)

        serverLabel = QLabel("Server:")
        self.serverTextField = QLineEdit()
        self.serverTextField.setMaximumSize(QSize(250, 30))
        self.serverTextField.setText(self.DEFAULT_SERVER)

        portLabel = QLabel("Port:")
        self.portTextField = QLineEdit()
        self.portTextField.setMaximumSize(QSize(50, 30))
        self.portTextField.setText(self.DEFAULT_PORT)

        usernameLabel = QLabel("Username:")
        self.usernameTextField = QLineEdit()
        self.usernameTextField.setMaximumSize(QSize(100, 30))
        # self.usernameTextField.setText("")

        passwordLabel = QLabel("Password:")
        self.passwordTextField = QLineEdit()
        # Hide text while typing
        self.passwordTextField.setEchoMode(QLineEdit.Password)
        self.passwordTextField.setMaximumSize(QSize(100, 30))
        # self.passwordTextField.setText("")

        self.connectionStatus = QLabel("Status: No connection")

        self.okButton = QPushButton("Connect")
        self.okButton.clicked.connect(self.accept)
        self.okButton.setMaximumSize(QSize(100, 30))

        # Add widget to a layout
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.addWidget(serverLabel)
        layout.addWidget(self.serverTextField)
        layout.addWidget(portLabel)
        layout.addWidget(self.portTextField)
        layout.addWidget(usernameLabel)
        layout.addWidget(self.usernameTextField)
        layout.addWidget(passwordLabel)
        layout.addWidget(self.passwordTextField)
        # layout.addWidget(self.okButton, 0, Qt.AlignCenter)
        layout.addWidget(self.okButton)
        layout.addSpacing(10)
        layout.addWidget(self.connectionStatus)
        layout.addSpacerItem(QSpacerItem(0, 0, vPolicy=QSizePolicy.Expanding))

        # Apply layout to the drawer
        self._drawer.setLayout(layout)

    def accept(self):
        """
        code executed when the button is pressed
        """

        # std_base64chars = "+"
        # custom_base64chars = ")"
        # for some reason the server replaces the + sign by empty spaces when receiving base64 data. Which is why I replace it with )

        username = str(self.usernameTextField.text())
        password = str(self.passwordTextField.text())
        server = str(self.serverTextField.text())
        port = str(self.portTextField.text())
        request = urllib.request.Request(
            '{}:{}/api/login'.format(server, port))
        request.add_header('username', username)
        request.add_header('password', password)
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        try:
            result = urllib.request.urlopen(request, context=context)
            # Reached if the response status code was 200
            self.connectionStatus.setText("Status: Connected")

            credDict = {
                'username': username,
                'password': password,
                'port': port,
                'server': server,
            }
            self.topLevelOperatorView.OutputCreds.setValue(credDict)

            body = result.read()

            serviceList = np.load(BytesIO(body))['services']
            self.topLevelOperatorView.OutputServiceList.setValue(serviceList)

            dataList = np.load(BytesIO(body))['data']
            self.topLevelOperatorView.OutputDataList.setValue(dataList)

            ccboostModelList = np.load(BytesIO(body))['ccboostModels']
            self.topLevelOperatorView.OutputCCboostModelList.setValue(ccboostModelList)

            unetGadModelList = np.load(BytesIO(body))['unetGadModels']
            self.topLevelOperatorView.OutputUnetGadModelList.setValue(unetGadModelList)

            unetDensityModelList = np.load(BytesIO(body))['vesicleDensityModels']
            self.topLevelOperatorView.OutputUnetDensityModelList.setValue(unetDensityModelList)

            # Unlock the next applets (notifies the workflow)
            self.parentApplet.appletStateUpdateRequested()
        except urllib.error.HTTPError as e:
            status = e.getcode()
            if status == 401:
                self.connectionStatus.setText(
                    "Status: 401 (Unauthorized)\n"
                    "Bad user/password?")
            elif status == 500:
                self.connectionStatus.setText("Status: 500 (Internal error)")
        except urllib.error.URLError as e:
            self.connectionStatus.setText("Status: Cannot reach server.\n"
                                          "Is it running? Is your VPN set up?")

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
