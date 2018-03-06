from __future__ import absolute_import
from lazyflow.graph import Operator, InputSlot, OutputSlot

import numpy
import os
from PIL import Image
from lazyflow.operators.ioOperators import OpInputDataReader
import tempfile


class OpLogin(Operator):
    name = "OpLogin"

    InputImage = InputSlot()

    # Will be an np array containing username + password
    OutputCreds = OutputSlot()
    OutputServiceList = OutputSlot()
    OutputDataList = OutputSlot()
    OutputModelList = OutputSlot()

    def setupOutputs(self):
        # overriding this function is necessary for the program to work
        # even if what we do in it is useless.
        self.OutputCreds.setValue([None])
