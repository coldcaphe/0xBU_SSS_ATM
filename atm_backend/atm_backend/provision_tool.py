import logging
from interface.psoc import DeviceRemoved, AlreadyProvisioned


class ProvisionTool(object):
    """Interface for the provisioning xmlrpc server

    Args:
        bank (Bank or BankEmulator): Interface to bank
        hsm (HSM or HSMEmulator): Interface to HSM
        card (Card or CardEmulator): Interface to ATM card
    Returns:
        bool: True on Success, False on Failure
    """

    def __init__(self, bank, hsm, card):
        super(ProvisionTool, self).__init__()
        self.bank = bank
        self.hsm = hsm
        self.card = card
        logging.info('provision tool initialized')

    def ready_for_hsm(self):
        return True

    def hsm_connected(self):
        return self.hsm.connected

    def card_connected(self):
        return self.card.connected

    def provision_card(self, card_blob, pin):
        """Attempts to provision an ATM card

        Args:
            card_blob (str): Provisioning data for the ATM card
            pin (str): Initial PIN for the card

        Returns:
            bool: True on Success, False on Failure
        """
        self.card.wait_for_insert()
        if not self.card.inserted():
            logging.error('provision_card: no card was inserted!')
            return False

        try:
            logging.info('provision_card: generating card id')

            #if it doesn't contain a random PRF key and an id
            if len(card_blob) != 32 + 36:
                return False

            r = card_blob[:32]
            card_id = [32:]

            logging.info('provision_card: sending info to card')
            if not self.card.provision(r, card_id):
                return False

            logging.info('provision_card: requesting pk from card')
            pk = self.card.request_new_public_key(self.REQUEST_NEW_PK, pin)

            logging.info('provision_card: setting pin on server side')
            if not bank.set_first_pk(xmlrpclib.Binary(pk)):
                return False

            logging.error('provision_card: provision card failed!')
            return False
        except DeviceRemoved:
            logging.error('provision_card: card was removed!')
            return False
        except AlreadyProvisioned:
            logging.error('provision_card: card was already provisioned!')
            return False

    def provision_atm(self, hsm_blob, bills):
        """Attempts to provision an HSM

        Args:
            hsm_blob (str): Provisioning data for the HSM
            bills (list of str): List of bills to be stored in the HSM

        Returns:
            bool: True on Success, False on Failure
        """
        if not isinstance(bills, list):
            logging.error('provision_atm: bills input must be array')
            return False

        self.hsm.wait_for_insert()
        if not self.hsm.inserted():
            logging.error('provision_hsm: no hsm was inserted!')
            return False

        #if it doesn't contain a 32 byte encryption key + a uuid
        if len(hsm_blob) != 32 + 36:
                return False

        try:
            logging.info('provision_atm: provisioning hsm with inputted bills')
            if self.hsm.provision(hsm_blob, bills):
                logging.info('provision_atm: provisioned hsm with inputted bills')
                return True
            logging.error('provision_atm: provision failed!')
            return False
        except DeviceRemoved:
            logging.error('provision_atm: HSM was removed!')
            return False
        except AlreadyProvisioned:
            logging.error('provision_atm: HSM was already provisioned!')
            return False
