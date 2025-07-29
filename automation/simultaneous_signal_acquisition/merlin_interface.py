import socket
import time

class MerlinInterface(object):
    def __init__(
            self, tcp_ip="198.0.4.2", tcp_port=6341, test_mode=False):
        
        """Class for controlling a Medipix3 detector via the Merlin software.

        The communication is done via the TCP/IP command API in the Merlin
        software.

        This class relies heavily on getters and setters, see the examples
        for how to use these.

        Parameter
        ---------
        tcp_ip : string
            IP address for the Merlin software. For connecting on the same
            computer, default "127.0.0.1".
    
        tcp_port : int
            Default 6341. This is the default port for the Merlin software
        test_mode : bool, default False

        Examples
        --------
        If the Merlin software is running on the same computer
        >>> import merlin_interface.merlin_interface as mi
        >>> merlin = mi.MerlinInterface(
        ...     tcp_ip='127.0.0.1', tcp_port=6341) # doctest: +SKIP

        Starting acquisition
        >>> merlin.startacquisition() # doctest: +SKIP

        Getting the acquisition time
        >>> merlin.acquisitiontime # doctest: +SKIP

        Getting the acquisition time (in milliseconds)
        >>> merlin.acquisitiontime = 10.0 # doctest: +SKIP

        Connection remotely
        >>> merlin = mi.MerlinInterface(
        ...     tcp_ip='10.123.141.132', tcp_port=6341) # doctest: +SKIP
        >>> merlin.startacquisition()

        Using test mode, which does not connect to anything,
        but outputs the string which is sent to the command API.
        >>> import merlin_interface.merlin_interface as mi
        >>> merlin = mi.MerlinInterface(test_mode=True)

        """
        self._tcp_ip = tcp_ip
        self._tcp_port = tcp_port
        self._receive_string_buffer = 1000
        self._message_preamble = b"MPX"
        self._socket = None
        self.test_mode = test_mode
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connected = False

    def __repr__(self):
        if self.test_mode:
            test_mode_string = "(test mode)"
        else:
            test_mode_string = ""

        return( f'<{self.__class__.__name__}, {self._tcp_ip}:{self._tcp_port} {test_mode_string}>')

    def _connect(self):
        self.socket.connect((self._tcp_ip, self._tcp_port))
        self.connected = True

    def _make_message_string(
            self,
            command_name,
            command_type,
            command_argument_list=None):
        """
        Parameters
        ----------
        command_name : bytes
        command_type : bytes
        command_argument_list : list
        """
        if command_argument_list is None:
            command_argument_list = []
        command_string_list = [
                command_type,
                command_name]
        for command_argument in command_argument_list:
            command_string_list.append(str(command_argument).encode())
       
        command_len_string = str(
                len(b",".join(
                    command_string_list))+1).zfill(10)
        
        command_string_list.insert(0, command_len_string.encode())

        command_string_list.insert(0, self._message_preamble)
        command_string = b",".join(command_string_list)
        return(command_string)

    def _send_packet(self, command_string):
        if self.test_mode:
            return_data = command_string + b",0"
        else:
            self._ensure_connected()
            try:
                self.socket.send(command_string)
                return_data = self.socket.recv(self._receive_string_buffer)
                time.sleep(0.01)
            except (socket.timeout, ConnectionError):
                self._reconnect_and_resend(command_string)
                return_data = self.socket.recv(self._receive_string_buffer)
        self._check_packet_response(command_string, return_data)
        if self.test_mode:
            print(return_data)
        return return_data

    def _ensure_connected(self):
        if not self.connected:
            self._connect()

    def _reconnect_and_resend(self, command_string):
        self._connect()
        self.socket.send(command_string)

    def _check_packet_response(self, command_string, return_data):
        # Todo: use more specific exceptions
        command_name = command_string.split(b',')[3]
        response_code = int(return_data.decode()[-1])

        if command_name not in return_data:
            raise Exception(
                f"Command name {command_name} not found in return data.")
        
        if response_code == 3:
            raise ValueError(
                "Medipix: Input parameter is out of range.")
        
        if response_code == 2:
            raise Exception(
                "Medipix: Command not recognised, probably caused by a bug in this Python wrapper.")
        
        if response_code == 1:
            raise Exception(
                "Medipix: System is busy.")

    # DRIVER VARIABLES

    @property
    def softwareversion(self):
        command_name = b"SOFTWAREVERSION"
        command_type = b"GET"
        command_string = self._make_message_string(
                command_name, command_type)
        return_data = self._send_packet(command_string)
        return(return_data)

    # EXECUTE COMMANDS

    def startacquisition(self):
            """
            Start an acquisition. If the start trigger mode is internal, the acquisition will begin immediately; otherwise the detector will arm and wait for a trigger.
            
            Example
            -------
            >>> merlin.startacquisition()
        
            """
            command_name = b"STARTACQUISITION"
            command_type = b"CMD"
            command_string = self._make_message_string(command_name, command_type)
            self._send_packet(command_string)

    def stopacquisition(self):
            """
            Stop any running acquisition, finishes sending any frames in buffers.
            
            Example
            -------
            >>> merlin.stopacquisition()
        
            """
            command_name = b"STOPACQUISITION"
            command_type = b"CMD"
            command_string = self._make_message_string(command_name, command_type)
            self._send_packet(command_string)

    def abort(self):
            """
            Stops any running acquisition, flushes image and network buffers.
            
            Example
            -------
            >>> merlin.abort()
        
            """
            command_name = b"ABORT"
            command_type = b"CMD"
            command_string = self._make_message_string(command_name, command_type)
            self._send_packet(command_string)

    def softtrigger(self):
            """
            Triggers an acquisition that has been configured for soft trigger and started.
            
            Example
            -------
            >>> merlin.softtrigger()
        
            """
            command_name = b"SOFTTRIGGER"
            command_type = b"CMD"
            command_string = self._make_message_string(command_name, command_type)
            self._send_packet(command_string)

    def thscan(self):
            """
            Perform a threshold scan.
            
            Example
            -------
            >>> merlin.thscan()
        
            """
            command_name = b"THSCAN"
            command_type = b"CMD"
            command_string = self._make_message_string(command_name, command_type)
            self._send_packet(command_string)

    def dacscan(self):
            """
            Performs a scan of a particular DAC
            
            Example
            -------
            >>> merlin.dacscan()
        
            """
            command_name = b"DACSCAN"
            command_type = b"CMD"
            command_string = self._make_message_string(command_name, command_type)
            self._send_packet(command_string)

    def standby(self):
            """
            Removes LV power to chips.
            
            Example
            -------
            >>> merlin.standby()
        
            """
            command_name = b"STANDBY"
            command_type = b"CMD"
            command_string = self._make_message_string(command_name, command_type)
            self._send_packet(command_string)

    def restart(self):
            """
            Restores power to chips, limited re-initialsation.
            
            Example
            -------
            >>> merlin.restart()
        
            """
            command_name = b"RESTART"
            command_type = b"CMD"
            command_string = self._make_message_string(command_name, command_type)
            self._send_packet(command_string)

    def noiseequalisation(self):
            """
            Performs an equalisation � using default values on screen.
            
            Example
            -------
            >>> merlin.noiseequalisation()
        
            """
            command_name = b"NOISEEQUALISATION"
            command_type = b"CMD"
            command_string = self._make_message_string(command_name, command_type)
            self._send_packet(command_string)

    def readchiptemps(self):
            """
            Reads chip temperature information from the Medipix chip DACs � must not be used during acquisition or when there is a risk of communication clashes. Note does not return values, see GET below
            
            Example
            -------
            >>> merlin.readchiptemps()
        
            """
            command_name = b"READCHIPTEMPS"
            command_type = b"CMD"
            command_string = self._make_message_string(command_name, command_type)
            self._send_packet(command_string)
            
    def reset(self):
        command_name = b"RESET"
        command_type = b"CMD"
        command_string = self._make_message_string(
                command_name,
                command_type)
        self._send_packet(command_string)

    # MEDIPIX3 modes

    # target properties

    
    @property
    def colourmode(self):
        command_name = b"COLOURMODE"
        command_type = b"GET"
        command_string = self._make_message_string(
                command_name, command_type)
        return_data = self._send_packet(command_string)
        return(return_data)

    @colourmode.setter
    def colourmode(self, value):
        command_name = b"COLOURMODE"
        command_type = b"SET"
        command_argument_list = [str(value)]
        command_string = self._make_message_string(
                command_name,
                command_type,
                command_argument_list)
        self._send_packet(command_string)

    @property
    def chargesumming(self):
        command_name = b"CHARGESUMMING"
        command_type = b"GET"
        command_string = self._make_message_string(
                command_name, command_type)
        return_data = self._send_packet(command_string)
        return(return_data)

    @chargesumming.setter
    def chargesumming(self, value):
        command_name = b"CHARGESUMMING"
        command_type = b"SET"
        command_argument_list = [str(value)]
        command_string = self._make_message_string(
                command_name,
                command_type,
                command_argument_list)
        self._send_packet(command_string)

    @property
    def gain(self):
        command_name = b"GAIN"
        command_type = b"GET"
        command_string = self._make_message_string(
                command_name, command_type)
        return_data = self._send_packet(command_string)
        return(return_data)

    @gain.setter
    def gain(self, value):
        command_name = b"GAIN"
        command_type = b"SET"
        command_argument_list = [str(value)]
        command_string = self._make_message_string(
                command_name,
                command_type,
                command_argument_list)
        self._send_packet(command_string)

    @property
    def continuousrw(self):
        command_name = b"CONTINUOUSRW"
        command_type = b"GET"
        command_string = self._make_message_string(
                command_name, command_type)
        return_data = self._send_packet(command_string)
        return(return_data)

    @continuousrw.setter
    def continuousrw(self, value):
        command_name = b"CONTINUOUSRW"
        command_type = b"SET"
        command_argument_list = [str(value)]
        command_string = self._make_message_string(
                command_name,
                command_type,
                command_argument_list)
        self._send_packet(command_string)

    @property
    def runheadless(self):
        """
        Getter method for RUNHEADLESS.
        
        
        0=Off, 1=ON turns off writes to Image Buffer. (Faster processing of images)

        Units: 
        Range: 0 - 1

        """
        command_name = b"RUNHEADLESS"
        command_type = b"GET"
        command_string = self._make_message_string(command_name, command_type)
        return_data = self._send_packet(command_string)
        return return_data

    @runheadless.setter
    def runheadless(self, value):
        command_name = b"RUNHEADLESS"
        command_type = b"SET"
        command_argument_list = [str(value)]
        command_string = self._make_message_string(command_name, command_type, command_argument_list)
        self._send_packet(command_string)

    @property
    def enablecounter1(self):
        command_name = b"ENABLECOUNTER1"
        command_type = b"GET"
        command_string = self._make_message_string(
                command_name, command_type)
        return_data = self._send_packet(command_string)
        return(return_data)

    @enablecounter1.setter
    def enablecounter1(self, value):
        command_name = b"ENABLECOUNTER1"
        command_type = b"SET"
        command_argument_list = [str(value)]
        command_string = self._make_message_string(
                command_name,
                command_type,
                command_argument_list)
        self._send_packet(command_string)

    @property
    def threshold0(self):
        command_name = b"THRESHOLD0"
        command_type = b"GET"
        command_string = self._make_message_string(
                command_name, command_type)
        return_data = self._send_packet(command_string)
        return(return_data)

    @threshold0.setter
    def threshold0(self, value):
        command_name = b"THRESHOLD0"
        command_type = b"SET"
        command_argument_list = [str(value)]
        command_string = self._make_message_string(
                command_name,
                command_type,
                command_argument_list)
        self._send_packet(command_string)

    @property
    def threshold1(self):
        command_name = b"THRESHOLD1"
        command_type = b"GET"
        command_string = self._make_message_string(
                command_name, command_type)
        return_data = self._send_packet(command_string)
        return(return_data)

    @threshold1.setter
    def threshold1(self, value):
        command_name = b"THRESHOLD1"
        command_type = b"SET"
        command_argument_list = [str(value)]
        command_string = self._make_message_string(
                command_name,
                command_type,
                command_argument_list)
        self._send_packet(command_string)

    @property
    def threshold2(self):
        command_name = b"THRESHOLD2"
        command_type = b"GET"
        command_string = self._make_message_string(
                command_name, command_type)
        return_data = self._send_packet(command_string)
        return(return_data)

    @threshold2.setter
    def threshold2(self, value):
        command_name = b"THRESHOLD2"
        command_type = b"SET"
        command_argument_list = [str(value)]
        command_string = self._make_message_string(
                command_name,
                command_type,
                command_argument_list)
        self._send_packet(command_string)

    @property
    def threshold3(self):
        command_name = b"THRESHOLD3"
        command_type = b"GET"
        command_string = self._make_message_string(
                command_name, command_type)
        return_data = self._send_packet(command_string)
        return(return_data)

    @threshold3.setter
    def threshold3(self, value):
        command_name = b"THRESHOLD3"
        command_type = b"SET"
        command_argument_list = [str(value)]
        command_string = self._make_message_string(
                command_name,
                command_type,
                command_argument_list)
        self._send_packet(command_string)

    @property
    def threshold4(self):
        command_name = b"THRESHOLD4"
        command_type = b"GET"
        command_string = self._make_message_string(
                command_name, command_type)
        return_data = self._send_packet(command_string)
        return(return_data)

    @threshold4.setter
    def threshold4(self, value):
        command_name = b"THRESHOLD4"
        command_type = b"SET"
        command_argument_list = [str(value)]
        command_string = self._make_message_string(
                command_name,
                command_type,
                command_argument_list)
        self._send_packet(command_string)

    @property
    def threshold5(self):
        command_name = b"THRESHOLD5"
        command_type = b"GET"
        command_string = self._make_message_string(
                command_name, command_type)
        return_data = self._send_packet(command_string)
        return(return_data)

    @threshold5.setter
    def threshold5(self, value):
        command_name = b"THRESHOLD5"
        command_type = b"SET"
        command_argument_list = [str(value)]
        command_string = self._make_message_string(
                command_name,
                command_type,
                command_argument_list)
        self._send_packet(command_string)

    @property
    def threshold6(self):
        command_name = b"THRESHOLD6"
        command_type = b"GET"
        command_string = self._make_message_string(
                command_name, command_type)
        self._send_packet(command_string)

    @threshold6.setter
    def threshold6(self, value):
        command_name = b"THRESHOLD6"
        command_type = b"SET"
        command_argument_list = [str(value)]
        command_string = self._make_message_string(
                command_name,
                command_type,
                command_argument_list)
        self._send_packet(command_string)

    @property
    def threshold7(self):
        command_name = b"THRESHOLD7"
        command_type = b"GET"
        command_string = self._make_message_string(
                command_name, command_type)
        return_data = self._send_packet(command_string)
        return(return_data)

    @threshold7.setter
    def threshold7(self, value):
        command_name = b"THRESHOLD7"
        command_type = b"SET"
        command_argument_list = [str(value)]
        command_string = self._make_message_string(
                command_name,
                command_type,
                command_argument_list)
        self._send_packet(command_string)

    @property
    def counterdepth(self):
        """Get or set the bit depth of the counter.

        Very important setting as it is the maximum number of counts
        each pixel on the detector can record. This also sets the
        maximum frame rate, with higher bit depths giving slower
        maximum frame rate.

        For the Merlin NN with a Medipix3 this is:
        - 24 bit, 16777216 (2**24) counts, 1.?? milliseconds
        - 12 bit, 4096 (2**13) counts, 0.86? milliseconds
        - 6 bit, 64 (2**6) counts, 0.411? milliseconds
        - 1 bit, 1 (2**1) counts, 0.081? milliseconds

        Parameters
        ----------
        value : int
            Must be 1, 6, 12 or 24

        Examples
        --------

        """
        command_name = b"COUNTERDEPTH"
        command_type = b"GET"
        command_string = self._make_message_string(
                command_name, command_type)
        return_data = self._send_packet(command_string)
        return(return_data)

    @counterdepth.setter
    def counterdepth(self, value):
        command_name = b"COUNTERDEPTH"
        command_type = b"SET"
        command_argument_list = [str(value)]
        command_string = self._make_message_string(
                command_name,
                command_type,
                command_argument_list)
        self._send_packet(command_string)

    @property
    def temperature(self):
        command_name = b"TEMPERATURE"
        command_type = b"GET"
        command_string = self._make_message_string(
                command_name, command_type)
        return_data = self._send_packet(command_string)
        return(return_data)

    @temperature.setter
    def temperature(self, value):
        command_name = b"TEMPERATURE"
        command_type = b"SET"
        command_argument_list = [str(value)]
        command_string = self._make_message_string(
                command_name,
                command_type,
                command_argument_list)
        self._send_packet(command_string)

    @property
    def hvbias(self):
        command_name = b"HVBIAS"
        command_type = b"GET"
        command_string = self._make_message_string(
                command_name, command_type)
        return_data = self._send_packet(command_string)
        return(return_data)

    @hvbias.setter
    def hvbias(self, value):
        command_name = b"HVBIAS"
        command_type = b"SET"
        command_argument_list = [str(value)]
        command_string = self._make_message_string(
                command_name,
                command_type,
                command_argument_list)
        self._send_packet(command_string)

    # ACQUISITION AND TRIGGER CONTROL

    @property
    def numframestoacquire(self):
        command_name = b"NUMFRAMESTOACQUIRE"
        command_type = b"GET"
        command_string = self._make_message_string(
                command_name, command_type)
        return_data = self._send_packet(command_string)
        return(return_data)

    @numframestoacquire.setter
    def numframestoacquire(self, value):
        command_name = b"NUMFRAMESTOACQUIRE"
        command_type = b"SET"
        command_argument_list = [str(value)]
        command_string = self._make_message_string(
                command_name,
                command_type,
                command_argument_list)
        self._send_packet(command_string)

    @property
    def acquisitiontime(self):
        command_name = b"ACQUISITIONTIME"
        command_type = b"GET"
        command_string = self._make_message_string(
                command_name, command_type)
        return_data = self._send_packet(command_string)
        return(return_data)

    @acquisitiontime.setter
    def acquisitiontime(self, value):
        command_name = b"ACQUISITIONTIME"
        command_type = b"SET"
        command_argument_list = [str(value)]
        command_string = self._make_message_string(
                command_name,
                command_type,
                command_argument_list)
        self._send_packet(command_string)

    # @property
    # def gaptime(self):
    #     command_name = b"GAPTIME"
    #     command_type = b"GET"
    #     command_string = self._make_message_string(
    #             command_name, command_type)
    #     return_data = self._send_packet(command_string)
    #     return(return_data)

    # @gaptime.setter
    # def gaptime(self, value):
    #     command_name = b"GAPTIME"
    #     command_type = b"SET"
    #     command_argument_list = [str(value)]
    #     command_string = self._make_message_string(
    #             command_name,
    #             command_type,
    #             command_argument_list)
    #     self._send_packet(command_string)

    @property
    def acquisitionperiod(self):
        command_name = b"ACQUISITIONPERIOD"
        command_type = b"GET"
        command_string = self._make_message_string(
                command_name, command_type)
        return_data = self._send_packet(command_string)
        return(return_data)

    @acquisitionperiod.setter
    def acquisitionperiod(self, value):
        command_name = b"ACQUISITIONPERIOD"
        command_type = b"SET"
        command_argument_list = [str(value)]
        command_string = self._make_message_string(
                command_name,
                command_type,
                command_argument_list)
        self._send_packet(command_string)

    @property
    def triggerstart(self):
        """Get or set the start trigger.

        Given through an integer, where the numbers correspond to the
        index in a list in the Merlin software:

        - 0: internal
        - 1: rising edge
        - 2: falling edge
        - 3: rising edge LVDS
        - 4: falling edge LVDS
        - 5: soft trigger
        - 6: multi trigger frame rising edge
        - 7: multi trigger frame falling edge
        - 8: multi trigger frame rising edge LVDS
        - 9: multi trigger frame falling edge LVDS

        Parameters
        ----------
        value : int
            Must be between 0 and 9

        """
        command_name = b"TRIGGERSTART"
        command_type = b"GET"
        command_string = self._make_message_string(
                command_name, command_type)
        return_data = self._send_packet(command_string)
        return(return_data)

    @triggerstart.setter
    def triggerstart(self, value):
        command_name = b"TRIGGERSTART"
        command_type = b"SET"
        command_argument_list = [str(value)]
        command_string = self._make_message_string(
                command_name,
                command_type,
                command_argument_list)
        self._send_packet(command_string)

    @property
    def triggerstop(self):
        """Get or set the stop trigger.

        Given through an integer, where the numbers correspond to the
        index in a list in the Merlin software:

        - 0: internal
        - 1: rising edge
        - 2: falling edge
        - 3: rising edge LVDS
        - 4: falling edge LVDS
        - 5: soft trigger
        - 6: multi trigger frame rising edge
        - 7: multi trigger frame falling edge
        - 8: multi trigger frame rising edge LVDS
        - 9: multi trigger frame falling edge LVDS

        Parameters
        ----------
        value : int
            Must be between 0 and 9

        """
        command_name = b"TRIGGERSTOP"
        command_type = b"GET"
        command_string = self._make_message_string(
                command_name, command_type)
        return_data = self._send_packet(command_string)
        return(return_data)

    @triggerstop.setter
    def triggerstop(self, value):
        command_name = b"TRIGGERSTOP"
        command_type = b"SET"
        command_argument_list = [str(value)]
        command_string = self._make_message_string(
                command_name,
                command_type,
                command_argument_list)
        self._send_packet(command_string)

    @property
    def numframespertrigger(self):
        command_name = b"NUMFRAMESPERTRIGGER"
        command_type = b"GET"
        command_string = self._make_message_string(
                command_name, command_type)
        return_data = self._send_packet(command_string)
        return(return_data)

    @numframespertrigger.setter
    def numframespertrigger(self, value):
        command_name = b"NUMFRAMESPERTRIGGER"
        command_type = b"SET"
        command_argument_list = [str(value)]
        command_string = self._make_message_string(
                command_name,
                command_type,
                command_argument_list)
        self._send_packet(command_string)

    @property
    def triggeroutttl(self):
        command_name = b"TriggerOutTTL"
        command_type = b"GET"
        command_string = self._make_message_string(
                command_name, command_type)
        return_data = self._send_packet(command_string)
        return(return_data)

    @triggeroutttl.setter
    def triggeroutttl(self, value):
        command_name = b"TriggerOutTTL"
        command_type = b"SET"
        command_argument_list = [str(value)]
        command_string = self._make_message_string(
                command_name,
                command_type,
                command_argument_list)
        self._send_packet(command_string)

    @property
    def triggeroutlvds(self):
        command_name = b"TriggerOutLVDS"
        command_type = b"GET"
        command_string = self._make_message_string(
                command_name, command_type)
        return_data = self._send_packet(command_string)
        return(return_data)

    @triggeroutlvds.setter
    def triggeroutlvds(self, value):
        command_name = b"TriggerOutLVDS"
        command_type = b"SET"
        command_argument_list = [str(value)]
        command_string = self._make_message_string(
                command_name,
                command_type,
                command_argument_list)
        self._send_packet(command_string)

    @property
    def triggeroutttlinvert(self):
        command_name = b"TriggerOutTTLInvert"
        command_type = b"GET"
        command_string = self._make_message_string(
                command_name, command_type)
        return_data = self._send_packet(command_string)
        return(return_data)

    @triggeroutttlinvert.setter
    def triggeroutttlinvert(self, value):
        command_name = b"TriggerOutTTLInvert"
        command_type = b"SET"
        command_argument_list = [str(value)]
        command_string = self._make_message_string(
                command_name,
                command_type,
                command_argument_list)
        self._send_packet(command_string)

    @property
    def triggeroutlvdsinvert(self):
        command_name = b"TriggerOutLVDSInvert"
        command_type = b"GET"
        command_string = self._make_message_string(
                command_name, command_type)
        return_data = self._send_packet(command_string)
        return(return_data)

    @triggeroutlvdsinvert.setter
    def triggeroutlvdsinvert(self, value):
        command_name = b"TriggerOutLVDSInvert"
        command_type = b"SET"
        command_argument_list = [str(value)]
        command_string = self._make_message_string(
                command_name,
                command_type,
                command_argument_list)
        self._send_packet(command_string)

    @property
    def triggeroutttldelay(self):
        command_name = b"TriggerOutTTLDelay"
        command_type = b"GET"
        command_string = self._make_message_string(
                command_name, command_type)
        return_data = self._send_packet(command_string)
        return(return_data)

    @triggeroutttldelay.setter
    def triggeroutttldelay(self, value):
        command_name = b"TriggerOutTTLDelay"
        command_type = b"SET"
        command_argument_list = [str(value)]
        command_string = self._make_message_string(
                command_name,
                command_type,
                command_argument_list)
        self._send_packet(command_string)

    @property
    def triggeroutlvdsdelay(self):
        command_name = b"TriggerOutLVDSDelay"
        command_type = b"GET"
        command_string = self._make_message_string(
                command_name, command_type)
        return_data = self._send_packet(command_string)
        return(return_data)

    @triggeroutlvdsdelay.setter
    def triggeroutlvdsdelay(self, value):
        command_name = b"TriggerOutLVDSDelay"
        command_type = b"SET"
        command_argument_list = [str(value)]
        command_string = self._make_message_string(
                command_name,
                command_type,
                command_argument_list)
        self._send_packet(command_string)

    @property
    def triggerusedelay(self):
        command_name = b"TriggerUseDelay"
        command_type = b"GET"
        command_string = self._make_message_string(
                command_name, command_type)
        return_data = self._send_packet(command_string)
        return(return_data)

    @triggerusedelay.setter
    def triggerusedelay(self, value):
        command_name = b"TriggerUseDelay"
        command_type = b"SET"
        command_argument_list = [str(value)]
        command_string = self._make_message_string(
                command_name,
                command_type,
                command_argument_list)
        self._send_packet(command_string)


    @property
    def softtriggeroutttl(self):
        command_name = b"SoftTriggerOutTTL"
        command_type = b"GET"
        command_string = self._make_message_string(
                command_name, command_type)
        return_data = self._send_packet(command_string)
        return(return_data)

    @softtriggeroutttl.setter
    def softtriggeroutttl(self, value):
        command_name = b"SoftTriggerOutTTL"
        command_type = b"SET"
        command_argument_list = [str(value)]
        command_string = self._make_message_string(
                command_name,
                command_type,
                command_argument_list)
        self._send_packet(command_string)

    @property
    def softtriggeroutlvds(self):
        command_name = b"SoftTriggerOutLVDS"
        command_type = b"GET"
        command_string = self._make_message_string(
                command_name, command_type)
        return_data = self._send_packet(command_string)
        return(return_data)

    @softtriggeroutlvds.setter
    def softtriggeroutlvds(self, value):
        command_name = b"SoftTriggerOutLVDS"
        command_type = b"SET"
        command_argument_list = [str(value)]
        command_string = self._make_message_string(
                command_name,
                command_type,
                command_argument_list)
        self._send_packet(command_string)


    # Threshold scan control

    @property
    def thscan(self):
        command_name = b"THSCAN"
        command_type = b"GET"
        command_string = self._make_message_string(
                command_name, command_type)
        return_data = self._send_packet(command_string)
        return(return_data)

    @thscan.setter
    def thscan(self, value):
        command_name = b"THSCAN"
        command_type = b"SET"
        command_argument_list = [str(value)]
        command_string = self._make_message_string(
                command_name,
                command_type,
                command_argument_list)
        self._send_packet(command_string)

    @property
    def thstart(self):
        command_name = b"THSTART"
        command_type = b"GET"
        command_string = self._make_message_string(
                command_name, command_type)
        return_data = self._send_packet(command_string)
        return(return_data)

    @thstart.setter
    def thstart(self, value):
        command_name = b"THSTART"
        command_type = b"SET"
        command_argument_list = [str(value)]
        command_string = self._make_message_string(
                command_name,
                command_type,
                command_argument_list)
        self._send_packet(command_string)

    @property
    def thstop(self):
        command_name = b"THSTOP"
        command_type = b"GET"
        command_string = self._make_message_string(
                command_name, command_type)
        return_data = self._send_packet(command_string)
        return(return_data)

    @thstop.setter
    def thstop(self, value):
        command_name = b"THSTOP"
        command_type = b"SET"
        command_argument_list = [str(value)]
        command_string = self._make_message_string(
                command_name,
                command_type,
                command_argument_list)
        self._send_packet(command_string)

    @property
    def thstep(self):
        command_name = b"THSTEP"
        command_type = b"GET"
        command_string = self._make_message_string(
                command_name, command_type)
        return_data = self._send_packet(command_string)
        return(return_data)

    @thstep.setter
    def thstep(self, value):
        command_name = b"THSTEP"
        command_type = b"SET"
        command_argument_list = [str(value)]
        command_string = self._make_message_string(
                command_name,
                command_type,
                command_argument_list)
        self._send_packet(command_string)

    @property
    def thnumsteps(self):
        command_name = b"THNUMSTEPS"
        command_type = b"GET"
        command_string = self._make_message_string(
                command_name, command_type)
        return_data = self._send_packet(command_string)
        return(return_data)

    @thnumsteps.setter
    def thnumsteps(self, value):
        command_name = b"THNUMSTEPS"
        command_type = b"SET"
        command_argument_list = [str(value)]
        command_string = self._make_message_string(
                command_name,
                command_type,
                command_argument_list)
        self._send_packet(command_string)

    # Local File Saving Control

    @property
    def filedirectory(self):
        command_name = b"FILEDIRECTORY"
        command_type = b"GET"
        command_string = self._make_message_string(
                command_name, command_type)
        return_data = self._send_packet(command_string)
        return(return_data)

    @filedirectory.setter
    def filedirectory(self, value):
        command_name = b"FILEDIRECTORY"
        command_type = b"SET"
        command_argument_list = [str(value)]
        command_string = self._make_message_string(
                command_name,
                command_type,
                command_argument_list)
        self._send_packet(command_string)

    @property
    def filename(self):
        command_name = b"FILENAME"
        command_type = b"GET"
        command_string = self._make_message_string(
                command_name, command_type)
        return_data = self._send_packet(command_string)
        return(return_data)

    @filename.setter
    def filename(self, value):
        command_name = b"FILENAME"
        command_type = b"SET"
        command_argument_list = [str(value)]
        command_string = self._make_message_string(
                command_name,
                command_type,
                command_argument_list)
        self._send_packet(command_string)

    @property
    def fileenable(self):
        command_name = b"FILEENABLE"
        command_type = b"GET"
        command_string = self._make_message_string(
                command_name, command_type)
        return_data = self._send_packet(command_string)
        return(return_data)

    @fileenable.setter
    def fileenable(self, value):
        command_name = b"FILEENABLE"
        command_type = b"SET"
        command_argument_list = [str(value)]
        command_string = self._make_message_string(
                command_name,
                command_type,
                command_argument_list)
        self._send_packet(command_string)

    @property
    def savealltofile(self):
        """
        Getter method for SAVEALLTOFILE.
        
        
        0=Disable, 1=Enable. When enabled the Merlin software all frames to a single file.

        Units: 
        Range: 0 - 1

        """
        command_name = b"SAVEALLTOFILE"
        command_type = b"GET"
        command_string = self._make_message_string(command_name, command_type)
        return_data = self._send_packet(command_string)
        return return_data

    @savealltofile.setter
    def savealltofile(self, value):
        command_name = b"SAVEALLTOFILE"
        command_type = b"SET"
        command_argument_list = [str(value)]
        command_string = self._make_message_string(command_name, command_type, command_argument_list)
        self._send_packet(command_string)

    @property
    def usetimestamping(self):
        """
        Getter method for USETIMESTAMPING.
        
        
        0=Off, 1=ON. Creates a new Time Stamped Directory for every acquisition. (Prevents overwriting of files in error.)

        Units: 
        Range: 0 - 1

        """
        command_name = b"USETIMESTAMPING"
        command_type = b"GET"
        command_string = self._make_message_string(command_name, command_type)
        return_data = self._send_packet(command_string)
        return return_data

    @usetimestamping.setter
    def usetimestamping(self, value):
        command_name = b"USETIMESTAMPING"
        command_type = b"SET"
        command_argument_list = [str(value)]
        command_string = self._make_message_string(command_name, command_type, command_argument_list)
        self._send_packet(command_string)
    # Commands related to getting the status of the detector
 
    @property
    def detectorstatus(self):
        command_name = b"DETECTORSTATUS"
        command_type = b"GET"
        command_string = self._make_message_string(
                command_name, command_type)
        return_data = self._send_packet(command_string)
        return(return_data)
