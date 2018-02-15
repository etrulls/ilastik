from .opSendToServDataExport import OpSendToServDataExport
from ilastik.applets.dataExport.dataExportApplet import DataExportApplet
from ilastik.applets.dataExport.dataExportSerializer import DataExportSerializer

from ilastik.utility import OpMultiLaneWrapper


class SendToServDataExportApplet(DataExportApplet):
    def __init__(self, workflow, title, isBatch=False):
        # Our operator is a subclass of the generic data export operator
        self._topLevelOperator = OpMultiLaneWrapper( OpSendToServDataExport, parent=workflow,
                                     promotedSlotNames=set(['RawData', 'Inputs', 'RawDatasetInfo', 'ConstraintDataset']) )
        self._gui = None
        self._title = title
        self._serializers = [ DataExportSerializer(self._topLevelOperator, title) ]

        # Base class init
        super(SendToServDataExportApplet, self).__init__(workflow, title, isBatch)
        
    @property
    def dataSerializers(self):
        return []

    @property
    def topLevelOperator(self):
        return self._topLevelOperator

    def getMultiLaneGui(self):
        return NotImplemented
       # if self._gui is None:
       #     # Gui is a special subclass of the generic gui
       #     from pixelClassificationDataExportGui import PixelClassificationDataExportGui
       #     self._gui = PixelClassificationDataExportGui( self, self.topLevelOperator )
       # return self._gui

