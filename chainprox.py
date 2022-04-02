import os
import sys
import urllib.parse
import asyncio
import signal
import quamash

import requests
from PyQt5 import QtGui, QtCore, QtWebChannel, QtWebEngineWidgets, QtWidgets
from PyQt5.QtWidgets import QApplication


from hpxclient import daemon as hpxclient_daemon
from hpxqt import consts as hpxqt_consts
from hpxqt import db as hpxqt_db
from hpxqt import mng as hpxqt_mng
from hpxqt import upgrade as hpxqt_upgrade
from hpxqt import utils as hpxqt_utils

# Required for QtGui.QPixmap to work
from hpxqt import hpximg


class Router(QtCore.QObject):
    init_close = QtCore.pyqtSignal()

    def __init__(self, window):
        super(Router, self).__init__()
        self.window = window

        self.channel = None

        self.init_close.connect(self.app_handler_close_connection)

        self.db_manager = hpxqt_db.DatabaseManager()
        self.db_manager.initialize()

    def app_handler_close_connection(self):
        if self.channel:
            self.channel.close_connections()
            
    @QtCore.pyqtSlot(str, str)
    def js_handler_login(self, email, password):
        """
        Method is called from js.
        """
        self.window.start_manager(email, password)

    @QtCore.pyqtSlot(str)
    def js_handler_reset_password(self, email):
        url = urllib.parse.urljoin(hpxqt_consts.URL_PREFIX,
                                   "api/account/password/reset/")
        requests.post(url, data=dict(email=email))

    @QtCore.pyqtSlot(str)
    def js_open_url(self, url):
        self.window.open_url(url)


class Window(hpxqt_mng.WindowManagerMixIn,
             hpxqt_upgrade.WindowUpdateMixIn,
             QtWebEngineWidgets.QWebEngineView):
    signal_minimize_tray = QtCore.pyqtSignal()

    def __init__(self):
        QtWebEngineWidgets.QWebEngineView.__init__(self)
        hpxqt_mng.WindowManagerMixIn.__init__(self)
        hpxqt_upgrade.WindowUpdateMixIn.__init__(self)

        # Connect to signals
        self.signal_minimize_tray.connect(self.action_minimize_tray)
        self.signal_upgrade_status_change.connect(self.upgrade_status_change_ui)

        # Initialize paths
        self.media = hpxqt_utils.get_media_dir_path()
        self.templates = hpxqt_utils.get_templates_dir_path()
        self.db_path = hpxqt_utils.get_db_file_path()

        # Initialize WebChannel
        self.channel = QtWebChannel.QWebChannel(self.page())
        self.router = Router(window=self)
        self.channel.registerObject("router", self.router)
        self.page().setWebChannel(self.channel)

        # Define window settings
        self.name = hpxqt_consts.APP_NAME
        self.setWindowTitle(hpxqt_consts.APP_TITLE)
        self.resize(400, 480)
        self.setWindowIcon(self._get_icon())

        self._create_tray_icon()
        self.trayIcon.show()

    def _get_icon(self):
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/images/icon.png"))
        return icon

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

    def close(self, *args):
        self.router.init_close.emit()
        self.stop_manager()
        QtWidgets.QApplication.instance().quit()
        
    def restart(self):
        self.close()
        hpxqt_utils.restart_program()

    def action_logout(self):
        self.router.init_close.emit()
        self.router.db_manager.delete_user()
        self.close()

    def action_minimize_tray(self):
        self.set_status_traymenu(is_disabled=False)
        self.hide()

    def load_login_page(self):
        url = QtCore.QUrl().fromLocalFile(os.path.join(self.templates,
                                                       "login.html"))
        self.load(url)

    def show_error(self, error_msg):
        self.page().runJavaScript("show_error('%s');" % error_msg)

    def open_url(self, url_path):
        url = urllib.parse.urljoin(hpxqt_consts.URL_PREFIX, url_path)
        if not QtGui.QDesktopServices.openUrl(QtCore.QUrl(url)):
            QtWidgets.QMessageBox.warning(self,
                                          'Open Url',
                                          'Could not open url')

    def open_help(self):
        self.open_url('dash/how-to-proxy/')

    def open_preferences(self):
        self.open_url('dash/proxy')

    def open_lost_password(self):
        self.open_url('dash/proxy')

    def open_create_account(self):
        self.open_url('dash/proxy')

    def set_status_traymenu(self, is_disabled):
        self.preference.setDisabled(is_disabled)
        self.logout.setDisabled(is_disabled)

    def get_latest_version(self):        
        self.upgrade.setDisabled(True)
        self.start_upgrade()

    def upgrade_status_change_ui(self, kind):
        if kind == hpxqt_consts.START_DOWNLOAD:
            self.upgrade.setText('Downloading...')
        elif kind == hpxqt_consts.START_INSTALL:
            self.upgrade.setText('Installing...')
        elif kind == hpxqt_consts.FINISHED_INSTALL:
            self.restart()

    def _create_tray_icon(self):
        """ Creates initial tray icon with the minimum options.
        """

        self.trayIconMenu = QtWidgets.QMenu()
        self.trayIcon = QtWidgets.QSystemTrayIcon(self)
        self.trayIcon.setIcon(self._get_icon())

        self.trayIcon.setContextMenu(self.trayIconMenu)
        self.label_balance = QtWidgets.QAction('Balance: unknown', self)
        self.label_balance.setDisabled(True)
        self.trayIconMenu.addAction(self.label_balance)
        self.trayIconMenu.addSeparator()

        self.upgrade = QtWidgets.QAction('Upgrade',
                                         self,
                                         triggered=self.get_latest_version)
        self.upgrade.setDisabled(True)
        self.trayIconMenu.addAction(self.upgrade)


        self.trayIconMenu.addSeparator()

        self.preference = QtWidgets.QAction('Preferences', self,
                                            triggered=self.open_preferences)
        self.trayIconMenu.addAction(self.preference)

        self.help = QtWidgets.QAction('Help', self, triggered=self.open_help)
        self.trayIconMenu.addAction(self.help)
        self.trayIconMenu.addSeparator()

        self.logout = QtWidgets.QAction('Logout',
                                        self,
                                        triggered=self.action_logout)
        self.trayIconMenu.addAction(self.logout)

        self.quitAction = QtWidgets.QAction("&Quit",
                                            self, 
                                            triggered=self.close)
        self.trayIconMenu.addAction(self.quitAction)

        self.set_status_traymenu(is_disabled=True)

    def shutdown(self, signal=None):
        try:
            self.close()
        except asyncio.InvalidStateError:
            raise SystemExit


class TestSystemTray(QtWidgets.QSystemTrayIcon):
    def __init__(self, icon, window, parent=None):
        QtWidgets.QSystemTrayIcon.__init__(self, icon, parent)
        self.window = window
        self.trayIconMenu = QtWidgets.QMenu()
        self.setContextMenu(self.trayIconMenu)


        self.logout = QtWidgets.QAction('Logout',
                                        self,
                                        triggered=self.action_logout)
        self.trayIconMenu.addAction(self.logout)

    def action_logout(self):
        self.window.router.init_close.emit()
        self.window.router.db_manager.delete_user()
        self.window.close()


async def process_events(qapp):
    while True:
        await asyncio.sleep(0)
        qapp.processEvents()
        print("processing events")


def init_app():
    hpxclient_daemon.load_config()

    app = QtWidgets.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    if not QtWidgets.QSystemTrayIcon.isSystemTrayAvailable():
        QtWidgets.QMessageBox.critical(
            None, "Systray", "I couldn't detect any system tray on this system.")
        sys.exit(1)

    window = Window()
    app._chainprox_main_window = window

    event_loop = quamash.QEventLoop(app)
    asyncio.set_event_loop(event_loop)
    asyncio.events._set_running_loop(event_loop)

    user = window.router.db_manager.last_user()

    with event_loop:
        if user:
            window.start_manager(user.email, user.password)
        else:
            window.load_login_page()
            window.show()

        event_loop.run_forever()

if __name__ == '__main__':
    app = init_app()
