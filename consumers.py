import platform

from PyQt5.QtCore import pyqtSlot

from hpxclient.fetcher.central import consumers as fetcher_central_consumers
from hpxclient import consts as hpxclient_consts
from hpxclient.mng import consumers as mng_consumers
from hpxqt import __version__ as version
from hpxqt import consts as hpxqt_consts
from hpxqt import utils as hpxqt_utils


class Consumer(object):
    def __init__(self, login_window, system_tray, mng):
        self.login_window = login_window
        self.system_tray = system_tray
        self.mng = mng


class AuthResponseConsumer(Consumer):
    KIND = fetcher_central_consumers.AuthResponseConsumer.KIND

    def process(self, msg):
        error = msg[b"error"]

        if error:
            self.login_window.show()
            self.login_window.show_error(error_msg=error.decode())

            self.mng.stop_manager()
            self.mng.delete_credentials()
        else:
            self.mng.save_credentials()
            self.login_window.signal_minimize_tray.emit()


class InfoBalanceConsumer(Consumer):
    KIND = mng_consumers.InfoBalanceConsumer.KIND

    def process(self, msg):
        balance_amount = hpxqt_utils.bytes2str(msg[b"balance_amount"])
        self.system_tray.label_balance.setText("Balance: %s" % balance_amount)


class PongConsumer(Consumer):
    KIND = hpxclient_consts.PONG_KIND

    def process(self, msg):
        pass


class InfoVersionConsumer(Consumer):
    KIND = mng_consumers.InfoVersionConsumer.KIND

    def __init__(self, login_window, system_tray, mng):
        super().__init__(login_window, system_tray, mng)

        self._OS = hpxqt_utils.get_os()
        self._ARCH = hpxqt_consts.ARCH_MAP.get(platform.architecture()[0], '')

    def _save_new_version(self, binaries):
        for binary in binaries:
            b_platform = binary['platform'].lower()
            b_arch = binary['arch'].lower()

            if b_platform != self._OS:
                continue

            if b_platform != hpxqt_consts.MAC_OS and (self._ARCH not in b_arch):
                    continue
            return self.login_window.router.db_manager.add_update(binary['version'],
                                                            binary['file'],
                                                            self._OS)

    def process(self, msg):
        msg = hpxqt_utils.convert_bytes(msg)
        if version == msg['version']:
            return
        
        update_ver = self.login_window.router.db_manager.get_update(msg["version"])
        if not update_ver:
            update_ver = self._save_new_version(msg['binaries'])
            if not update_ver:
                # There was no update matching system specification
                return

        if update_ver.is_installed:
            return
        self.login_window.upgrade.setDisabled(False)


REGISTERED_CONSUMERS = [
    AuthResponseConsumer,
    InfoBalanceConsumer,
    InfoVersionConsumer,
    PongConsumer
]


@pyqtSlot(dict)
def process_message(msg):
    """ All messages sent to the manager are also processed by
    the ui interface.
    """

    consumer_cls = None
    consumer_kind = msg[b'kind'].decode()

    for _consumer_cls in REGISTERED_CONSUMERS:
        if consumer_kind == _consumer_cls.KIND:
            consumer_cls = _consumer_cls
            break

    if consumer_cls is None:
        print('Kind not recognized %s' % consumer_kind)
        return

    window = hpxqt_utils.get_login_window()
    system_tray = hpxqt_utils.get_system_tray()
    mng = hpxqt_utils.get_chainprox_manager()

    return consumer_cls(window, system_tray, mng).process(msg[b'data'])
