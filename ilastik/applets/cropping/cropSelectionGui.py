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
#		   http://ilastik.org/license.html
###############################################################################
import os
from functools import partial

import numpy
from PyQt4 import uic
from PyQt4.QtGui import QVBoxLayout, QSpacerItem, QSizePolicy, QColor
from PyQt4.QtCore import pyqtSlot

from ilastik.applets.layerViewer.layerViewerGui import LayerViewerGui
from ilastik.widgets.cropListView import CropListView
from ilastik.applets.cropping.croppingGui import CroppingGui
from ilastik.utility import bind
from ilastik.utility.gui import threadRouted
from lazyflow.operators import OpCompressedUserCropArray
#from lazyflow.operators import OpValueCache, OpTrainClassifierBlocked, OpClassifierPredict,\
#                               OpSlicedBlockedArrayCache, OpMultiArraySlicer2, \
#                               OpPixelOperator, OpMaxChannelIndicatorOperator, OpCompressedUserLabelArray

def _listReplace(old, new):
    if len(old) > len(new):
        return new + old[len(new):]
    else:
        return new

class CropSelectionGui(CroppingGui):
    """
    Crop selection applet Gui
    """
    ###########################################
    ### AppletGuiInterface Concrete Methods ###
    ###########################################

    def appletDrawer(self):
        return self._drawer

    def centralWidget( self ):
        return self

    def stopAndCleanUp(self):
        for fn in self.__cleanup_fns:
            fn()

        # Base class
        super(CropSelectionGui, self).stopAndCleanUp()

    #def viewerControlWidget(self):
    #    return self._viewerControlUi

#    @property
#    def crops(self):
#        return self._crops
#
#    @crops.setter
#    def crops(self,cropList):
#        self._crops = cropList




    def __init__(self, parentApplet, topLevelOperatorView):
        """
        """
        self.topLevelOperatorView = topLevelOperatorView

        # Tell our base class which slots to monitor
        cropSlots = CroppingGui.CroppingSlots()
        cropSlots.cropInput = topLevelOperatorView.CropInputs
        cropSlots.cropOutput = topLevelOperatorView.CropOutput
        cropSlots.cropEraserValue = topLevelOperatorView.opCropPipeline.opCropArray.eraser
        cropSlots.cropDelete = topLevelOperatorView.opCropPipeline.DeleteCrop
        cropSlots.cropNames = topLevelOperatorView.CropNames
        cropSlots.cropsAllowed = topLevelOperatorView.CropsAllowedFlags

        # We provide our own UI file (which adds an extra control for interactive mode)
        self.uiPath = os.path.split(__file__)[0] + '/cropSelectionWidget.ui'

        super(CropSelectionGui, self).__init__(parentApplet, cropSlots, self.topLevelOperatorView, self.uiPath )

        self.topLevelOperatorView = topLevelOperatorView
        self.topLevelOperatorView.CropNames.notifyDirty( bind(self.handleCropSelectionChange) )
        self.__cleanup_fns = []
        self.__cleanup_fns.append( partial( self.topLevelOperatorView.CropNames.unregisterDirty, bind(self.handleCropSelectionChange) ) )

        self.render = False
        self._renderMgr = None
        self._renderedLayers = {} # (layer name, label number)

        # Always off for now (see note above)
        if self.render:
            try:
                self._renderMgr = RenderingManager( self.editor.view3d )
            except:
                self.render = False

    def initAppletDrawerUi(self):
        localDir = os.path.split(__file__)[0]
        self._drawer = self._cropControlUi#uic.loadUi(localDir+"/drawer.ui")

        #self.cropSelectionWidget = CropSelectionWidget(self)
        #self.uiPath = self.cropSelectionWidget.uiPath

        data_has_z_axis = True
        if self.topLevelOperatorView.InputImage.ready():
            tShape = self.topLevelOperatorView.InputImage.meta.getTaggedShape()
            if not 'z' in tShape or tShape['z']==1:
                data_has_z_axis = False

        self._cropControlUi._minSliderZ.setVisible(data_has_z_axis)
        self._cropControlUi._minSliderZ.setVisible(data_has_z_axis)
        self._cropControlUi._maxSliderZ.setVisible(data_has_z_axis)
        self._cropControlUi._minSpinZ.setVisible(data_has_z_axis)
        self._cropControlUi._maxSpinZ.setVisible(data_has_z_axis)
        self._cropControlUi.labelMinZ.setVisible(data_has_z_axis)
        self._cropControlUi.labelMaxZ.setVisible(data_has_z_axis)

        self._cropControlUi.AddCropButton.clicked.connect( bind (self.newCrop) )
        self._cropControlUi.SetCropButton.clicked.connect( bind (self.setCrop) )

        self.topLevelOperatorView.MinValueT.notifyDirty(self.apply_operator_settings_to_gui)
        self.topLevelOperatorView.MaxValueT.notifyDirty(self.apply_operator_settings_to_gui)
        self.topLevelOperatorView.MinValueX.notifyDirty(self.apply_operator_settings_to_gui)
        self.topLevelOperatorView.MaxValueX.notifyDirty(self.apply_operator_settings_to_gui)
        self.topLevelOperatorView.MinValueY.notifyDirty(self.apply_operator_settings_to_gui)
        self.topLevelOperatorView.MaxValueY.notifyDirty(self.apply_operator_settings_to_gui)
        self.topLevelOperatorView.MinValueZ.notifyDirty(self.apply_operator_settings_to_gui)
        self.topLevelOperatorView.MaxValueZ.notifyDirty(self.apply_operator_settings_to_gui)

        self.topLevelOperatorView.InputImage.notifyDirty(self.setDefaultValues)
        self.topLevelOperatorView.PredictionImage.notifyDirty(self.setDefaultValues)

        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.addWidget( self._cropControlUi )
        layout.addSpacerItem( QSpacerItem(0,0,vPolicy=QSizePolicy.Expanding) )

        #self._drawer.setLayout( layout )

        self.setDefaultValues()
        self.apply_operator_settings_to_gui()

        self.editor.showCropLines(True)
        self.editor.cropModel.changed.connect(self.onCropModelChanged)
        self.editor.posModel.timeChanged.connect(self.updateTime)
        self._cropControlUi._minSliderT.valueChanged.connect(self._onMinSliderTMoved)
        self._cropControlUi._maxSliderT.valueChanged.connect(self._onMaxSliderTMoved)
        self._cropControlUi._minSliderX.valueChanged.connect(self._onMinSliderXMoved)
        self._cropControlUi._maxSliderX.valueChanged.connect(self._onMaxSliderXMoved)
        self._cropControlUi._minSliderY.valueChanged.connect(self._onMinSliderYMoved)
        self._cropControlUi._maxSliderY.valueChanged.connect(self._onMaxSliderYMoved)
        self._cropControlUi._minSliderZ.valueChanged.connect(self._onMinSliderZMoved)
        self._cropControlUi._maxSliderZ.valueChanged.connect(self._onMaxSliderZMoved)

        self._cropControlUi.cropListView.deleteCrop.connect(self.onDeleteCrop)

        # The editor's layerstack is in charge of which layer movement buttons are enabled
        #model = self.editor.layerStack
        #self._viewerControlUi.viewerControls.setupConnections(model)

        #if hasattr(_cropControlUi, "AddCropButton"):
        #    _cropControlUi.AddCropButton.setIcon( QIcon(ilastikIcons.AddSel) )
        #    _cropControlUi.AddCropButton.clicked.connect( bind(self._addNewCrop) )
        #_cropControlUi.cropListModel.dataChanged.connect(self.onCropListDataChanged)

    @pyqtSlot()
    @threadRouted
    def handleCropSelectionChange(self):
        enabled = False
        if self.topLevelOperatorView.CropNames.ready():
            enabled = True
            enabled &= len(self.topLevelOperatorView.CropNames.value) > 0
            #enabled &= len(self.topLevelOperatorView.CropNames.value) >= 2
            #enabled &= numpy.all(numpy.asarray(self.topLevelOperatorView.CachedFeatureImages.meta.shape) > 0)
            # FIXME: also check that each label has scribbles?

        self._cropControlUi.cropListView.update()

    def _getNext(self, slot, parentFun, transform=None):
        numCrops = self.cropListData.rowCount()
        value = slot.value
        if numCrops < len(value):
            result = value[numCrops]
            if transform is not None:
                result = transform(result)
            return result
        else:
            return parentFun()

    def _onCropChanged(self, parentFun, mapf, slot):
        parentFun()
        new = map(mapf, self.cropListData)
        old = slot.value
        slot.setValue(_listReplace(old, new))

    def _onCropRemoved(self, parent, start, end):
        # Call the base class to update the operator.
        if self.cropListData.rowCount() > 1:
            super(CropSelectionGui, self)._onCropRemoved(parent, start, end)

            # Keep colors in sync with names
            # (If we deleted a name, delete its corresponding colors, too.)
            op = self.topLevelOperatorView
            if len(op.PmapColors.value) > len(op.CropNames.value):
                for slot in (op.CropColors, op.PmapColors):
                    value = slot.value
                    value.pop(start)
                    # Force dirty propagation even though the list id is unchanged.
                    slot.setValue(value, check_changed=False)

    def onDeleteCrop(self, position):
        if len(self._crops) > 1:
            del self._crops[self._cropControlUi.cropListModel[position].name]

    def getNextCropName(self):
        return self._getNext(self.topLevelOperatorView.CropNames,
                             super(CropSelectionGui, self).getNextCropName)

    def getNextCropColor(self):
        return self._getNext(
            self.topLevelOperatorView.CropColors,
            super(CropSelectionGui, self).getNextCropColor,
            lambda x: QColor(*x)
        )

    def getNextPmapColor(self):
        return self._getNext(
            self.topLevelOperatorView.PmapColors,
            super(CropSelectionGui, self).getNextPmapColor,
            lambda x: QColor(*x)
        )

    def onCropNameChanged(self):
        self._onCropChanged(super(CropSelectionGui, self).onCropNameChanged,
                             lambda l: l.name,
                             self.topLevelOperatorView.CropNames)

    def onCropColorChanged(self):
        self._onCropChanged(super(CropSelectionGui, self).onCropColorChanged,
                             lambda l: (l.brushColor().red(),
                                        l.brushColor().green(),
                                        l.brushColor().blue()),
                             self.topLevelOperatorView.CropColors)

    def _update_rendering(self):
        if not self.render:
            return
        shape = self.topLevelOperatorView.InputImages.meta.shape[1:4]
        if len(shape) != 5:
            #this might be a 2D image, no need for updating any 3D stuff
            return

        time = self.editor.posModel.slicingPos5D[0]
        if not self._renderMgr.ready:
            self._renderMgr.setup(shape)

        layernames = set(layer.name for layer in self.layerstack)
        self._renderedLayers = dict((k, v) for k, v in self._renderedLayers.iteritems()
                                if k in layernames)

        newvolume = numpy.zeros(shape, dtype=numpy.uint8)
        for layer in self.layerstack:
            try:
                crop = self._renderedLayers[layer.name]
            except KeyError:
                continue
            for ds in layer.datasources:
                vol = ds.dataSlot.value[time, ..., 0]
                indices = numpy.where(vol != 0)
                newvolume[indices] = crop

        self._renderMgr.volume = newvolume
        self._update_colors()
        self._renderMgr.update()

    def _update_colors(self):
        for layer in self.layerstack:
            try:
                crop = self._renderedLayers[layer.name]
            except KeyError:
                continue
            color = layer.tintColor
            color = (color.red() / 255.0, color.green() / 255.0, color.blue() / 255.0)
            self._renderMgr.setColor(crop, color)

    def newCrop(self):
        self.apply_gui_settings_to_operator()
        self._addNewCrop()

    def setCrop(self):
        self.apply_gui_settings_to_operator()
        self._crops [self._cropControlUi.cropListModel[self._cropControlUi.cropListModel.selectedRow()].name]=self.editor.cropModel.get_roi_3d()
        if not (self.editor.cropModel._crop_extents[0][0]  == None or self.editor.cropModel.cropZero()):
            cropMidPos = [(b+a)/2 for [a,b] in self.editor.cropModel._crop_extents]
            for i in range(3):
                self.editor.navCtrl.changeSliceAbsolute(cropMidPos[i],i)

        self.topLevelOperatorView.Crops.setValue(self._crops)


    def getNextCropName(self):
        return "Crop {}".format(self._maxCropNumUsed+1)

    def getNextCropColor(self):
        """
        Return a QColor to use for the next crop.
        """
        #numCrops = len(self._cropControlUi.cropListModel)
        numCrops = self._maxCropNumUsed+1
        if numCrops >= len(self._colorTable16)-1:
            # If the color table isn't large enough to handle all our crops,
            #  append a random color
            randomColor = QColor(numpy.random.randint(0,255), numpy.random.randint(0,255), numpy.random.randint(0,255))
            self._colorTable16.append( randomColor.rgba() )

        color = QColor()
        color.setRgba(self._colorTable16[numCrops+1]) # First entry is transparent (for zero crop)
        return color

    def numCrops(self):
        return len(self._crops)

    def get_roi_4d(self):
        return [(self.topLevelOperatorView.MinValueT.value,self.topLevelOperatorView.MinValueX.value,self.topLevelOperatorView.MinValueY.value,self.topLevelOperatorView.MinValueZ.value),
                (self.topLevelOperatorView.MaxValueT.value,self.topLevelOperatorView.MaxValueX.value,self.topLevelOperatorView.MaxValueY.value,self.topLevelOperatorView.MaxValueZ.value)]

    def updateTime(self):
        delta = self._cropControlUi._minSliderT.value() - self.editor.posModel.time
        if delta > 0:
            self.editor.navCtrl.changeTimeRelative(delta)
        else:
            delta = self._cropControlUi._maxSliderT.value() - self.editor.posModel.time
            if delta < 0:
                self.editor.navCtrl.changeTimeRelative(delta)

    def _onMinSliderTMoved(self):
        delta = self._cropControlUi._minSliderT.value() - self.editor.posModel.time
        if delta > 0:
            self.editor.navCtrl.changeTimeRelative(delta)
        self.topLevelOperatorView.MinValueT.setValue(self._cropControlUi._minSliderT.value())

    def _onMaxSliderTMoved(self):
        delta = self._cropControlUi._maxSliderT.value() - self.editor.posModel.time
        if delta < 0:
            self.editor.navCtrl.changeTimeRelative(delta)
        self.topLevelOperatorView.MaxValueT.setValue(self._cropControlUi._maxSliderT.value())

    def _onMinSliderXMoved(self):
        [(minValueX,minValueY,minValueZ),(maxValueX,maxValueY,maxValueZ)] = self.editor.cropModel.get_roi_3d()
        self.editor.cropModel.set_roi_3d([(self._cropControlUi._minSliderX.value(),minValueY,minValueZ),(maxValueX,maxValueY,maxValueZ)])

    def _onMaxSliderXMoved(self):
        [(minValueX,minValueY,minValueZ),(maxValueX,maxValueY,maxValueZ)] = self.editor.cropModel.get_roi_3d()
        self.editor.cropModel.set_roi_3d([(minValueX,minValueY,minValueZ),(self._cropControlUi._maxSliderX.value()+1,maxValueY,maxValueZ)])

    def _onMinSliderYMoved(self):
        [(minValueX,minValueY,minValueZ),(maxValueX,maxValueY,maxValueZ)] = self.editor.cropModel.get_roi_3d()
        self.editor.cropModel.set_roi_3d([(minValueX,self._cropControlUi._minSliderY.value(),minValueZ),(maxValueX,maxValueY,maxValueZ)])

    def _onMaxSliderYMoved(self):
        [(minValueX,minValueY,minValueZ),(maxValueX,maxValueY,maxValueZ)] = self.editor.cropModel.get_roi_3d()
        self.editor.cropModel.set_roi_3d([(minValueX,minValueY,minValueZ),(maxValueX,self._cropControlUi._maxSliderY.value()+1,maxValueZ)])

    def _onMinSliderZMoved(self):
        [(minValueX,minValueY,minValueZ),(maxValueX,maxValueY,maxValueZ)] = self.editor.cropModel.get_roi_3d()
        self.editor.cropModel.set_roi_3d([(minValueX,minValueY,self._cropControlUi._minSliderZ.value()),(maxValueX,maxValueY,maxValueZ)])

    def _onMaxSliderZMoved(self):
        [(minValueX,minValueY,minValueZ),(maxValueX,maxValueY,maxValueZ)] = self.editor.cropModel.get_roi_3d()
        self.editor.cropModel.set_roi_3d([(minValueX,minValueY,minValueZ),(maxValueX,maxValueY,self._cropControlUi._maxSliderZ.value()+1)])

    def onCropModelChanged(self):
        starts, stops = self.editor.cropModel.get_roi_3d()
        for dim, start, stop in zip("xyz", starts, stops):
            if dim=='x':
                self.topLevelOperatorView.MinValueX.setValue(start)
                self.topLevelOperatorView.MaxValueX.setValue(stop)
            elif dim=='y':
                self.topLevelOperatorView.MinValueY.setValue(start)
                self.topLevelOperatorView.MaxValueY.setValue(stop)
            elif dim=='z':
                self.topLevelOperatorView.MinValueZ.setValue(start)
                self.topLevelOperatorView.MaxValueZ.setValue(stop)
            else:
                print "ERROR: Setting up an axis that does NOT exist!"

        return [[start, stop] for dim, start, stop in zip("xyz", starts, stops)]

    def _onCropSelected(self, row):
        #logger.debug("switching to crop=%r" % (self._cropControlUi.cropListModel[row]))

        self.editor.brushingModel.setDrawnNumber(row+1)
        brushColor = self._cropControlUi.cropListModel[row].brushColor()
        self.editor.brushingModel.setBrushColor( brushColor )

        self.editor.cropModel.set_roi_3d(self._crops[self._cropControlUi.cropListModel[row].name])
        if not (self.editor.cropModel._crop_extents[0][0]  == None or self.editor.cropModel.cropZero()):
            cropMidPos = [(b+a)/2 for [a,b] in self.editor.cropModel._crop_extents]
            for i in range(3):
                self.editor.navCtrl.changeSliceAbsolute(cropMidPos[i],i)

        self.editor.cropModel._cropColor = QColor.cyan#self._cropControlUi.cropListModel[row].brushColor
        self.editor.cropModel.colorChanged.emit()#self.editor.cropModel)#self._cropControlUi.cropListModel[row].brushColor)


    def apply_operator_settings_to_gui(self,*args):
        minValueT, maxValueT, minValueX, maxValueX, minValueY, maxValueY, minValueZ, maxValueZ = [0]*8

        inputImageSlot = self.topLevelOperatorView.InputImage
        tagged_shape = inputImageSlot.meta.getTaggedShape()

        self.editor.posModel.shape5D = [tagged_shape['t'],tagged_shape['x'],tagged_shape['y'],tagged_shape['z'],tagged_shape['c']]

        # t
        if self.topLevelOperatorView.MinValueT.ready():
            minValueT = self.topLevelOperatorView.MinValueT.value
        if self.topLevelOperatorView.MaxValueT.ready():
            maxValueT = self.topLevelOperatorView.MaxValueT.value
        if maxValueT == 0:
            maxValueT =  tagged_shape['t']-1

        # x
        if self.topLevelOperatorView.MinValueX.ready():
            minValueX = self.topLevelOperatorView.MinValueX.value
        if self.topLevelOperatorView.MaxValueX.ready():
            maxValueX = self.topLevelOperatorView.MaxValueX.value

        # y
        if self.topLevelOperatorView.MinValueY.ready():
            minValueY = self.topLevelOperatorView.MinValueY.value
        if self.topLevelOperatorView.MaxValueY.ready():
            maxValueY = self.topLevelOperatorView.MaxValueY.value

        # z
        if self.topLevelOperatorView.MinValueZ.ready():
            minValueZ = self.topLevelOperatorView.MinValueZ.value
        if self.topLevelOperatorView.MaxValueZ.ready():
            maxValueZ = self.topLevelOperatorView.MaxValueZ.value

        self.editor.cropModel.set_roi_3d([(minValueX,minValueY,minValueZ),(maxValueX,maxValueY,maxValueZ)])
        self._cropControlUi.setValue(minValueT, maxValueT, minValueX, maxValueX-1, minValueY, maxValueY-1, minValueZ, maxValueZ-1)
        self.updateTime()

    def setTimeValues(self, minValueT, maxValueT):
        self.topLevelOperatorView.MinValueT.setValue(minValueT)
        self.topLevelOperatorView.MaxValueT.setValue(maxValueT)

    def setValues(self, minValueT, maxValueT, minValueX, maxValueX, minValueY, maxValueY, minValueZ, maxValueZ):
        self.topLevelOperatorView.MinValueT.setValue(minValueT)
        self.topLevelOperatorView.MaxValueT.setValue(maxValueT)
        self.topLevelOperatorView.MinValueX.setValue(minValueX)
        self.topLevelOperatorView.MaxValueX.setValue(maxValueX)
        self.topLevelOperatorView.MinValueY.setValue(minValueY)
        self.topLevelOperatorView.MaxValueY.setValue(maxValueY)
        self.topLevelOperatorView.MinValueZ.setValue(minValueZ)
        self.topLevelOperatorView.MaxValueZ.setValue(maxValueZ)

    def apply_gui_settings_to_operator(self, ):
        minValueT, maxValueT, minValueX, maxValueX, minValueY, maxValueY, minValueZ, maxValueZ = self._cropControlUi.getValues()
        self.topLevelOperatorView.MinValueT.setValue(minValueT)
        self.topLevelOperatorView.MaxValueT.setValue(maxValueT)

        self.topLevelOperatorView.MinValueX.setValue(minValueX)
        self.topLevelOperatorView.MaxValueX.setValue(maxValueX+1)

        self.topLevelOperatorView.MinValueY.setValue(minValueY)
        self.topLevelOperatorView.MaxValueY.setValue(maxValueY+1)

        self.topLevelOperatorView.MinValueZ.setValue(minValueZ)
        self.topLevelOperatorView.MaxValueZ.setValue(maxValueZ+1)

        self.topLevelOperatorView.Crops.setValue(self._crops)

    def setupLayers(self):
        """
        Overridden from LayerViewerGui.
        Create a list of all layer objects that should be displayed.
        """
        layers = []

        cropImageSlot = self.topLevelOperatorView.CropImage
        if cropImageSlot.ready():
            cropImageLayer = self.createStandardLayerFromSlot( cropImageSlot )
            cropImageLayer.name = "Crop"
            cropImageLayer.visible = False #True
            cropImageLayer.opacity = 0.25
            layers.append(cropImageLayer)

        # Show the prediction data
        predictionImageSlot = self.topLevelOperatorView.PredictionImage
        if predictionImageSlot.ready():
            inputPredictionLayer = self.createStandardLayerFromSlot( predictionImageSlot )
            inputPredictionLayer.name = "Prediction Input"
            inputPredictionLayer.visible = True
            inputPredictionLayer.opacity = 0.75
            layers.append(inputPredictionLayer)

        # Show the raw input data
        inputImageSlot = self.topLevelOperatorView.InputImage
        if inputImageSlot.ready():
            #print " ..... SLT .....> in if inputImageSlot.ready()"
            inputLayer = self.createStandardLayerFromSlot( inputImageSlot )
            inputLayer.name = "Raw Input"
            inputLayer.visible = True
            inputLayer.opacity = 0.75
            layers.append(inputLayer)

        return layers

    def defaultRangeValues(self):
        inputImageSlot = self.topLevelOperatorView.InputImage

        if not inputImageSlot.ready():
            return [0]*8

        tagged_shape = inputImageSlot.meta.getTaggedShape()
        minValueT = 0
        maxValueT = tagged_shape['t']

        # x
        minValueX = 0
        maxValueX = tagged_shape['x']

        # y
        minValueY = 0
        maxValueY = tagged_shape['y']

        # z
        minValueZ = 0
        maxValueZ = tagged_shape['z']

        return minValueT,maxValueT-1,minValueX,maxValueX-1,minValueY,maxValueY-1,minValueZ,maxValueZ-1

    def defaultValues(self):
        inputImageSlot = self.topLevelOperatorView.InputImage
        if not inputImageSlot.ready():
            return [0]*8

        tagged_shape = inputImageSlot.meta.getTaggedShape()
        minValueT = 0
        maxValueT = tagged_shape['t'] - 1

        if self.topLevelOperatorView.MinValueT.ready():
            minValueTnew = self.topLevelOperatorView.MinValueT.value
        else:
            minValueTnew = 0

        if self.topLevelOperatorView.MaxValueT.ready():
            maxValueTnew = self.topLevelOperatorView.MaxValueT.value
        else:
            maxValueTnew = tagged_shape['t'] - 1

        minValueT = max(minValueT,minValueTnew)
        maxValueT = min(maxValueT,maxValueTnew)

        # x
        if self.topLevelOperatorView.MinValueX.ready():
            minValueX = self.topLevelOperatorView.MinValueX.value
        else:
            minValueX = 0
        if self.topLevelOperatorView.MaxValueX.ready():
            maxValueX = self.topLevelOperatorView.MaxValueX.value
        else:
            maxValueX = tagged_shape['x'] - 1

        # y
        if self.topLevelOperatorView.MinValueY.ready():
            minValueY = self.topLevelOperatorView.MinValueY.value
        else:
            minValueY = 0
        if self.topLevelOperatorView.MaxValueY.ready():
            maxValueY = self.topLevelOperatorView.MaxValueY.value
        else:
            maxValueY = tagged_shape['y'] - 1

  # z
        if self.topLevelOperatorView.MinValueZ.ready():
            minValueZ = self.topLevelOperatorView.MinValueZ.value
        else:
            minValueZ = 0
        if self.topLevelOperatorView.MaxValueZ.ready():
            maxValueZ = self.topLevelOperatorView.MaxValueZ.value
        else:
            maxValueZ = tagged_shape['z'] - 1
        self.setValues(minValueT,maxValueT,minValueX,maxValueX,minValueY,maxValueY,minValueZ,maxValueZ)
        return minValueT,maxValueT,minValueX,maxValueX,minValueY,maxValueY,minValueZ,maxValueZ

    def setDefaultValues(self,*args):
        minValueT,maxValueT,minValueX,maxValueX,minValueY,maxValueY,minValueZ,maxValueZ = self.defaultRangeValues()
        self._cropControlUi.setRange(minValueT, maxValueT, minValueX, maxValueX, minValueY, maxValueY, minValueZ, maxValueZ)

        minValueT,maxValueT,minValueX,maxValueX,minValueY,maxValueY,minValueZ,maxValueZ = self.defaultValues()
        self._cropControlUi.setValue(minValueT, maxValueT, minValueX, maxValueX-1, minValueY, maxValueY-1, minValueZ, maxValueZ-1)


