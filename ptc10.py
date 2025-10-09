"""
PTC10 Controller Interface
"""
from typing import List, Dict, Optional
from errno import EISCONN
import logging
import sys
import socket


class PTC10:
    """
    Interface for controlling the PTC10 controller.
    """
    logger = None
    sock = None
    connected = False
    success = False
    channel_names = None

    def __init__(self, logfile: Optional[str] = None, log: bool = True):
        """
        Initialize the PTC10 controller interface.

        Args:
            logfile (str, optional): Path to log file.
            log (bool): If True, start logging.
        """
        # set up logging
        if logfile is None:
            logfile = __name__.rsplit('.', 1)[-1]
        self.logger = logging.getLogger(logfile)
        self.logger.setLevel(logging.INFO)
        # log to console by default
        console_formatter = logging.Formatter(
            '%(asctime)s--%(message)s')
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        # log to file if requested
        if log:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler = logging.FileHandler(logfile)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)


    def connect(self, host: str, port: int) -> None:
        """ Connect to controller. """
        if self.sock is None:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect((host, port))
            if self.logger:
                self.logger.info("Connected to %(host)s:%(port)s", {
                    'host': host,
                    'port': port
                })
            self.connected = True
            self.success = True

        except OSError as e:
            if e.errno == EISCONN:
                if self.logger:
                    self.logger.info("Already connected")
                self.connected = True
                self.success = True
            else:
                if self.logger:
                    self.logger.error("Connection error: %s", e.strerror)
                self.connected = False
                self.success = False
        # clear socket
        if self.connected:
            self.__clear_socket()

    def __clear_socket(self):
        """ Clear socket buffer. """
        if self.sock is not None:
            self.sock.setblocking(False)
            while True:
                try:
                    _ = self.sock.recv(1024)
                except BlockingIOError:
                    break
            self.sock.setblocking(True)

    def set_verbose(self, verbose: bool =True) -> None:
        """Set verbose mode."""

        if self.logger:
            if verbose:
                self.logger.setLevel(logging.DEBUG)
            else:
                self.logger.setLevel(logging.INFO)

    def write(self, msg: str):
        """
        Send a message to the controller (adds newline).

        Args:
            msg (str): The message to send (e.g., '3A?').
        """
        try:
            self.logger.debug('Sending: %s', msg)
            self.sock.sendall((msg + "\n").encode())
        except Exception as ex:
            raise IOError(f'Failed to write message: {ex}') from ex

    def read(self) -> str:
        """
        Read a response from the controller.

        Returns:
            str: The received message, stripped of trailing newline.
        """
        try:
            retval = self.sock.recv(4096).decode().strip()
            self.logger.debug('Received: %s', retval)
            return retval
        except Exception as ex:
            raise IOError(f"Failed to read message: {ex}") from ex

    def query(self, msg: str) -> str:
        """
        Send a command and read the immediate response.

        Args:
            msg (str): Command string to send.

        Returns:
            str: Response from the controller.
        """
        self.write(msg)
        return self.read()

    def disconnect(self):
        """
        Close the connection to the controller.
        """
        try:
            self.logger.info('Closing connection to controller')
            self.sock.close()
        except Exception as ex:
            raise IOError(f"Failed to close connection: {ex}") from ex

    def identify(self) -> str:
        """
        Query the device identification string.

        Returns:
            str: Device identification (e.g. manufacturer, model, serial number, firmware version).
        """
        id_str = self.query("*IDN?")
        if self.logger:
            self.logger.info("Device identification: %s", id_str)
        return id_str

    def validate_channel_name(self, channel_name: str) -> bool:
        """Is channel name valid?"""
        if self.channel_names is None:
            self.channel_names = self.get_channel_names()
        return channel_name in self.channel_names

    def get_channel_value(self, channel: str) -> float:
        """
        Read the latest value of a specific channel.

        Args:
            channel (str): Channel name (e.g., "3A", "Out1")

        Returns:
            float: Current value, or NaN if invalid.
        """
        if self.validate_channel_name(channel):
            self.logger.debug("Channel name validated: %s", channel)
            # Spaces not allowed
            query_channel = channel.replace(" ", "")
            response = self.query(f"{query_channel}?")
            try:
                value = float(response)
                if self.logger:
                    self.logger.debug("Channel %s value: %f", channel, value)
                return value
            except ValueError:
                if self.logger:
                    self.logger.error(
                        "Invalid float returned for channel %s: %s", channel, response
                    )
                else:
                    print("Invalid float returned for channel %s: %s", channel, response)
                return float("nan")
        else:
            if self.logger:
                self.logger.error("Invalid channel name: %s", channel)
            else:
                print("Invalid channel name: %s", channel)
            return float("nan")

    def get_all_values(self) -> List[float]:
        """
        Read the latest values of all channels.

        Returns:
            List[float]: List of float values, with NaN where applicable.
        """
        response = self.query("getOutput?")
        values = [
            float(val) if val != "NaN" else float("nan") for val in response.split(",")
        ]
        if self.logger:
            self.logger.debug("Output values: %s", values)
        return values

    def get_channel_names(self) -> List[str]:
        """
        Get the list of channel names corresponding to the getOutput() values.

        Returns:
            List[str]: List of channel names.
        """
        response = self.query("getOutputNames?")
        names = [name.strip() for name in response.split(",")]
        if self.logger:
            self.logger.debug("Channel names: %s", names)
        return names

    def get_named_output_dict(self) -> Dict[str, float]:
        """
        Get a dictionary mapping channel names to their current values.

        Returns:
            Dict[str, float]: Mapping of channel names to values.
        """
        names = self.get_channel_names()
        values = self.get_all_values()
        output_dict = dict(zip(names, values))
        if self.logger:
            self.logger.debug("Named outputs: %s", output_dict)
        return output_dict
