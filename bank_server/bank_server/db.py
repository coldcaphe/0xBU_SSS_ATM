""" DB
This module implements an interface to the bank_server database.
It uses a mutex because both the bank_interface and admin_interface
need access to database. (sqlite3 does not gurantee concurrent operations)"""

import sqlite3
import os

class DB(object):
    """Implements a Database interface for the bank server and admin interface"""
    def __init__(self, db_mutex=None, db_init=None, db_path=None):
        super(DB, self).__init__()
        self.db_conn = sqlite3.connect(os.getcwd() + db_path)
        self.db_mutex = db_mutex
        self.cur = self.db_conn.cursor()
        if db_init and not os.path.isfile(os.getcwd() + db_path):
            self.init_db(os.getcwd() + db_init)

    def close(self):
        """close the database connection"""
        self.db_conn.commit()
        self.db_conn.close()

    def init_db(self, filepath):
        """initialize database with file at filepath"""
        with open(filepath, 'r') as file_handle:
            cmds = file_handle.read().replace('\n', '')
        self.cur.executescript(cmds)
        self.db_conn.commit()

    def lock_db(func):
        """function wrapper for functions that require db access"""
        def func_wrap(self, *args):
            """acquire and release dbMuted if available"""
            if self.db_mutex:
                self.db_mutex.acquire()
            result = func(self, *args)
            self.db_conn.commit()
            if self.db_mutex:
                self.db_mutex.release()
            return result
        return func_wrap

    def modify(self, statement, param):
        """reduce duplicate code"""
        try:
            self.cur.execute(statement, param)
            return True
        except sqlite3.IntegrityError:
            return False

    ############################
    # BANK INTERFACE FUNCTIONS #
    ############################

    @lock_db
    def user_exists(self, name):
        """
        Returns true iff the name exists in the db
        """
        self.cur.execute('SELECT EXISTS(SELECT 1 FROM cards WHERE account_name = (?) LIMIT 1);', (name,))
        
        result = self.cur.fetchone()
        if result[0] == 0:
            return False

        return True

    @lock_db
    def card_exists(self, card_id):
        """
        Returns true iff the card_id exists in the db
        """
        self.cur.execute('SELECT EXISTS(SELECT 1 FROM cards WHERE card_id = (?) LIMIT 1);', (card_id,))
        
        result = self.cur.fetchone()
        if result[0] == 0:
            return False

        return True

    @lock_db
    def check_expired_and_update_nonce(self, card_id, nonce):
        (_, timestamp, used) = get_nonce_data(card_id)

        #if card has unused nonce that hasn't expired, return error
        if not used and self.check_timestamp_valid(timestamp):
            return False

        return self.modify("UPDATE cards SET nonce=(?), used=0, timestamp=DATETIME('now','localtime') WHERE card_id=(?);", 
                        (sqlite3.Binary(nonce), card_id,))

    @lock_db
    def update_pk(self, card_id, new_pk):
        return self.modify("UPDATE cards SET pk=(?) WHERE card_id=(?);", 
            (sqlite3.Binary(new_pk), card_id,))

    @lock_db
    def get_hsm_key(self, hsm_id):
        self.cur.execute('SELECT k_hsm FROM atms WHERE hsm_id = (?);', (hsm_id,))
        
        result = self.cur.fetchone()
        if result == None:
            return None

        return result[0]

    @lock_db
    def do_withdrawal(self, card_id, hsm_id, amount):
        self.cur.execute('SELECT balance FROM cards WHERE card_id = (?);', (card_id,))
        balance = self.cur.fetchone()
        if balance == None:
            return False
        balance = balance[0]

        self.cur.execute('SELECT num_bills FROM atms WHERE hsm_id = (?);', (hsm_id,))
        hsm_balance = self.cur.fetchone()
        if hsm_balance == None:
            return False
        hsm_balance = hsm_balance[0]

        if amount > balance:
            return False

        if amount > hsm_balance:
            return False

        balance -= amount
        hsm_balance -= amount

        if not self.modify("UPDATE cards SET balance=(?) WHERE card_id=(?)", (balance, card_id,)):
            return False

        if not self.modify("UPDATE atms SET num_bills=(?) WHERE hsm_id=(?)", (hsm_balance, hsm_id,)):
            return False

        return True

    @lock_db
    def read_set_nonce_used(self, card_id, nonce):
        (db_nonce, timestamp, used) = get_nonce_data(card_id)

        if used:
            return False

        if db_nonce != nonce:
            return False

        if not check_timestamp_valid(timestamp):
            return False

        return self.modify("UPDATE cards SET nonce=(?), used=0, timestamp=DATETIME('now','localtime') WHERE card_id=(?);", 
                        (sqlite3.Binary(nonce), card_id,))

    @lock_db
    def get_pk(self, card_id):
        self.cur.execute('SELECT pk FROM cards WHERE card_id = (?);', (card_id,))
        
        result = self.cur.fetchone()
        if result == None:
            return None

        return result[0]

    @lock_db
    def set_first_pk(card_id, pk):
        #check that card exists
        self.cur.execute('SELECT EXISTS(SELECT 1 FROM cards WHERE card_id = (?) LIMIT 1);', (card_id,))
        
        result = self.cur.fetchone()
        if result[0] == 0:
            return False

        #check that pk is null
        self.cur.execute('SELECT pk FROM cards WHERE card_id = (?);', (card_id,))
        
        result = self.cur.fetchone()
        if result[0] is not None:
            return False

        return self.modify("UPDATE cards SET pk=(?) WHERE card_id=(?);", 
            (sqlite3.Binary(new_pk), card_id,))



##########

    def get_nonce_data(card_id):
        self.cur.execute('SELECT nonce, timestamp, used FROM cards WHERE card_id = (?);', (card_id,))
        (nonce, timestamp, used) = self.cur.fetchone()

        if nonce == None or timestamp == None or timestamp == None or used == None:
            return None

        return (nonce, timestamp, used)

###############################################################
    #############################
    # ADMIN INTERFACE FUNCTIONS #
    #############################

    @lock_db
    def admin_create_account(self, account_name, card_id, amount):
        """create account with account_name, card_id, and amount

        Returns:
            (bool): Returns True on Success. False otherwise.
        """

        return self.modify('INSERT INTO cards(account_name, card_id, balance) \
                            values (?, ?, ?);', (account_name, card_id, amount,))

    @lock_db
    def admin_create_atm(self, hsm_id, hsm_key):
        """create atm

        Returns:
            (bool): True on success, false otherwise
        """

        return self.modify('INSERT INTO atms(hsm_id, hsm_key, num_bills) values (?,?,?);', (hsm_id, sqlite3.Binary(hsm_key), 128, ))

    @lock_db
    def admin_get_balance(self, account_name):
        """get balance of account: card_id

        Returns:
            (string or None): Returns balance on Success. None otherwise.
        """
        self.cur.execute("SELECT balance FROM cards WHERE account_name = (?);", (account_name,))
        result = self.cur.fetchone()
        if result is None:
            return None
        return result[0]

    @lock_db
    def admin_set_balance(self, account_name, balance):
        """set balance of account: card_id

        Returns:
            (bool): Returns True on Success. False otherwise.
        """
        self.cur.execute('SELECT EXISTS(SELECT 1 FROM cards WHERE account_name = (?) LIMIT 1);', (account_name,))
        
        result = self.cur.fetchone()
        if result[0] == 0:
            return False

        return self.modify("UPDATE cards SET balance = (?) \
                            WHERE account_name = (?);", (balance, account_name))
