import sqlite3


class DbHandler:
    def __init__(self, database):
        self.connection = self.connect(database)
        self.cursor = self.connection.cursor()

    def connect(self, database):
        if not database.endswith('.db'):
            raise Exception('Invalid Database')
        return sqlite3.connect(database)

    def create_tables(self):
        """
        Create main bot tables.
        """
        self.cursor.execute('CREATE TABLE profile(user, badges, bio)')
        self.cursor.execute('CREATE TABLE ticket(opened_by, channel, is_open, open_date, close_date, category, guild_id)')

    def create_profile(self, user_id):
        """
        Creates a new profile record on database.
        """
        self.cursor.execute(f'''
            INSERT INTO profile VALUES
                ({user_id}, "", "")
        ''')
        self.connection.commit()

    def update_badge(self, user_id, badge):
        """
        Updates a profile record badge column content from a specific user
        """
        self.cursor.execute(f'''
            UPDATE profile set badges = "{badge}" WHERE user = {user_id}
        ''')
        self.connection.commit()

    def update_bio(self, user_id, bio):
        """
        Updates a profile record bio column content from a specific user
        """
        self.cursor.execute(f'''
            UPDATE profile set bio = "{bio}" WHERE user = {user_id}
        ''')
        self.connection.commit()

    def view_profile(self, user_id):
        result = self.cursor.execute(f'SELECT user, badges, bio FROM profile WHERE user = {user_id}')
        result = result.fetchall()
        if not result:
            return []
        return result[0]
