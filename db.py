import os
from datetime import datetime

from pony import orm as pony_orm

from hpxqt import utils as hpxqt_utils


DB = pony_orm.Database()


class User(DB.Entity):
    email = pony_orm.Required(str)
    password = pony_orm.Required(str)


class Upgrade(DB.Entity):
    version = pony_orm.Required(str, unique=True)
    url = pony_orm.Required(str)
    platform = pony_orm.Required(str)
    date = pony_orm.Required(datetime, default=datetime.now)
    is_installed = pony_orm.Required(bool, default=False)
    is_downloaded = pony_orm.Required(bool, default=False)


class DatabaseManager(object):
    def initialize(self):
        DB.bind(provider='sqlite',
                filename=hpxqt_utils.get_db_file_path(),
                create_db=not os.path.exists(hpxqt_utils.get_db_file_path()))

        DB.generate_mapping(create_tables=True)

    @pony_orm.db_session
    def add_user(self, email, password):
        if self.get_user(email):
            return
        User(email=email, password=password)

    @pony_orm.db_session
    def add_update(self, version, url, platform, added=None, installed=False):
        data = dict(
            version=version, 
            url=url, 
            platform=platform, 
            is_installed=installed)
        
        if added is not None:
            data['date'] = added
        u = Upgrade(**data)
        return u

    @pony_orm.db_session
    def set_last_update_installed(self):
        update = pony_orm.select(u for u in Upgrade if not u.is_installed)\
                        .order_by(self.modelUpdate.date).first()
        update.is_installed = True

    @pony_orm.db_session
    def delete_user(self):
        pony_orm.delete(u for u in User)

    @pony_orm.db_session
    def delete_update(self, version):
        pony_orm.delete(u for u in Upgrade if u.version == version)

    @pony_orm.db_session
    def last_update(self):
        return pony_orm.select(u for u in Upgrade).order_by(Upgrade.date).first()

    @pony_orm.db_session
    def last_user(self):
        return pony_orm.select(u for u in User).order_by(User.id).first()

    @pony_orm.db_session
    def get_user(self, email):
        return pony_orm.select(u for u in User if u.email == email).first()

    @pony_orm.db_session
    def get_update(self, version):
        return pony_orm.select(u for u in Upgrade if u.version == version).first()

    @pony_orm.db_session
    def mark_downloaded(self, version):
        u = self.get_update(version)
        u.is_downloaded = True

    @pony_orm.db_session
    def remove_downloaded(self, version):
        u = self.get_update(version)
        u.is_downloaded = False
        
    @pony_orm.db_session
    def mark_installed(self, version):
        u = self.get_update(version)
        u.is_installed = True
