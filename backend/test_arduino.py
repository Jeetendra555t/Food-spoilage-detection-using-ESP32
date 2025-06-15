import serial
import json
import time
from datetime import datetime
import sys
import os

def read_arduino_data():
    try:
        # Try to find Arduino port
        import serial.tools.list_ports
        ports = list(serial.tools.list_ports.comports())
        arduino_port = None
        
        print("\nAvailable ports:")
        for port in ports:
            print(f"- {port.device}: {port.description}")
        
        # First try to find Arduino
        for port in ports:
            if 'Arduino' in port.description or 'CH340' in port.description:
                arduino_port = port.device
                print(f"\nFound Arduino on port: {arduino_port}")
                break
        
        # If no Arduino found, use first available port
        if not arduino_port and ports:
            arduino_port = ports[0].device
            print(f"\nUsing first available port: {arduino_port}")
        
        if not arduino_port:
            print("No suitable port found!")
            return
        
        # On Windows, try to force close any existing handles
        if sys.platform.startswith('win'):
            try:
                import win32file
                handle = win32file.CreateFile(
                    f"\\\\.\\{arduino_port}",
                    win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                    0, None, win32file.OPEN_EXISTING,
                    win32file.FILE_ATTRIBUTE_NORMAL, None
                )
                win32file.CloseHandle(handle)
            except Exception as e:
                print(f"Warning: Could not force close port: {e}")
            time.sleep(1)  # Give Windows time to release the port
        
        # Open serial port
        ser = serial.Serial(
            port=arduino_port,
            baudrate=9600,
            timeout=1
        )
        
        print("\nWaiting for Arduino to initialize...")
        time.sleep(2)  # Wait for Arduino to reset
        
        # Clear any pending data
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        print("\nStarting to read data...")
        data_buffer = ""
        last_data = None
        
        while True:
            try:
                if ser.in_waiting:
                    # Read all available bytes
                    raw_data = ser.read(ser.in_waiting)
                    decoded_data = raw_data.decode('utf-8', errors='ignore')
                    
                    # Process each character
                    for char in decoded_data:
                        if char == '{':
                            data_buffer = char
                        elif char == '}':
                            data_buffer += char
                            try:
                                data = json.loads(data_buffer)
                                if 'temperature' in data and 'humidity' in data:
                                    current_time = datetime.now().strftime('%H:%M:%S')
                                    print(f"\nTime: {current_time}")
                                    print(f"Temperature: {data['temperature']}°C")
                                    print(f"Humidity: {data['humidity']}%")
                                    print("-" * 30)
                                    last_data = data
                            except json.JSONDecodeError:
                                pass
                            data_buffer = ""
                        elif data_buffer:
                            data_buffer += char
                
                time.sleep(0.1)  # Small delay to prevent CPU overuse
                
            except KeyboardInterrupt:
                print("\nStopping data reading...")
                break
            except Exception as e:
                print(f"Error reading data: {e}")
                if last_data:
                    print("\nLast good reading:")
                    print(f"Temperature: {last_data['temperature']}°C")
                    print(f"Humidity: {last_data['humidity']}%")
                time.sleep(1)
                continue
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("Serial port closed")

if __name__ == "__main__":
    read_arduino_data() 