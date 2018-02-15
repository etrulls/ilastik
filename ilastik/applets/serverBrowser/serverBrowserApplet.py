from ilastik.applets.base.standardApplet import StandardApplet

from .opServerBrowser import OpServerBrowser


class ServerBrowserApplet(StandardApplet):

    def __init__(self, workflow, guiName):
        super(ServerBrowserApplet, self).__init__(guiName, workflow)
        self.workflow = workflow

    @property
    def singleLaneOperatorClass(self):
        return OpServerBrowser

    @property
    def broadcastingSlots(self):
        return []

    @property
    def singleLaneGuiClass(self):
        from .serverBrowserGui import ServerBrowserGui
        return ServerBrowserGui

    @property
    def dataSerializers(self):
        return []
