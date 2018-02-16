from PyQt5.QtCore import QThread, pyqtSignal
import urllib
import urllib.request
import ssl


class ServerProgressProber(QThread):
    """
    Probe server during processing to display progress.
    """
    signal_server_log = pyqtSignal(str)

    def __init__(self, creds, datasetName, modelName, probingRate):
        QThread.__init__(self)
        self.creds = creds
        self.datasetName = datasetName
        self.modelName = modelName
        self.probingRate = probingRate

    def __del__(self):
        self.wait()

    def stop(self):
        self.terminate()

    def run(self):
        while True:
            username = self.creds.value['username']
            password = self.creds.value['password']
            server = self.creds.value['server']
            port = self.creds.value['port']
            request = urllib.request.Request('{}:{}/api/getProgress'.format(server, port))
            request.add_header('username', username)
            request.add_header('password', password)
            request.add_header('dataset-name', self.datasetName)
            request.add_header('model-name', self.modelName)
            context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
            # print(username, password, self.datasetName, self.modelName)
            try:
                result = urllib.request.urlopen(request, context=context)
                # print('Result {}'.format(result))
                # print(result.read().decode('utf-8'))
                # self.emit(SIGNAL('update server progress'), result.read())
                self.signal_server_log.emit(result.read().decode('utf-8'))
                self.sleep(self.probingRate)
            # except urllib.error.HTTPError as e:
            except:
                # File is not ready yet
                # self.signal_server_log.emit("(No log yet)")
                self.sleep(self.probingRate)
