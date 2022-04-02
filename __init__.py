__version__ = '1.0.1'

import logging.config

from pony.orm.dbproviders import sqlite  # it is needed to pyinstaller

from hpxqt import utils


logging.config.dictConfig(utils.get_logging_config())