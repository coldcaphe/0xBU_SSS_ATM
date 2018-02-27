""" Admin Backend

This module implements the admin interface as defined by the rules and
requirements of the 2018 Collegiate eCTF.

The module exposes the following functions using an xmlrpcserver listening on
host 127.0.0.1 and port 1338

The following interface must be supported by the XMLRPC server
running in your Bank Server.

        The following interface must be supported by the XMLRPC server
        running in your Bank Server.

        ------------------------------------------------------------------------
        function:
            ready_for_atm - check if bank is ready for atms to connect

        args:
            None

        returns:
            bool: True for success, False otherwise.
        ------------------------------------------------------------------------
        function:
            create_account

        args:
            param1 (string - max length 1024): AccountName for created card
            param2 (int): Starting account balance

        returns:
            xmlrpclib base64: Card provisioning material on Success.
            bool: False otherwise.
        ------------------------------------------------------------------------
        function:
            update_balance

        args:
            param1 (string - max length 1024): AccountName of card
            param2 (int): new account balance

        returns:
            bool: True for success, False otherwise.
        ------------------------------------------------------------------------
        function:
            check_balance

        args:
            param1 (string - max length 1024): AccountName of card

        returns:
            int: Account balance on Success.
            bool: False otherwise.
        ------------------------------------------------------------------------
        function:
            create_atm

        args:
            None

        returns:
            xmlrpclib base64:: ATM provisioning material on Success.
            bool: False otherwise.
        ------------------------------------------------------------------------
"""

import uuid
import logging
import xmlrpclib
import os

from SimpleXMLRPCServer import SimpleXMLRPCServer
from . import DB



class AdminBackend(object):
    """ Implemenation of Admin Interface fulfilling competition requirements

    The methods create_account, update_balance, check_balance, and create_atm
    are exposed via an xmlrpc server in __init__. Introspection functions are
    also expose to ease service discovery on the client-side.

    """
    def __init__(self, config, db_mutex, ready_event):
        """ __init__ reads config object and registers interface to xmlrpc

        Args:
            config (dict): dictionary with xmlrpc host and port information
                            as well as database filepath
            db_mutex (object): mutex for accessing database
        """
        super(AdminBackend, self).__init__()
        self.admin_host = config['admin']['host']
        self.admin_port = config['admin']['port']
        self.db_path = config['database']['db_path']
        self.db_mutex = db_mutex
        self.ready_event = ready_event

        self.db_obj = DB(db_path=self.db_path)
        server = SimpleXMLRPCServer((self.admin_host, self.admin_port))
        server.register_introspection_functions()
        server.register_function(self.create_account)
        server.register_function(self.update_balance)
        server.register_function(self.check_balance)
        server.register_function(self.create_atm)
        server.register_function(self.ready_for_atm)
        logging.info('admin interface listening on ' + self.admin_host + ':' + str(self.admin_port))
        server.serve_forever()

    def ready_for_atm(self):
        return self.ready_event.isSet()

    def create_account(self, account_name, amount):
        """Create account with account_name starting amount

        Args:
            account_name(string): name for account
            amount(string): initial balance

        Returns:
            Returns randomly generated secret | name padded to 1024 bits on Success.
                    False on Failure.

        """
        try:
            amount = int(amount)
        except ValueError:
            logging.info('amount must be a integer')
            return False

        card_id = str(uuid.uuid4())

        if self.db_obj.admin_create_account(account_name, card_id, amount):
            logging.info('admin create account success')
            r = os.urandom(32)

            return xmlrpclib.Binary(r + card_id)

        logging.info('admin create account failed')
        return False

    def update_balance(self, account_name, amount):
        """Update balance of account: account_name with amount

        Args:
            account_name(string): account_name of account
            amount(string): new balance

        Returns:
            Returns True on Success. False on Failure.

        """
        if self.db_obj.admin_set_balance(account_name, amount):
            logging.info('admin update balance success')
            return True
        logging.info('admin update balance failure')
        return False

    def check_balance(self, account_name):
        """Check balance of account: account_name

        Args:
            account_name(string): account_name of account

        Returns:
            Returns balance (string) on Success. False on Failure.

        """
        balance = self.db_obj.admin_get_balance(account_name)
        if balance is not None:
            logging.info('admin check_balance success')
            return balance
        logging.info('admin check_balance failure')
        return False

    #todo create provisioning data
    def create_atm(self):
        """Create atm

        Returns:
            Returns hsm id | hsm key on Success
                    False on Failure.
        """
        hsm_id = str(uuid.uuid4())
        hsm_key = os.urandom(32)

        if self.db_obj.admin_create_atm(hsm_id, hsm_key):
            logging.info('admin create_atm success')
            return xmlrpclib.Binary(hsm_id + hsm_key)
        logging.info('admin create_atm failure')
        return False
