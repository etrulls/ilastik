import ssl
import urllib
import urllib.request

import numpy as np
from PyQt5 import QtCore
from PyQt5.QtCore import QThread, pyqtSignal
from io import StringIO, BytesIO
import os
import tempfile


class DatasetDownloader(QThread):
    signal_has_update = pyqtSignal(str)
    signal_is_finished = pyqtSignal()

    def __init__(self, username, password, dataset_name, server, port, result=None):
        QThread.__init__(self)
        self.username = username
        self.password = password
        self.dataset_name = dataset_name
        self.server = server
        self.port = port
        self.result = result

    def __del__(self):
        self.wait()

    def run(self):
        request = urllib.request.Request('{}:{}/api/downloadDataset'.format(self.server, self.port))
        request.add_header('username', self.username)
        request.add_header('password', self.password)
        request.add_header('dataset-name', self.dataset_name)
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        result = urllib.request.urlopen(request, context=context)
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
            # data_list.append(data)
            data_list.append(data)
            # self.emit(SIGNAL('update status'), "\nDownloading... "+ "{0:.2f}".format(round(100*(float(current)/ totalSize),2)) + '%')
            # self.signal_update.emit("\nDownloading... "+ "{0:.2f}".format(round(100*(float(current)/ totalSize),2)) + '%')
            self.signal_has_update.emit("\nDownloading... {0:.2f}".format(
                round(100 * (float(current) / totalSize), 2)) + '%')

        body = b''.join(data_list)
        # dataset = np.load(StringIO(body))['data']
        dataset = np.load(BytesIO(body))['data']

        # we will save this to the user's temp files in order to load it afterwards
        tmpDir = tempfile.gettempdir()
        tmpDir = os.path.join(tmpDir, 'contextFeaturesResult')
        if not os.path.isdir(tmpDir):
            os.mkdir(tmpDir)
        tmpFile = os.path.join(tmpDir, 'tmp.h5')

        import h5py
        h5 = h5py.File(tmpFile, 'w', driver=None)
        h5.create_dataset('data', data=dataset)
        h5.close()
        self.result[0] = tmpFile
        # self.emit(SIGNAL('finished'))
        # self.signal_finished.emit()
        self.signal_is_finished.emit()
