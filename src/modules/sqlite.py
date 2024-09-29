import sqlite3

from modules.logger import Logger

class SQLiteDB:
    def __init__(self, db_path, table_name='mac_addresses'):
        self.db_path = db_path
        self.table_name = table_name
        self.logger = Logger.get_logger('SMTP')
        self.init_db()

    def init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    id INTEGER PRIMARY KEY,
                    mac_address TEXT NOT NULL
                )
            ''')
            conn.commit()

    def insert_mac_address(self, mac_address):
        if self.is_known_mac(mac_address):
            return False

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(f'''
                    INSERT INTO {self.table_name} (mac_address)
                    VALUES (?)
                ''', (mac_address,))
                conn.commit()
            return True
        except sqlite3.Error as e:
            self.logger.error(f"An error occurred: {e}")
            return False

    def is_known_mac(self, mac_address):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(f'''
                    SELECT EXISTS(
                        SELECT 1 FROM {self.table_name}
                        WHERE mac_address = ?
                    )
                ''', (mac_address,))
                result = cursor.fetchone()[0] == 1
            return result
        except sqlite3.Error as e:
            self.logger.error(f"An error occurred: {e}")
            return False
