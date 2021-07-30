import sqlite3
import discord
import datetime
import semantic_version

class InvalidDatabase(Exception):
    """Raised when the database is not the correct version."""
    pass

class Database:
    def __init__(self):
        self.db = sqlite3.connect('serverData.db', detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
        self.db.row_factory = sqlite3.Row
        self.init_db()

    def init_db(self):
        with self.db:
            self.db.execute("""CREATE TABLE IF NOT EXISTS _database( version TEXT NOT NULL DEFAULT "2.1.0")""")
            self.db.execute("""CREATE TABLE IF NOT EXISTS servers( id INTEGER UNIQUE NOT NULL, name TEXT, topicCategory INTEGER, quotesChannel INTEGER, startingRole INTEGER, archiveCategory INTEGER)""")
            self.db.execute("""CREATE TABLE IF NOT EXISTS topicChannels( guildID INTEGER NOT NULL, channelID INTEGER UNIQUE NOT NULL, name TEXT, description TEXT, creatorID INTEGER NOT NULL, tier INTEGER NOT NULL DEFAULT 1, pendingRemovalDate timestamp, pinned INTEGER DEFAULT 0, archive INTEGER DEFAULT 0)""")
            self.db.execute("""CREATE TABLE IF NOT EXISTS banned(id INTEGER NOT NULL, name TEXT)""")
            self.db.execute("""CREATE TABLE IF NOT EXISTS quotes(id INTEGER PRIMARY KEY NOT NULL, author INTEGER, content TEXT, image TEXT, jump TEXT, speakers TEXT)""")
            self.db.execute("""CREATE TABLE IF NOT EXISTS voice(id INTEGER PRIMARY KEY NOT NULL, creator INTEGER, voiceID INTEGER NOT NULL UNIQUE, textID INTEGER NOT NULL UNIQUE, whitelist INTEGER DEFAULT 0, people TEXT NOT NULL, deleteTime timestamp)""")
            self.db.execute("""CREATE TABLE IF NOT EXISTS lastVoice(creator INTEGER NOT NULL UNIQUE, name TEXT NOT NULL, whitelist INTEGER DEFAULT 0, people TEXT NOT NULL)""")
            self.db.execute("""CREATE TABLE IF NOT EXISTS theme(guildID INTEGER NOT NULL UNIQUE, themeName TEXT DEFAULT '', guildName TEXT NOT NULL, ranks TEXT DEFAULT '')""")
            self.db.execute("""CREATE TABLE IF NOT EXISTS hero(name TEXT NOT NULL DEFAULT 'Unnamed', guildID INTEGER NOT NULL, heroID INTEGER NOT NULL, stars INTEGER NOT NULL DEFAULT -1, active INTEGER NOT NULL DEFAULT 1, total INTEGER NOT NULL DEFAULT 0)""")
            self.db.execute("""CREATE TABLE IF NOT EXISTS deck(guildID INTEGER NOT NULL, userID INTEGER NOT NULL, cards TEXT DEFAULT '', totalPoints INTEGER DEFAULT 0, spentPoints INTEGER DEFAULT 0)""")

        self.update_db()

    def update_db(self):
        c = self.db.execute("""SELECT * FROM _database""")
        data = c.fetchone()
        if not data:
            with self.db:
                self.db.execute("""INSERT INTO _database DEFAULT VALUES""")
            c = self.db.execute("""SELECT * FROM _database""")
            data = c.fetchone()
        self.version = semantic_version.Version(data['version'])
        needed_version = semantic_version.SimpleSpec('>=2.1.0')

        if not needed_version.match(self.version):
            if self.version < semantic_version.Version('1.1.0'):
                self.version = semantic_version.Version('1.1.0')
                with self.db:
                    self.db.execute(
                        'ALTER TABLE topicChannels ADD COLUMN archive INTEGER DEFAULT 0'
                    )

            if self.version < semantic_version.Version('2.0.0'):
                self.version = semantic_version.Version('2.0.0')
                with self.db:
                    self.db.execute(
                        'ALTER TABLE topicChannels RENAME TO topicChannelsOld'
                    )
                    self.db.execute(
                        'CREATE TABLE topicChannels (guildID INTEGER NOT NULL, channelID INTEGER UNIQUE NOT NULL, name TEXT, description TEXT, creatorID INTEGER NOT NULL, tier INTEGER NOT NULL DEFAULT 1, pendingRemovalDate timestamp, pinned INTEGER DEFAULT 0, archive INTEGER DEFAULT 0)'
                    )
                    self.db.execute(
                        'INSERT INTO topicChannels (guildID, channelID, name, creatorID, tier, pendingRemovalDate, pinned, archive) '
                        'SELECT serverID, id, name, createdBy, tier, pendingDeletionDate, pinned, archive FROM topicChannelsOld'
                    )
                    self.db.execute(
                        'DROP TABLE topicChannelsOld'
                    )

            if self.version < semantic_version.Version('2.1.0'):
                self.version = semantic_version.Version('2.1.0')
                with self.db:
                    self.db.execute(
                        'ALTER TABLE servers ADD COLUMN archiveCategory INTEGER'
                    )

            with self.db:
                self.db.execute(
                    'UPDATE _database SET version = ?',
                    (str(self.version),)
                )


    def get_server(self, server: discord.Guild):
        if isinstance(server, int):
            key = server
        else:
            key = server.id
        c = self.db.execute(
            """SELECT * FROM servers WHERE id = ?""",
            (key,)
        )
        fetch = c.fetchone()
        return fetch

    def add_server(self, server: discord.Guild):
        key = server.id
        name = server.name
        with self.db:
            self.db.execute(
                """INSERT INTO servers(id, name) VALUES(?, ?)""",
                (key, name)
            )

    def check_server(self, server: discord.Guild):
        fetch = self.get_server(server)
        if not fetch:
            self.add_server(server)
            return None
        else:
            return fetch

    def update_server(self, server: discord.Guild, category_id, quotes_id, archive_id):
        with self.db:
            self.db.execute(
                """UPDATE servers SET name = ?, topicCategory = ?, quotesChannel = ?, archiveCategory = ? WHERE id = ?""",
                (server.name, category_id, quotes_id, archive_id, server.id)
            )

    def add_topic(self, guild_id: int, channel_id: int, user_id: int):
        with self.db:
            self.db.execute(
                """INSERT INTO topicChannels(guildID, channelID, creatorID) VALUES(?, ?, ?)""",
                (guild_id, channel_id, user_id)
            )

    def set_topic(self, channel_id, guild_id, **options):
        sqlite_query = 'UPDATE topicChannels SET'
        strings = []
        values = []
        if len(options) < 1:
            raise AttributeError('at least one option required')
        for key, value in options.items():
            attribute_string = f' {key} = ?'
            values.append(value)
            strings.append(attribute_string)
        sqlite_query += ','.join(strings)
        if guild_id:
            sqlite_query += ' WHERE channelID = ? AND guildID = ?'
            values.append(channel_id)
            values.append(guild_id)
        with self.db:
            self.db.execute(
                sqlite_query,
                tuple(values)
            )

    def get_topic(self, **options):
        sqlite_query = 'SELECT * FROM topicChannels'
        values = []
        if len(options) > 0:
            sqlite_query += ' WHERE'
            key_list = []
            for key, value in options.items():
                key_list.append(f' {key} = ?')
                values.append(value)
            sqlite_query += 'AND'.join(key_list)

        c = self.db.execute(
            sqlite_query,
            tuple(values)
        )
        return c.fetchall()

    def delete_topic(self, channel_id: int):
        with self.db:
            self.db.execute(
                """DELETE FROM topicChannels WHERE channelID = ?""",
                (channel_id,)
            )

    def is_not_banned(self, user: discord.Member):
        c = self.db.execute(
            """SELECT * FROM banned WHERE id = ?""",
            (user.id,)
        )
        if c.fetchone():
            return False
        else:
            return True

    def add_ban(self, user: discord.Member):
        with self.db:
            self.db.execute(
                """INSERT INTO banned(id, name) VALUES(?, ?)""",
                (user.id, str(user))
            )

    def del_ban(self, user: discord.Member):
        with self.db:
            self.db.execute(
                """DELETE FROM banned WHERE id = ?""",
                (user.id,)
            )

    def add_quote(self, author: discord.Member, content=None, image=None, jump=None, speakers=None):
        with self.db:
            cursor = self.db.cursor()
            cursor.execute(
                """INSERT INTO quotes(author, content, image, jump, speakers) VALUES(?, ?, ?, ?, ?)""",
                (author.id, content, image, jump, speakers)
            )
            lastrowid = cursor.lastrowid
            cursor.close()
        return lastrowid

    def del_quote(self, id):
        with self.db:
            self.db.execute(
                """DELETE FROM quotes WHERE id = ?""",
                (id,)
            )

    def update_quote(self, id, author: discord.Member, content=None, image=None, jump=None, speakers=None):
        with self.db:
            self.db.execute(
                """UPDATE quotes SET author = ?, content = ?, image = ?, jump = ?, speakers = ? WHERE id = ?""",
                (author.id, content, image, jump, speakers, id)
            )

    def get_quote(self, id=None, author=None, speaker=None, jump=None):
        if id:
            c = self.db.execute(
                """SELECT * FROM quotes WHERE id = ?""",
                (id,)
            )
        elif author:
            c = self.db.execute(
                """SELECT * FROM quotes WHERE author = ?""",
                (author.id,)
            )
        elif speaker:
            c = self.db.execute(
                """SELECT * FROM quotes WHERE speakers = ?""",
                (speaker.id,)
            )
        elif jump:
            c = self.db.execute(
                """SELECT * FROM quotes WHERE jump = ?""",
                (jump,)
            )
        else:
            c = self.db.execute(
                """SELECT * FROM quotes"""
            )
        fetch = c.fetchall()
        return fetch

    def add_voice(self, creator_id: int, voice_id: int, text_id: int, whitelist: bool, people: list, delete: datetime.datetime):
        with self.db:
            self.db.execute(
                """INSERT INTO voice(creator, voiceID, textID, whitelist, people, deleteTime) VALUES(?, ?, ?, ?, ?, ?)""",
                (creator_id, voice_id, text_id, int(whitelist), ','.join(str(x) for x in people), delete)
            )
    
    def get_voice(self, **options):
        sqlite_query = 'SELECT * FROM voice'
        values = []
        if len(options) > 0:
            sqlite_query += ' WHERE'
            for key, value in options.items():
                sqlite_query += f' {key} = ?'
                values.append(value)

        c = self.db.execute(
            sqlite_query,
            tuple(values)
        )
        return c.fetchall()

    def delete_voice(self, voice_id):
        with self.db:
            self.db.execute(
                """DELETE FROM voice WHERE voiceID = ?""",
                (voice_id,)
            )

    def add_last(self, creator_id):
        with self.db:
            self.db.execute(
                """INSERT INTO lastVoice(creator, name, people) VALUES(?, 'unset', '')""",
                (creator_id,)
            )

    def set_last(self, creator_id, name, whitelist, people):
        with self.db:
            self.db.execute(
                """UPDATE lastVoice SET name = ?, whitelist = ?, people = ? WHERE creator = ?""",
                (name, whitelist, ','.join(str(x) for x in people), creator_id)
            )

    def get_last(self, creator_id):
        c = self.db.execute(
            """SELECT * FROM lastVoice WHERE creator = ?""",
            (creator_id,)
        )
        return c.fetchone()

    def add_theme(self, guild_id, guild_name):
        with self.db:
            self.db.execute(
                """INSERT INTO theme(guildID, guildName) VALUES(?, ?)""",
                (guild_id, guild_name)
            )

    def set_theme(self, guild_id, **options):
        sqlite_query = 'UPDATE theme SET'
        strings = []
        values = []
        if len(options) < 1:
            raise AttributeError('at least one option required')
        else:
            for key, value in options.items():
                attribute_string = f' {key} = ?'
                values.append(value)
                strings.append(attribute_string)
        sqlite_query += ','.join(strings)
        sqlite_query += ' WHERE guildID = ?'
        values.append(guild_id)
        with self.db:
            self.db.execute(
                sqlite_query,
                tuple(values)
            )

    def get_theme(self, **options):
        sqlite_query = 'SELECT * FROM theme'
        values = []
        if len(options) > 0:
            sqlite_query += ' WHERE'
            key_list = []
            for key, value in options.items():
                key_list.append(f' {key} = ?')
                values.append(value)
            sqlite_query += 'AND'.join(key_list)

        c = self.db.execute(
            sqlite_query,
            tuple(values)
        )
        return c.fetchall()

    def add_hero(self, guild_id, hero_id):
        with self.db:
            self.db.execute(
                """INSERT INTO hero(guildID, heroID) VALUES(?, ?)""",
                (guild_id, hero_id)
            )

    def set_hero(self, guild_id, hero_id, **options):
        sqlite_query = 'UPDATE hero SET'
        strings = []
        values = []
        if len(options) < 1:
            raise AttributeError('at least one option required')
        for key, value in options.items():
            attribute_string = f' {key} = ?'
            values.append(value)
            strings.append(attribute_string)
        sqlite_query += ','.join(strings)
        if guild_id:
            sqlite_query += ' WHERE guildID = ? AND heroID = ?'
            values.append(guild_id)
            values.append(hero_id)
        with self.db:
            self.db.execute(
                sqlite_query,
                tuple(values)
            )

    def get_hero(self, **options):
        sqlite_query = 'SELECT * FROM hero'
        values = []
        if len(options) > 0:
            sqlite_query += ' WHERE'
            key_list = []
            for key, value in options.items():
                key_list.append(f' {key} = ?')
                values.append(value)
            sqlite_query += 'AND'.join(key_list)

        c = self.db.execute(
            sqlite_query,
            tuple(values)
        )
        return c.fetchall()

    def add_total_hero(self, guild_id, hero_id, points: int):
        sqlite_query = 'UPDATE hero SET total = total + ? WHERE guildID = ? AND heroID = ?'
        with self.db:
            self.db.execute(
                sqlite_query,
                (points, guild_id, hero_id)
            )

    def add_deck(self, guild_id, user_id):
        with self.db:
            self.db.execute(
                'INSERT INTO deck(guildID, userID) VALUES(?, ?)',
                (guild_id, user_id)
            )

    def set_deck(self, guild_id, user_id, **options):
        sqlite_query = 'UPDATE deck SET'
        strings = []
        values = []
        if len(options) < 1:
            raise AttributeError('at least one option required')
        for key, value in options.items():
            attribute_string = f' {key} = ?'
            values.append(value)
            strings.append(attribute_string)
        sqlite_query += ','.join(strings)
        sqlite_query += ' WHERE guildID = ? AND userID = ?'
        values.append(guild_id)
        values.append(user_id)
        with self.db:
            self.db.execute(
                sqlite_query,
                tuple(values)
            )

    def get_deck(self, **options):
        sqlite_query = 'SELECT * FROM deck'
        values = []
        if len(options) > 0:
            sqlite_query += ' WHERE'
            key_list = []
            for key, value in options.items():
                key_list.append(f' {key} = ?')
                values.append(value)
            sqlite_query += 'AND'.join(key_list)

        c = self.db.execute(
            sqlite_query,
            tuple(values)
        )
        return c.fetchall()


db = Database()