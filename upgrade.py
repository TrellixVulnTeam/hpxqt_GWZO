import os
import shutil
import tarfile
import tempfile

import requests
from PyQt5.QtCore import QThread
from PyQt5.QtCore import pyqtSignal

from hpxqt import consts as hpxqt_consts
from hpxqt import utils as hpxqt_utils


class DownloadThread(QThread):
    signal_download_finished = pyqtSignal(int)

    def __init__(self, url, file_path):
        QThread.__init__(self)
        self.url = url
        self.file_path = file_path

    def __del__(self):
        self.wait()

    def run(self):
        response = requests.get(self.url, stream=True)
        if response.status_code != 200:
            return

        with open(self.file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):
                if not chunk:
                    continue
                f.write(chunk)
        self.signal_download_finished.emit(hpxqt_consts.FINISHED_DOWNLOAD)


class WindowUpdateMixIn(object):
    signal_upgrade_status_change = pyqtSignal(int)

    def __init__(self):
        _os = hpxqt_utils.get_os()

        self.app_dir = hpxqt_utils.get_app_dir()
        self.app_path = os.path.join(self.app_dir, hpxqt_consts.APP_NAME_MAP[_os])
        self.download_thread = None
        self.last_update = None

        self.download_dir = None
        self.download_file = None

        self.signal_upgrade_status_change.connect(self.upgrade_status_change)

        self._remove_old_executable()

    def start_upgrade(self):
        self.last_update = self.router.db_manager.last_update()

        self.download_dir = tempfile.TemporaryDirectory()
        self.download_file = os.path.join(self.download_dir.name, self.last_update.url.rsplit('/', maxsplit=1)[-1])

        if self.last_update.is_downloaded:
            self.signal_upgrade_status_change.emit(hpxqt_consts.START_INSTALL)
            return

        self.signal_upgrade_status_change.emit(hpxqt_consts.START_DOWNLOAD)
        self.download_thread = DownloadThread(self.last_update.url,
                                              self.download_file)
        self.download_thread.signal_download_finished.connect(
            self.upgrade_status_change)
        self.download_thread.start()

    def _rename_executable(self):
        os.rename(self.app_path, '%s.tmp' % self.app_path)

    def _remove_old_executable(self):
        tmp_app_path = '%s.tmp' % self.app_path
        if os.path.exists(tmp_app_path):
            os.remove(tmp_app_path)

    def upgrade_status_change(self, kind):
        if kind == hpxqt_consts.FINISHED_DOWNLOAD:
            self.router.db_manager.mark_downloaded(self.last_update.version)

        if kind in [hpxqt_consts.START_INSTALL, hpxqt_consts.FINISHED_DOWNLOAD]:
            self.process_installation()

    def process_linux(self):
        with tarfile.open(self.download_file) as tar:
            # specify path explicitly to extract files to download_dir
            tar.extractall(path=os.path.join(self.download_dir.name))
            # Get path to executable
            src_dir = os.path.join(self.download_dir.name, tar.getnames()[-1])
            self._rename_executable()
            shutil.move(src_dir, self.app_path)

    def process_osx(self):
        self._rename_executable()
        with hpxqt_utils.ZipFileWithPermissions(self.download_file) as zip:
            zip.extractall(path=self.app_dir)

    def process_windows(self):
        self._rename_executable()
        shutil.move(self.download_file, self.app_path)

    def process_installation(self):
        """
        Updates database and replaces a current process with
        a new process.
        """
        getattr(self, 'process_%s' % self.last_update.platform)()
        self.download_dir.cleanup()

        self.router.db_manager.remove_downloaded(self.last_update.version)
        self.router.db_manager.mark_installed(self.last_update.version)
        self.signal_upgrade_status_change.emit(hpxqt_consts.FINISHED_INSTALL)
