"""
PTC10 Controller Interface
"""
from typing import List, Dict, Optional
import logging
import sys
import socket

class PTC10:
    """
    Interface for controlling the PTC10 controller.
    """
    logger = None
    sock = None

    def __init__(self, logfile: Optional[str] = None, log: bool = True):
        """
        Initialize the PTC10 controller interface.

        Args:
            logfile (str, optional): Path to log file.
            log (bool): If True, start logging.
        """
        if log:
            if logfile is None:
                logfile = __name__.rsplit('.', 1)[-1] + '.log'
            self.logger = logging.getLogger(logfile)
            self.logger.setLevel(logging.INFO)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler = logging.FileHandler(logfile)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

            console_formatter = logging.Formatter(
                '%(asctime)s--%(message)s')
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)
        else:
            self.logger = None

    def connect(self, host: str =None, port: int = None) -> None:
        """Connect to the PTC10 controller."""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(1.0)
        self.sock.connect((host, port))

    def write(self, msg: str):
        """
        Send a message to the controller (adds newline).

        Args:
            msg (str): The message to send (e.g., '3A?').
        """
        try:
            self.sock.sendall((msg + "\n").encode())
        except Exception as ex:
            raise IOError(f"Failed to write message: {ex}")

    def read(self) -> str:
        """
        Read a response from the controller.

        Returns:
            str: The received message, stripped of trailing newline.
        """
        try:
            return self.sock.recv(4096).decode().strip()
        except Exception as ex:
            raise IOError(f"Failed to read message: {ex}")

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

    def close(self):
        """
        Close the connection to the controller.
        """
        try:
            self.sock.close()
        except Exception as ex:
            raise IOError(f"Failed to close connection: {ex}")

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

    def get_channel_value(self, channel: str) -> float:
        """
        Read the latest value of a specific channel.

        Args:
            channel (str): Channel name (e.g., "3A", "Out1")

        Returns:
            float: Current value, or NaN if invalid.
        """
        response = self.query(f"{channel}?")
        try:
            value = float(response)
            if self.logger:
                self.logger.info("Channel %s value: %f", channel, value)
            return value
        except ValueError:
            if self.logger:
                self.logger.error(
                    "Invalid float returned for channel %s: %s", channel, response
                )
            else:
                print("Invalid float returned for channel %s: %s", channel, response)
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
            self.logger.info("Output values: %s", values)
        return values

    def get_channel_names(self) -> List[str]:
        """
        Get the list of channel names corresponding to the getOutput() values.

        Returns:
            List[str]: List of channel names.
        """
        response = self.query("getOutputNames?")
        names = [name.strip() for name in response.split(",")]
        self.logger.info("Channel names: %s", names)
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
        self.logger.info("Named outputs: %s", output_dict)
        return output_dict
