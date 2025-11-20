"""
PTC10 Controller Interface
"""
from typing import List, Dict, Union
from errno import EISCONN
import socket

from hardware_device_base.hardware_sensor_base import HardwareSensorBase

class PTC10(HardwareSensorBase):
    """
    Interface for controlling the PTC10 controller.
    """
    channel_names = None

    def __init__(self, log: bool = True, logfile: str = __name__.rsplit(".", 1)[-1] ):
        """
        Initialize the PTC10 controller interface.

        Args:
            log (bool): If True, start logging.
            logfile (str, optional): Path to log file.
        """
        super().__init__(log, logfile)
        self.sock: socket.socket | None = None

    def connect(self, host, port, con_type="tcp") -> None: # pylint: disable=W0221
        """ Connect to controller. """
        if self.validate_connection_params((host, port)):
            if con_type == "tcp":
                if self.sock is None:
                    self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    self.sock.connect((host, port))
                    self.report_info(f"Connected to {host}:{port}")
                    self._set_connected(True)

                except OSError as e:
                    if e.errno == EISCONN:
                        self.report_info("Already connected")
                        self._set_connected(True)
                    else:
                        self.report_error(f"Connection error {e.strerror}")
                        self._set_connected(False)
                # clear socket
                if self.is_connected():
                    self._clear_socket()
            elif con_type == "serial":
                self.report_error("Serial connection not yet implemented")
            else:
                self.report_error(f"Unknown con_type: {con_type}")
        else:
            self.report_error(f"Invalid connection arguments: {host}:{port}")

    def _clear_socket(self):
        """ Clear socket buffer. """
        if self.sock is not None:
            self.sock.setblocking(False)
            while True:
                try:
                    _ = self.sock.recv(1024)
                except BlockingIOError:
                    break
            self.sock.setblocking(True)

    def _send_command(self, command: str) -> bool: # pylint: disable=W0221
        """
        Send a message to the controller (adds newline).

        Args:
            command (str): The message to send (e.g., '3A?').
        """
        if not self.is_connected():
            self.report_error("Device not connected")
            return False
        try:
            self.logger.debug('Sending: %s', command)
            with self.lock:
                self.sock.sendall((command + "\n").encode())
        except Exception as ex:
            self.report_error(f"Failed to send command: {ex}")
            raise IOError(f'Failed to write message: {ex}') from ex
        self.logger.debug("Command sent")
        return True

    def _read_reply(self) -> Union[str, None]:
        """
        Read a response from the controller.

        Returns:
            str: The received message, stripped of trailing newline.
        """
        if not self.is_connected():
            self.report_error("Device not connected")
            return None
        try:
            retval = self.sock.recv(4096).decode().strip()
            self.logger.debug('Received: %s', retval)
            return retval
        except Exception as ex:
            raise IOError(f"Failed to _read_reply message: {ex}") from ex

    def query(self, msg: str) -> str:
        """
        Send a command and _read_reply the immediate response.

        Args:
            msg (str): Command string to send.

        Returns:
            str: Response from the controller.
        """
        self._send_command(msg)
        return self._read_reply()

    def disconnect(self):
        """
        Close the connection to the controller.
        """
        if not self.is_connected():
            self.report_warning("Already disconnected from device")
            return
        try:
            self.logger.info('Closing connection to controller')
            if self.sock:
                self.sock.close()
                self.sock = None
            self._set_connected(False)
            self.report_info("Disconnected from device")
        except Exception as ex:
            raise IOError(f"Failed to close connection: {ex}") from ex

    def identify(self) -> str:
        """
        Query the device identification string.

        Returns:
            str: Device identification (e.g. manufacturer, model, serial number, firmware version).
        """
        id_str = self.query("*IDN?")
        self.logger.info("Device identification: %s", id_str)
        return id_str

    def validate_channel_name(self, channel_name: str) -> bool:
        """Is item name valid?"""
        if self.channel_names is None:
            self.channel_names = self.get_channel_names()
        return channel_name in self.channel_names

    def get_atomic_value(self, item: str = "") -> float:
        """
        Read the latest value of a specific item.

        Args:
            item (str): Channel name (e.g., "3A", "Out1")

        Returns:
            float: Current value, or NaN if invalid.
        """
        if self.validate_channel_name(item):
            self.logger.debug("Channel name validated: %s", item)
            # Spaces not allowed
            query_channel = item.replace(" ", "")
            response = self.query(f"{query_channel}?")
            try:
                value = float(response)
                self.logger.debug("Channel %s value: %f", item, value)
                self.report_info("Atomic value retrieved")
                return value
            except ValueError:
                self.report_error(f"Invalid float returned for item{item}: {response}")
                return float("nan")
        else:
            self.report_error(f"Invalid item name: {item}")
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
        self.logger.debug("Output values: %s", values)
        return values

    def get_channel_names(self) -> List[str]:
        """
        Get the list of item names corresponding to the getOutput() values.

        Returns:
            List[str]: List of item names.
        """
        response = self.query("getOutputNames?")
        names = [name.strip() for name in response.split(",")]
        self.logger.debug("Channel names: %s", names)
        return names

    def get_named_output_dict(self) -> Dict[str, float]:
        """
        Get a dictionary mapping item names to their current values.

        Returns:
            Dict[str, float]: Mapping of item names to values.
        """
        names = self.get_channel_names()
        values = self.get_all_values()
        output_dict = dict(zip(names, values))
        self.logger.debug("Named outputs: %s", output_dict)
        return output_dict
