import struct
import time
import logging
import threading
import serial
import sys
import os

from binascii import hexlify
from serial.tools.list_ports import comports as list_ports


class DeviceRemoved(Exception):
    pass


class NotProvisioned(Exception):
    pass


class AlreadyProvisioned(Exception):
    pass


class Psoc(object):
    """
    Generic PSoC communication interface

    Args:
        name (str): Name of the PSoC for debugging
        ser (serial.Serial or serial emulator): Serial interface for
            communication
        verbose (bool): Controls printing of debug messages
    """

    def __init__(self, name, ser, verbose):
        log = sys.stdout if verbose else open(os.devnull, 'w')
        logging.basicConfig(stream=log, level=logging.DEBUG)
        self.ser = ser
        self.verbose = verbose
        self.fmt = '%s: %%s' % name
        self.name = name
        self.lock = threading.Lock()
        self.connected = False
        self.port = ''
        self.baudrate = 115200
        self.old_ports = [port_info.device for port_info in list_ports()]

        self.SYNC_REQUEST_PROV         = 0x15
        self.SYNC_REQUEST_NO_PROV      = 0x16
        self.SYNC_CONFIRMED_PROV       = 0x17
        self.SYNC_CONFIRMED_NO_PROV    = 0x18
        self.SYNC_FAILED_NO_PROV       = 0x19
        self.SYNC_FAILED_PROV          = 0x1A
        self.SYNCED                    = 0x1B
        self.SYNC_TYPE_HSM_N           = 0x1C
        self.SYNC_TYPE_HSM_P           = 0x3C
        self.SYNC_TYPE_CARD_N          = 0x1D
        self.SYNC_TYPE_CARD_P          = 0x3D
        self.PSOC_DEVICE_REQUEST       = 0x1E

        self.sync_name_n = '%s_N' % name
        self.sync_name_p = '%s_P' % name


        if ser:
            self.connected = True
        else:
            self.start_connect_watcher()

    def _vp(self, msg, stream=logging.info):
        """
        Prints message if verbose was set

        Args:
            msg (str): message to print
            stream (logging function, optional): logging function to call
        """
        if self.verbose:
            stream(self.fmt % msg)

    def _push_msg(self, msg):
        """
        Sends formatted message to PSoC

        Args:
            msg (str): message to be sent to the PSoC
        """
        #pkt = struct.pack("B%ds" % (len(msg)), len(msg), msg)
        pkt = struct.pack("%ds" % len(msg), msg)
        self.write(pkt)
        time.sleep(0.1)

    def _pull_msg(self):
        """
        Pulls message form the PSoC

        Returns:
            string with message from PSoC
        """
        hdr = self.read(size=1)
        if len(hdr) != 1:
            self._vp("RECEIVED BAD HEADER: \'%s\'" % hdr, logging.error)
            return ''
        pkt_len = struct.unpack('B', hdr)[0]
        return self.read(pkt_len)

    def _sync_once(self,request,accept,wrong_states):
        resp = ''
        while resp not in accept:
            self._push_msg(chr(request))
            resp = self.read(size=1)
            print "resp=", hexlify(resp), resp
            if resp == "":
                continue
            resp = ord(resp)


            # if in wrong state (provisioning/normal)
            if resp in wrong_states:
                #self._vp(str(resp))
                return False

        self._vp(resp)
        return resp

    def _sync(self, provision):
        """
        Synchronize communication with PSoC

        Args:
            provision (bool): Whether expecting unprovisioned state

        Raises:
            NotProvisioned if PSoC is unexpectedly unprovisioned
            AlreadyProvisioned if PSoC is unexpectedly already provisioned
        """
        if provision:
            #self._push_msg(chr(self.SYNC_REQUEST_NO_PROV))

            if not self._sync_once(self.SYNC_REQUEST_PROV,
                [self.SYNC_CONFIRMED_NO_PROV],
                [self.SYNC_CONFIRMED_PROV,
                self.SYNC_FAILED_NO_PROV,
                self.SYNC_FAILED_PROV]):

                self._vp("Already provisioned!", logging.error)
                raise AlreadyProvisioned
        else:
            if not self._sync_once(self.SYNC_REQUEST_NO_PROV,
                [self.SYNC_CONFIRMED_PROV],
                [self.SYNC_CONFIRMED_NO_PROV,
                self.SYNC_FAILED_NO_PROV,
                self.SYNC_FAILED_PROV]):

                self._vp("Not yet provisioned!", logging.error)
                raise NotProvisioned

        self._push_msg(chr(self.SYNCED))

    def open(self):
        time.sleep(.1)
        self.ser = serial.Serial(self.port, baudrate=self.baudrate, timeout=1)
        resp = self._sync_once(self.PSOC_DEVICE_REQUEST,[self.SYNC_TYPE_HSM_P, self.SYNC_TYPE_HSM_N, self.SYNC_TYPE_CARD_P, self.SYNC_TYPE_CARD_N],[])
        print "syncd", hexlify(resp), resp
        resp_f = "Error"
        if resp == chr(self.SYNC_TYPE_HSM_P):
            resp_f="HSM_P"
        elif resp == chr(self.SYNC_TYPE_HSM_N):
            resp_f="HSM_N"
        elif resp == chr(self.SYNC_TYPE_CARD_P):
            resp_f="CARD_P"
        elif resp == chr(self.SYNC_TYPE_CARD_N):
            resp_f="CARD_N"
        if resp_f == self.sync_name_p or resp_f == self.sync_name_n:
            logging.info('DYNAMIC SERIAL: Connected to %s', resp)
            self.connected = True
        else:
            logging.info('DYNAMIC SERIAL: Expected %s or %s', self.sync_name_p,
                                                              self.sync_name_n)
            logging.info('DYNAMIC SERIAL: Disconnecting from %s', resp)
            self.start_connect_watcher()

    def device_connect_watch(self):
        """Threaded function that connects to new serial devices"""

        # Read current ports
        connecting = []

        # Has a new device connected?
        while len(connecting) == 0:
            new_ports = [port_info.device for port_info in list_ports()]
            connecting = list(set(new_ports) - set(self.old_ports))
            self.old_ports = new_ports
            time.sleep(.25)
        self.port = connecting[0]
        logging.info("DYNAMIC SERIAL: Found new serial device")
        self.open()
        if self.name == 'CARD':
            self.start_disconnect_watcher()

    def device_disconnect_watch(self):
        """Threaded function that connects to new serial devices"""

        # Read current ports
        disconnecting = []

        # Has a new device connected?
        while not disconnecting and self.port not in disconnecting:
            new_ports = [port_info.device for port_info in list_ports()]
            disconnecting = list(set(self.old_ports) - set(new_ports))
            self.old_ports = new_ports

        logging.info("DYNAMIC SERIAL: %s disconnected", self.name)
        self.port = ''
        self.connected = False
        self.lock.acquire()
        self.ser.close()
        self.lock.release()
        self.start_connect_watcher()

    def read(self, size=1):
        """
        Reads bytes from the connected serial device

        Args:
            size (int, optional): The number of bytes to read from the serial
                device. Defaults to reading one byte.

        Returns:
            str: Buffer of bytes read from device

        Raises:
            DeviceRemoved: If the Device was removed before or during read
        """
        try:
            self.lock.acquire()
            res = self.ser.read(size=size)
            print "read: ", hexlify(res), res
            self.lock.release()
            return res
        except serial.SerialException:
            self.connected = False
            self.ser.close()
            self.lock.release()
            self.start_connect_watcher()
            raise DeviceRemoved

    def write(self, data):
        """
        Writes bytes to the connected serial device

        Args:
            data (str): The bytes to be written to the serial device

        Raises:
            DeviceRemoved: If the Device was removed before or during write
        """
        try:
            self.lock.acquire()
            res = self.ser.write(data)
            print "write: ", hexlify(data), data

            self.lock.release()
            return res
        except serial.SerialException:
            self.connected = False
            self.ser.close()
            self.lock.release()
            self.start_connect_watcher()
            raise DeviceRemoved

    def start_connect_watcher(self):
        logging.info("DYNAMIC SERIAL: Closed serial and spun off %s-connect-watcher thread", self.name)
        self.old_ports = [port_info.device for port_info in list_ports()]
        threading.Thread(target=self.device_connect_watch, name="%s-watcher" % self.name).start()

    def start_disconnect_watcher(self):
        logging.info("DYNAMIC SERIAL: Opened serial and spun off %s-disconnect-watcher thread", self.name)
        self.old_ports = [port_info.device for port_info in list_ports()]
        threading.Thread(target=self.device_disconnect_watch, name="%s-disconnect-watcher" % self.name).start()

    def inserted(self):
        """
        Queries if serial port to ATM card is open

        Returns:
            bool: True if port is open, False otherwise
        """
        return self.ser.isOpen()

    def wait_for_insert(self):
        """Blocks until a card is dynamically acquired"""
        self._vp('Waiting for card insertion')
        while not self.ser:
            time.sleep(.25)
        while not self.ser.isOpen():
            time.sleep(.25)
