from lazyflow.graph import Operator, InputSlot, OutputSlot
from lazyflow.operators.ioOperators import OpInputDataReader

class OpServerBrowser(Operator):
    name = "OpServerBrowser"
    
    InputImage = InputSlot()
    InputDataList = InputSlot()
    InputModelList = InputSlot()
    InputCreds = InputSlot()
    OutputSelectedDatasetName = OutputSlot()
    OutputSelectedModelNameAndArgs = OutputSlot()
    OutputSelectedMode = OutputSlot()

    def propagateDirty(self, slot, subindex, roi):
        return NotImplemented
    
    def setupOutputs(self):
        self.OutputSelectedDatasetName.setValue([])
        self.OutputSelectedModelNameAndArgs.setValue([])



