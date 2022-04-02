import asyncio

from PyQt5.QtCore import QThread, pyqtSignal

from hpxclient.mng import service as mng_service
from hpxqt import consumers as hpxqt_consumers


class WindowManagerMixIn(object):
    def start_manager(self, email, password):
        self.email = email
        self.password = password
        asyncio.ensure_future(mng_service.start_client(
                email=email,
                password=password,
                message_handler=hpxqt_consumers.process_message))

    def stop_manager(self):
        pass
