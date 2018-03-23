from lazyflow.graph import Operator, InputSlot, OutputSlot
from lazyflow.operators.ioOperators import OpInputDataReader


class OpServerBrowser(Operator):
    name = "OpServerBrowser"

    InputImage = InputSlot()
    InputServiceList = InputSlot()
    InputDataList = InputSlot()
    InputCCboostModelList = InputSlot()
    InputUnetGadModelList = InputSlot()
    InputUnetDensityModelList = InputSlot()
    InputCreds = InputSlot()
    OutputSelectedServiceName = OutputSlot()
    OutputSelectedDatasetName = OutputSlot()
    OutputSelectedModelNameAndArgs = OutputSlot()
    OutputSelectedServiceName = OutputSlot()
    OutputSelectedMode = OutputSlot()

    def propagateDirty(self, slot, subindex, roi):
        return NotImplemented

    def setupOutputs(self):
        self.OutputSelectedServiceName.setValue([])
        self.OutputSelectedDatasetName.setValue([])
        self.OutputSelectedModelNameAndArgs.setValue([])
        self.OutputSelectedServiceName.setValue([])
