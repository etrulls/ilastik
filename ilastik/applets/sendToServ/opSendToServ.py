from lazyflow.graph import Operator, InputSlot, OutputSlot

import numpy
import os
from PIL import Image
from lazyflow.operators.ioOperators import OpInputDataReader
import tempfile
import numpy as np


class OpSendToServ(Operator):
    name = "OpSendToServ"

    InputImage = InputSlot()

    # An applet waits for all of it's inputs to be set before it allows it's output to be
    # written to, since labels aren't always required we mark this input slot as optional
    # to avoid the outputs staying disabled
    InputLabel = InputSlot(optional=True)

    InputCreds = InputSlot()
    InputSelectedModelNameAndArgs = InputSlot()
    InputSelectedDatasetName = InputSlot()
    InputSelectedMode = InputSlot()
    InputSelectedServiceName = InputSlot()
    ThresholdValue = InputSlot(optional=True)

    Output = OutputSlot()
    OutputThreshold = OutputSlot()

    def setupOutputs(self):
        # copy metadata from input image (same dimensions etc.)
        self.Output.meta.assignFrom(self.InputImage.meta)
        self.OutputThreshold.meta.assignFrom(self.InputImage.meta)

    def propagateDirty(self, slot, subindex, roi):
        self.Output.setDirty(roi)
        # super( OpSendToServ, self ).propagateDirty(slot, subindex, roi)

    def execute(self, slot, subindex, roi, result):
        # Needs to be implemented to prevent exception when user moves thresholder slider before image is ready
        pass
