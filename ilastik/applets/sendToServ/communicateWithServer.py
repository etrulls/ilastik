from PyQt5 import QtCore
from PyQt5.QtCore import QThread, pyqtSignal

import numpy as np
import base64
import urllib
from io import BytesIO
from .readCallbackStream import ReadCallbackStream
import ssl
import sys


class CommunicateWithServer(QThread):
    signal_update_status = pyqtSignal(str, bool)
    signal_communication_ended = pyqtSignal()
    signal_is_finished = pyqtSignal()
    signal_failure = pyqtSignal()

    def __init__(self, creds, datasetName, modelNameAndArgs, mode, imgArray=None, labelArray=None, result=None):
        QThread.__init__(self)
        self.labelArray = labelArray
        self.imgArray = imgArray
        self.creds = creds
        self.datasetName = datasetName
        self.modelNameAndArgs = modelNameAndArgs
        self.result = result
        self.mode = mode

    def __del__(self):
        self.wait()

    def sendWithBody(self, request):
        # For some reason the server replaces the + sign by empty spaces when receiving base64 data. Which is why I replace it with )
        std_base64chars = b"+"
        custom_base64chars = b")"

        # Create a StringIO where we will store and compress the array and send it to the server
        f = BytesIO()
        self.signal_update_status.emit("Status: Compressing data...", False)
        # Saves the arrays in a compressed format (gzip)
        # Used with StringIO, in memory
        # Example of compression with image + labels
        # Before compression: total = 220662048 bytes (220.7MB)
        # After compression: total =  95220490 bytes (95.22MB)
        if self.mode == 'train':
            np.savez_compressed(f, labels=self.labelArray, image=self.imgArray)
        elif self.mode == 'test':
            np.savez_compressed(f, image=self.imgArray)
        f.seek(0)
        compressed_data = f.read()
        compressedData64 = base64.b64encode(compressed_data)
        # Changes + to ) for compatibility with server
        # compressedData64 = compressedData64.translate(string.maketrans(std_base64chars, custom_base64chars))
        compressedData64 = compressedData64.replace(std_base64chars, custom_base64chars)

        self.total = 0

        def callback(num_bytes_read):
            """
            Will be called constantly as a callback during upload, to track progress.
            """
            self.total += num_bytes_read
            self.signal_update_status.emit("Status: Uploading data... {0:.1f}".format(round(
                100 * (float(self.total) / sys.getsizeof(compressedData64)), 2)) + '%', False)
            # print("uploading")

        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        stream = ReadCallbackStream(compressedData64, callback)
        result = urllib.request.urlopen(request, stream, context=context)

        return result

    def run(self):
        """
        code executed when the button is pressed
        """
        try:
            if self.mode == 'train':
                self.labelArray = self.labelArray.value
            self.imgArray = self.imgArray.value
            username = self.creds.value['username']
            password = self.creds.value['password']
            server = self.creds.value['server']
            port = self.creds.value['port']

            if self.mode == 'train':
                request = urllib.request.Request('{}:{}/api/train'.format(server, port))
            elif self.mode=='test':
                request = urllib.request.Request('{}:{}/api/testNewData'.format(server, port))
            elif self.mode=='testOldData':
                request = urllib.request.Request('{}:{}/api/testOldData'.format(server, port))

            # Common parameters
            # Could move some of these these to the body, but they are small enough
            request.add_header('username', username)
            request.add_header('password', password)
            request.add_header('dataset-name', self.datasetName)
            request.add_header('model-name', self.modelNameAndArgs['name'])
            request.add_header('ccboost-mirror', self.modelNameAndArgs['ccboost_mirror'])

            # Train parameters
            if self.mode == 'train':
                request.add_header('ccboost-num-stumps', self.modelNameAndArgs['ccboost_num_stumps'])
                request.add_header('ccboost-inside-pixel', self.modelNameAndArgs['ccboost_inside_pixel'])
                request.add_header('ccboost-outside-pixel', self.modelNameAndArgs['ccboost_outside_pixel'])

            # No need to send the data if it's already in the server
            if self.mode == 'testOldData':
                context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
                result = urllib.request.urlopen(request, context=context)
            else:
                result = self.sendWithBody(request)

            # Hack to avoid the current status from getting deleted.
            # self.signal_update_status.emit('', True)
            self.signal_update_status.emit('Status: Running on server...', True)

            # Read response in chunks to track progress
            totalSize = result.getheader('Content-Length').strip()
            totalSize = int(totalSize)
            data_list = []
            current = 0
            chunk = 4096
            while 1:
                data = result.read(chunk)
                current += len(data)
                if not data:
                    break
                data_list.append(data)
                self.signal_update_status.emit("Status: Downloading... {0:.1f}".format(
                    round(100 * (float(current) / totalSize), 2)) + '%', False)
            self.signal_communication_ended.emit()

            body = b''.join(data_list)

            # If testing with data on server, must also retrieve it here
            # TODO it might be better to do it at the beginning?
            # if self.mode == 'testOldData':
            #     image = np.load(BytesIO(body))['image']
            #     self.result[2] = image
            resultArray = np.load(BytesIO(body))['result']
            self.result[0] = resultArray

            # Threshold
            # print('Results {} {}'.format(resultArray.min(), resultArray.max()))
            thresholded = np.copy(resultArray)
            th = 0
            thresholded[resultArray < th] = 1
            thresholded[resultArray >= th] = 2
            thresholded = thresholded.astype('uint8')
            self.result[1] = thresholded
            self.signal_is_finished.emit()
        except Exception:
            # Kill the probe and update label
            self.signal_failure.emit()
