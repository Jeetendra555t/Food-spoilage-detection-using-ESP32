import serial
import serial.tools.list_ports
import json
import time
import threading
import sys
import os
import atexit
from datetime import datetime

# Global configuration
ARDUINO_CONFIG = {
    'port': None,  # Will be auto-detected
    'baudrate': 9600,
    'timeout': 1
}

class SerialReader:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(SerialReader, cls).__new__(cls)
        return cls._instance

    def __init__(self, port=None):
        if not hasattr(self, 'initialized'):
            self.initialized = True
            print("\n=== Initializing SerialReader ===")
            self.serial_port = None
            self.is_running = True
            self.latest_data = {
                'temperature': 0.0,
                'humidity': 0.0,
                'lastUpdate': 'Never',
                'connected': False
            }
            self.read_thread = None
            self.port_name = port
            self.connection_lock = threading.Lock()
            self.data_buffer = ""
            self.last_read_time = time.time()
            self.reconnect_delay = 5
            self.port_initialized = False
            self.should_stop = False
            self.last_good_data = None
            
            # Find and connect to Arduino
            self._find_arduino_port()
            self._start_reading()
            
            # Register cleanup on program exit
            atexit.register(self.stop)

    def _find_arduino_port(self):
        """Find and set the Arduino port"""
        if sys.platform.startswith('win'):
            ports = list(serial.tools.list_ports.comports())
            
            # First try to use specified port if provided
            if self.port_name:
                for port in ports:
                    if port.device == self.port_name:
                        return
            
            # Then try to find any Arduino
            for port in ports:
                if 'Arduino' in port.description or 'CH340' in port.description:
                    self.port_name = port.device
                    return
            
            # If no Arduino found, try any available port
            if ports:
                self.port_name = ports[0].device
                return
        
        else:
            for port in ['/dev/ttyUSB0', '/dev/ttyACM0', '/dev/tty.usbserial']:
                if os.path.exists(port):
                    self.port_name = port
                    return
        
        self.port_name = None

    def _open_serial_port(self):
        """Open the serial port with proper error handling"""
        if self.serial_port and self.serial_port.is_open:
            return True

        try:
            # On Windows, try to force close any existing handles
            if sys.platform.startswith('win'):
                try:
                    import win32file
                    handle = win32file.CreateFile(
                        f"\\\\.\\{self.port_name}",
                        win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                        0, None, win32file.OPEN_EXISTING,
                        win32file.FILE_ATTRIBUTE_NORMAL, None
                    )
                    win32file.CloseHandle(handle)
                except:
                    pass
                time.sleep(1)  # Give Windows time to release the port

            self.serial_port = serial.Serial(
                port=self.port_name,
                baudrate=9600,
                timeout=1
            )
            
            # Wait for Arduino to reset
            time.sleep(2)
            
            # Clear any pending data
            self.serial_port.reset_input_buffer()
            self.serial_port.reset_output_buffer()
            
            with self.connection_lock:
                self.latest_data['connected'] = True
                self.latest_data['lastUpdate'] = datetime.now().strftime('%H:%M:%S')
                if self.last_good_data:
                    self.latest_data.update(self.last_good_data)
            self.port_initialized = True
            return True
            
        except Exception as e:
            with self.connection_lock:
                if self.last_good_data:
                    self.latest_data.update(self.last_good_data)
                self.latest_data['connected'] = False
            self.port_initialized = False
            return False

    def _start_reading(self):
        """Start the reading thread"""
        if not self.read_thread or not self.read_thread.is_alive():
            self.should_stop = False
            self.read_thread = threading.Thread(target=self._read_loop)
            self.read_thread.daemon = True
            self.read_thread.start()

    def _read_loop(self):
        """Main reading loop that continuously monitors the serial port"""
        consecutive_errors = 0
        max_consecutive_errors = 3
        
        while self.is_running and not self.should_stop:
            try:
                # Try to open port if not already open
                if not self._open_serial_port():
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        self._find_arduino_port()
                        consecutive_errors = 0
                    time.sleep(self.reconnect_delay)
                    continue

                # Read data if available
                if self.serial_port.in_waiting:
                    try:
                        # Read all available bytes
                        raw_data = self.serial_port.read(self.serial_port.in_waiting)
                        
                        # Try to decode as string
                        try:
                            decoded_data = raw_data.decode('utf-8', errors='ignore')
                            
                            # Process each character
                            for char in decoded_data:
                                if char == '{':
                                    self.data_buffer = char
                                elif char == '}':
                                    self.data_buffer += char
                                    self._process_data(self.data_buffer)
                                    self.data_buffer = ""
                                    consecutive_errors = 0
                                elif self.data_buffer:
                                    self.data_buffer += char
                        except UnicodeDecodeError:
                            continue
                            
                        self.last_read_time = time.time()
                    except:
                        continue
                
                # Check for timeout
                if time.time() - self.last_read_time > 10:  # 10 seconds timeout
                    self._cleanup_port()
                    time.sleep(1)
                    continue
                    
            except:
                consecutive_errors += 1
                self._cleanup_port()
                time.sleep(1)
                continue

    def _process_data(self, data_str):
        """Process and validate the received data"""
        try:
            data = json.loads(data_str)
            
            if 'temperature' in data and 'humidity' in data:
                with self.connection_lock:
                    new_data = {
                        'temperature': float(data['temperature']),
                        'humidity': float(data['humidity']),
                        'lastUpdate': datetime.now().strftime('%H:%M:%S'),
                        'connected': True
                    }
                    self.latest_data.update(new_data)
                    self.last_good_data = {
                        'temperature': float(data['temperature']),
                        'humidity': float(data['humidity'])
                    }
                print(f"Temperature: {data['temperature']}°C, Humidity: {data['humidity']}% | SerialReader instance id (in thread): {id(self)}")
        except:
            pass

    def _cleanup_port(self):
        """Safely close and cleanup the serial port"""
        with self.connection_lock:
            try:
                if self.serial_port:
                    if self.serial_port.is_open:
                        self.serial_port.close()
                    self.serial_port = None
            except:
                pass
            finally:
                if sys.platform.startswith('win'):
                    time.sleep(1)

    def get_latest_data(self):
        """Thread-safe method to get the latest data"""
        with self.connection_lock:
            return self.latest_data.copy()

    def stop(self):
        """Cleanup method for Flask app context"""
        self.should_stop = True
        self.is_running = False
        self._cleanup_port()

    @staticmethod
    def set_port(new_port):
        """Change the Arduino port"""
        self.port_name = new_port
        self._cleanup_port()
        self._start_reading() 