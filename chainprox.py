import os
import sys
import urllib.parse
import asyncio
import functools

import requests
import qasync

from qasync import asyncSlot
from PyQt5 import QtGui, QtCore, QtWebChannel, QtWebEngineWidgets, QtWidgets
from PyQt5.QtWidgets import QApplication

from hpxclient import daemon as hpxclient_daemon
from hpxclient import settings
from hpxqt import consts as hpxqt_consts
from hpxqt import db as hpxqt_db
from hpxqt import mng as hpxqt_mng
from hpxqt import utils as hpxqt_utils

# Required for QtGui.QPixmap to work
from hpxqt import hpximg


class ChainproxManager(QtCore.QObject):
    def __init__(self):
        super().__init__()

        self.db_manager = hpxqt_db.DatabaseManager()
        self.db_manager.initialize()

        self._login = None
        self._password = None

    async def start_manager(self, login, password):
        self._login = login
        self._password = password

        await hpxqt_mng.start_manager(login, password, proxy_enabled=settings.PROXY_SSL_ENABLED)

    def stop_manager(self):
        hpxqt_mng.stop_manager()

    def close(self, *args):
        self.stop_manager()
        QtWidgets.QApplication.instance().quit()

    def save_credentials(self):
        if not self._login or not self._password:
            raise Exception("Password or Login not set.")

        self.db_manager.add_user(
            email=self._login,
            password=self._password)

    def delete_credentials(self):
        self.db_manager.delete_user()


class QObjectMixIn(object):
    @staticmethod
    def get_media_path():
        return hpxqt_utils.get_media_dir_path()

    @staticmethod
    def get_templates_path():
        return hpxqt_utils.get_templates_dir_path()

    @staticmethod
    def get_db_path():
        return hpxqt_utils.get_db_file_path()

    @staticmethod
    def open_url(qobject, url_path):
        url = urllib.parse.urljoin(hpxqt_consts.URL_PREFIX, url_path)
        if not QtGui.QDesktopServices.openUrl(QtCore.QUrl(url)):
            QtWidgets.QMessageBox.warning(qobject,
                                          'Open Url',
                                          'Could not open url')

    @staticmethod
    def get_icon():
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/images/icon.png"))
        return icon


class Router(QObjectMixIn, QtCore.QObject):
    def __init__(self, window):
        super().__init__()
        self.window = window

    @asyncSlot(str, str)
    async def js_handler_login(self, email, password):
        """
        Method is called from js.
        """
        await self.window.chainprox_manager.start_manager(email, password)

    @QtCore.pyqtSlot(str)
    def js_handler_reset_password(self, email):
        url = urllib.parse.urljoin(hpxqt_consts.URL_PREFIX,
                                   "api/account/password/reset/")
        requests.post(url, data=dict(email=email))

    @QtCore.pyqtSlot(str)
    def js_open_url(self, url):
        self.open_url(self, url)


class WebWindowView(QObjectMixIn, QtWebEngineWidgets.QWebEngineView):
    signal_minimize_tray = QtCore.pyqtSignal()

    def __init__(self, chainprox_manager):
        QtWebEngineWidgets.QWebEngineView.__init__(self)

        self.chainprox_manager = chainprox_manager

        # Initialize WebChannel
        self.channel = QtWebChannel.QWebChannel(self.page())
        self.router = Router(window=self)
        self.channel.registerObject("router", self.router)
        self.page().setWebChannel(self.channel)

        # Define window settings
        self.name = hpxqt_consts.APP_NAME
        self.setWindowTitle(hpxqt_consts.APP_TITLE)
        self.resize(400, 480)
        self.setWindowIcon(self.get_icon())

        # Connect to signals
        self.signal_minimize_tray.connect(self.action_minimize_tray)
        self.load_login_page()

    def action_minimize_tray(self):
        hpxqt_utils.get_system_tray().set_status_traymenu(is_disabled=False)
        self.hide()

    def show_error(self, error_msg):
        self.page().runJavaScript("window.show_error('%s');" % error_msg)

    def closeEvent(self, event):
        close = QtWidgets.QMessageBox()
        close.setText("Do you want to exit?")
        close.setStandardButtons(
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        close = close.exec()

        if close == QtWidgets.QMessageBox.Yes:
            event.accept()
            QtWidgets.QApplication.instance().quit()
        else:
            event.ignore()

    def load_login_page(self):
        url = QtCore.QUrl().fromLocalFile(os.path.join(self.get_templates_path(),
                                                       "login.html"))
        self.load(url)


class SystemTrayIcon(QObjectMixIn, QtCore.QObject):
    def __init__(self, chainprox_manager):
        super().__init__()

        self.chainprox_manager = chainprox_manager

        # System try icon
        self._create_tray_icon()
        self.trayIcon.show()

    def open_preferences(self):
        self.open_url(self, 'dash/proxy')

    def open_help(self):
        self.open_url(self, 'dash/how-to-proxy/')

    def set_status_traymenu(self, is_disabled):
        self.preference.setDisabled(is_disabled)
        self.logout.setDisabled(is_disabled)

    def action_logout(self):
        self.chainprox_manager.delete_credentials()
        self.chainprox_manager.close()

    def _create_tray_icon(self):
        """ Creates initial tray icon with the minimum options.
        """

        self.trayIconMenu = QtWidgets.QMenu()
        self.trayIcon = QtWidgets.QSystemTrayIcon()
        self.trayIcon.setIcon(self.get_icon())

        self.trayIcon.setContextMenu(self.trayIconMenu)
        self.label_balance = QtWidgets.QAction('Balance: unknown', self)
        self.label_balance.setDisabled(True)
        self.trayIconMenu.addAction(self.label_balance)
        self.trayIconMenu.addSeparator()

        self.preference = QtWidgets.QAction('Preferences', self,
                                            triggered=self.open_preferences)
        self.trayIconMenu.addAction(self.preference)

        self.help = QtWidgets.QAction('Help', self, triggered=self.open_help)
        self.trayIconMenu.addAction(self.help)
        self.trayIconMenu.addSeparator()

        self.logout = QtWidgets.QAction('Logout and Quit',
                                        self,
                                        triggered=self.action_logout)
        self.trayIconMenu.addAction(self.logout)

        self.quitAction = QtWidgets.QAction("&Quit",
                                            self,
                                            triggered=self.chainprox_manager.close)
        self.trayIconMenu.addAction(self.quitAction)

        self.set_status_traymenu(is_disabled=True)


async def main():
    def close_future(future, loop):
        loop.call_later(10, future.cancel)
        future.cancel()

    loop = asyncio.get_event_loop()
    future = asyncio.Future()

    app = QApplication.instance()
    app.setQuitOnLastWindowClosed(False)

    chainprox_manager = ChainproxManager()

    if not QtWidgets.QSystemTrayIcon.isSystemTrayAvailable():
        QtWidgets.QMessageBox.critical(
            None, "Systray", "I couldn't detect any system tray on this system.")
        sys.exit(1)

    if hasattr(app, "aboutToQuit"):
        getattr(app, "aboutToQuit").connect(
            functools.partial(close_future, future, loop)
        )

    tray = SystemTrayIcon(chainprox_manager)
    window = WebWindowView(chainprox_manager)
    user = chainprox_manager.db_manager.last_user()

    if user:
        await chainprox_manager.start_manager(user.email, user.password)
    else:
        window.show()

    app._chainprox_manager = chainprox_manager
    app._chainprox_login_window = window
    app._chainprox_system_tray = tray

    await future
    return True


if __name__ == "__main__":
    hpxclient_daemon.load_config()

    try:
        qasync.run(main())
    except asyncio.exceptions.CancelledError:
        sys.exit(0)
