from ilastik.applets.base.standardApplet import StandardApplet

from .opSendToServ import OpSendToServ

class SendToServApplet( StandardApplet ):

    def __init__( self, workflow, guiName):
        super(SendToServApplet, self).__init__(guiName, workflow)
        self.workflow = workflow

    @property
    def singleLaneOperatorClass(self):
        return OpSendToServ

    @property
    def broadcastingSlots(self):
        return []
    
    @property
    def singleLaneGuiClass(self):
        from .sendToServGui import SendToServGui
        return SendToServGui

    @property
    def dataSerializers(self):
        return []
