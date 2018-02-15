from __future__ import absolute_import
from ilastik.applets.base.standardApplet import StandardApplet

from .opLogin import OpLogin


class LoginApplet(StandardApplet):

    def __init__(self, workflow, guiName):
        super(LoginApplet, self).__init__(guiName, workflow)

    @property
    def singleLaneOperatorClass(self):
        return OpLogin

    @property
    def broadcastingSlots(self):
        return []

    @property
    def singleLaneGuiClass(self):
        from .loginGui import LoginGui
        return LoginGui

    @property
    def dataSerializers(self):
        return []
