###############################################################################
#   ilastik: interactive learning and segmentation toolkit
#
#       Copyright (C) 2011-2014, the ilastik developers
#                                <team@ilastik.org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# In addition, as a special exception, the copyright holders of
# ilastik give you permission to combine ilastik with applets,
# workflows and plugins which are not covered under the GNU
# General Public License.
#
# See the LICENSE file for details. License information is also available
# on the ilastik web site at:
#                  http://ilastik.org/license.html
###############################################################################

from ilastik.config import cfg as ilastik_config
from ilastik.workflow import Workflow
from ilastik.applets.dataSelection import DataSelectionApplet
from ilastik.applets.login import LoginApplet
from ilastik.applets.sendToServ import SendToServApplet, SendToServDataExportApplet
from ilastik.applets.serverBrowser import ServerBrowserApplet
from ilastik.applets.remoteServerLabeling import LabelingSingleLaneApplet

from lazyflow.graph import Graph


# Ilastik-side plug-in for remote computation developed by CVlab@EPFL
# Find the server at: TODO add repo link
# CCboost -> https://infoscience.epfl.ch/record/183638/files/Becker13TMI.pdf
# Others...


class RemoteServerWorkflow(Workflow):
    workflowName = "Remote server plug-in"
    worflowDescription = "Remote server computation plug-in for ilastik"
    # Go directly to the login applet
    defaultAppletIndex = 1

    @property
    def applets(self):
        return self._applets

    @property
    def imageNameListSlot(self):
        return self.dataSelectionApplet.topLevelOperator.ImageName

    def __init__(self, shell, headless, workflow_cmdline_args,
                 project_creation_args, *args, **kwargs):
        # Create a graph to be shared by all operators
        graph = Graph()
        super(RemoteServerWorkflow,
              self).__init__(shell,
                             headless,
                             workflow_cmdline_args,
                             project_creation_args,
                             graph=graph,
                             *args,
                             **kwargs)

        self._applets = []

        # Parse workflow-specific command-line args
        # TODO allow command-line (does this make sense? probably not...)
        # parsed_creation_args, unused_args = parser.parse_known_args(
        #     project_creation_args)

        # Create applets
        self.dataSelectionApplet = DataSelectionApplet(
            self,
            "Remote Computation Plug-in",
            "Input Data",
            supportIlastik05Import=True,
            batchDataGui=False)
        self.loginApplet = LoginApplet(self, "Log In")
        self.serverBrowserApplet = ServerBrowserApplet(self, "Remote Service")
        self.labelingSingleLaneApplet = LabelingSingleLaneApplet(self, "Labeling")
        self.sendToServApplet = SendToServApplet(self, "Request Service")

        opDataSelection = self.dataSelectionApplet.topLevelOperator
        opDataSelection.DatasetRoles.setValue(["Raw Data"])

        # Append applets
        self._applets.append(self.dataSelectionApplet)
        self._applets.append(self.loginApplet)
        self._applets.append(self.serverBrowserApplet)
        self._applets.append(self.labelingSingleLaneApplet)
        self._applets.append(self.sendToServApplet)

    def connectLane(self, laneIndex):
        opDataSelection = self.dataSelectionApplet.topLevelOperator.getLane(laneIndex)
        opSingleLaneLabeling = self.labelingSingleLaneApplet.topLevelOperator.getLane(laneIndex)
        opSendToServ = self.sendToServApplet.topLevelOperator.getLane(laneIndex)
        opLogin = self.loginApplet.topLevelOperator.getLane(laneIndex)
        opServerBrowser = self.serverBrowserApplet.topLevelOperator.getLane(laneIndex)

        # Connect top-level operators
        opLogin.InputImage.connect(opDataSelection.Image)

        opServerBrowser.InputCreds.connect(opLogin.OutputCreds)
        opServerBrowser.InputImage.connect(opDataSelection.Image)
        opServerBrowser.InputServiceList.connect(opLogin.OutputServiceList)
        opServerBrowser.InputDataList.connect(opLogin.OutputDataList)
        opServerBrowser.InputCCboostModelList.connect(opLogin.OutputCCboostModelList)
        opServerBrowser.InputUnetGadModelList.connect(opLogin.OutputUnetGadModelList)

        opSingleLaneLabeling.InputImage.connect(opDataSelection.Image)

        opSendToServ.InputCreds.connect(opLogin.OutputCreds)
        opSendToServ.InputImage.connect(opDataSelection.Image)
        opSendToServ.InputLabel.connect(opSingleLaneLabeling.LabelImage)
        opSendToServ.InputSelectedDatasetName.connect(opServerBrowser.OutputSelectedDatasetName)
        opSendToServ.InputSelectedModelNameAndArgs.connect(opServerBrowser.OutputSelectedModelNameAndArgs)
        opSendToServ.InputSelectedMode.connect(opServerBrowser.OutputSelectedMode)
        opSendToServ.InputSelectedServiceName.connect(opServerBrowser.OutputSelectedServiceName)

    def handleAppletStateUpdateRequested(self):
        """
        Overridden from Workflow base class
        Called when an applet has fired the :py:attr:`Applet.appletStateUpdateRequested`
        """
        opLogin = self.loginApplet.topLevelOperator
        loginOutput = opLogin.OutputCreds
        # Username, password, server, port
        login_ready = len(loginOutput) > 0 and  \
            loginOutput[0].ready() and \
            len(loginOutput[0].value) >= 4

        opServerBrowser = self.serverBrowserApplet.topLevelOperator
        datasetSelectionOutput = opServerBrowser.OutputSelectedDatasetName
        modelSelectionOutput = opServerBrowser.OutputSelectedModelNameAndArgs
        selection_ready = login_ready and \
            len(datasetSelectionOutput) > 0 and  \
            len(modelSelectionOutput) > 0 and \
            datasetSelectionOutput[0].ready() and \
            modelSelectionOutput[0].ready() and \
            len(datasetSelectionOutput[0].value) > 0 and \
            len(modelSelectionOutput[0].value) > 0

        modeOutput = opServerBrowser.OutputSelectedMode
        labeling_ready = selection_ready and \
            len(modeOutput) > 0 and \
            modeOutput[0].ready() and \
            len(modeOutput[0].value) > 0 and \
            (modeOutput[0].value == 'train' or
             modeOutput[0].value == 'trainOldData')

        # This applet is used to inject the image into the lane
        self._shell.setAppletEnabled(self.dataSelectionApplet, False)
        # No interaction with user
        self._shell.setAppletEnabled(self.serverBrowserApplet, login_ready)
        self._shell.setAppletEnabled(self.labelingSingleLaneApplet, True)
        self._shell.setAppletEnabled(self.labelingSingleLaneApplet, labeling_ready)
        self._shell.setAppletEnabled(self.sendToServApplet, selection_ready)

    def onProjectLoaded(self, projectManager):
        # Will load placeholder
        self.dataSelectionApplet.setInput()

    def addImageStatic(self, path):
        self.disconnectAll(0)
        self.dataSelectionApplet.setInput(0, path)
        self.reconnectAll(0)

    def addImageFromDisk(self):
        """
        Let's the user select a file from disk

        NOTE ON THE IMPLEMENTATION :
        For some weird reason, Ilastik sets all slots to null when the image is changed, even though we write to the same lane
        to counter this, we save the necessary old values and set them back after the new image is imported
        Ilastik doesn't allow changing values of slots which are already connected, which is why we need to disconnect them before changing their value.
        """
        self.disconnectAll(0)
        self.dataSelectionApplet.selectInputFromDisk(0)
        self.reconnectAll(0)

    def disconnectAll(self, laneIndex):
        # opDataSelection = self.dataSelectionApplet.topLevelOperator.getLane(laneIndex)
        opSingleLaneLabeling = self.labelingSingleLaneApplet.topLevelOperator.getLane(laneIndex)
        opSendToServ = self.sendToServApplet.topLevelOperator.getLane(laneIndex)
        opLogin = self.loginApplet.topLevelOperator.getLane(laneIndex)
        opServerBrowser = self.serverBrowserApplet.topLevelOperator.getLane(laneIndex)

        # Connect top-level operators
        opLogin.InputImage.disconnect()

        self.oldCreds = opLogin.OutputCreds.value
        opServerBrowser.InputCreds.disconnect()
        opServerBrowser.InputImage.disconnect()
        opServerBrowser.InputDataList.disconnect()
        opServerBrowser.InputCCboostModelList.disconnect()
        opServerBrowser.InputUnetGadModelList.disconnect()

        opSingleLaneLabeling.InputImage.disconnect()

        opSendToServ.InputCreds.disconnect()
        opSendToServ.InputImage.disconnect()
        opSendToServ.InputLabel.disconnect()
        opSendToServ.InputSelectedDatasetName.disconnect()
        opSendToServ.InputSelectedModelNameAndArgs.disconnect()
        opSendToServ.InputSelectedMode.disconnect()
        opSendToServ.InputSelectedServiceName.disconnect()

    def reconnectAll(self, laneIndex):
        opDataSelection = self.dataSelectionApplet.topLevelOperator.getLane(laneIndex)
        opSingleLaneLabeling = self.labelingSingleLaneApplet.topLevelOperator.getLane(laneIndex)
        opSendToServ = self.sendToServApplet.topLevelOperator.getLane(laneIndex)
        opLogin = self.loginApplet.topLevelOperator.getLane(laneIndex)
        opServerBrowser = self.serverBrowserApplet.topLevelOperator.getLane(laneIndex)

        # Connect top-level operators
        opLogin.InputImage.connect(opDataSelection.Image)

        opServerBrowser.InputCreds.connect(opLogin.OutputCreds)
        opServerBrowser.InputImage.connect(opDataSelection.Image)
        opServerBrowser.InputDataList.connect(opLogin.OutputDataList)
        opServerBrowser.InputCCboostModelList.connect(opLogin.OutputCCboostModelList)
        opServerBrowser.InputUnetGadModelList.connect(opLogin.OutputUnetGadModelList)

        opLogin.OutputCreds.setValue(self.oldCreds)

        opSingleLaneLabeling.InputImage.connect(opDataSelection.Image)

        opSendToServ.InputCreds.connect(opLogin.OutputCreds)
        opSendToServ.InputImage.connect(opDataSelection.Image)
        opSendToServ.InputLabel.connect(opSingleLaneLabeling.LabelImage)
        opSendToServ.InputSelectedDatasetName.connect(opServerBrowser.OutputSelectedDatasetName)
        opSendToServ.InputSelectedModelNameAndArgs.connect(opServerBrowser.OutputSelectedModelNameAndArgs)
        opSendToServ.InputSelectedMode.connect(opServerBrowser.OutputSelectedMode)
        opSendToServ.InputSelectedServiceName.connect(opServerBrowser.OutputSelectedServiceName)
