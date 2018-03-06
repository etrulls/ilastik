from PyQt5.QtCore import QThread, pyqtSignal
import urllib
import urllib.request
import ssl


class ServerUsageProber(QThread):
    """
    Probe server during processing to get available resources.
    """
    signal_server_usage = pyqtSignal(str)

    def __init__(self, creds, probingRate):
        QThread.__init__(self)
        self.creds = creds
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
            request = urllib.request.Request('{}:{}/api/getUsage'.format(server, port))
            request.add_header('username', username)
            request.add_header('password', password)
            context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
            try:
                result = urllib.request.urlopen(request, context=context)
                self.signal_server_usage.emit(result.read().decode('utf-8'))
                self.sleep(self.probingRate)
            except:
                # File is not ready yet
                # self.signal_server_usage.emit("(No log yet)")
                self.sleep(self.probingRate)
