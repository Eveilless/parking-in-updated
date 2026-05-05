import serial
import time
import os

class SerialReader:
    def __init__(self, port_env_key, baudrate=9600, default_port=None):
        self.port = os.getenv(port_env_key, default_port)
        self.baudrate = baudrate
        self.serial_conn = None

    def connect(self):
        if not self.serial_conn or not self.serial_conn.is_open:
            if not self.port:
                return False
            try:
                self.serial_conn = serial.Serial(self.port, self.baudrate, timeout=1)
                return True
            except serial.SerialException as e:
                print(f"[Serial {self.port}] Connection failed: {e}")
                self.serial_conn = None
                time.sleep(3)
                return False
        return True

    def read_line(self):
        if self.serial_conn and self.serial_conn.in_waiting > 0:
            return self.serial_conn.readline()
        return None

    def read_bytes(self, size):
        if self.serial_conn:
            return self.serial_conn.read(size)
        return None

    def flush(self):
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.reset_input_buffer()

    def close(self):
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            self.serial_conn = None

class EmoneyReader(SerialReader):
    def __init__(self):
        super().__init__('SERIAL_PORT')
        self.buffer = ""

    def process_stream(self, data):
        """Menerima chunk bytes, memasukkannya ke buffer, dan mencari paket 25-byte yang valid via LRC"""
        if not data:
            return None
            
        self.buffer += data.hex().upper()
        
        while len(self.buffer) >= 50:
            packet = self.buffer[:50]
            
            try:
                # Hitung LRC (byte ke-1 sampai ke-23) -> total 23 byte (46 karakter hex)
                removeHeader = packet[2:48]
                hexLRC = 0
                for i in range(0, 46, 2):
                    hexLRC ^= int(removeHeader[i:i+2], 16)
                    
                expected_lrc = int(packet[48:50], 16)
                
                if hexLRC == expected_lrc:
                    # Paket Valid!
                    self.buffer = self.buffer[50:] # Hapus dari buffer
                    
                    typeCard = packet[6:8]
                    uidCard = packet[8:22]
                    dataValidity = packet[22:24]
                    cardNo = packet[24:40]
                    balance = int(packet[40:48], 16)
                    
                    return {
                        "cardType": typeCard,
                        "uidCard": uidCard,
                        "dataValidity": dataValidity,
                        "cardNo": cardNo,
                        "balance": balance,
                    }
                else:
                    # LRC tidak cocok, geser buffer sebanyak 1 byte (2 karakter hex)
                    self.buffer = self.buffer[2:]
            except ValueError:
                # Jika ada error parsing hex, geser 1 byte
                self.buffer = self.buffer[2:]
                
        # Cegah memory leak jika terus menerus menerima sampah
        if len(self.buffer) > 1024:
            self.buffer = self.buffer[-50:]
            
        return None

class RfidReader(SerialReader):
    def __init__(self):
        super().__init__('SERIAL_PORT_RFID')

    def parse_data(self, raw_data):
        try:
            data = raw_data.decode("utf-8", errors="ignore").strip()
            if data.startswith('\x02'): data = data[1:]
            if data.endswith('\x03'): data = data[:-1]
            data = data.strip()
            
            if len(data) <= 1:
                return "", False
            try:
                data_integer = int(data, 16)
                data_str = str(data_integer)[0:10].zfill(10)
                return data_str, True
            except ValueError:
                return "", False
        except Exception as e:
            return "", False

# class LprReader(SerialReader):
#     def __init__(self):
#         super().__init__('SERIAL_PORT_LPR', baudrate=9600, default_port='/dev/ttyACM0')
#         self.buffer = ""

#     def parse_data(self, data):
#         try:
#             self.buffer += data.hex().upper()
            
#             idx = self.buffer.find("BB88AA02FF")
#             if idx == -1:
#                 idx = self.buffer.find("BB88AA03FF")
                
#             if idx != -1:
#                 # Asumsi paket 64 byte (128 karakter hex)
#                 if len(self.buffer) >= idx + 128:
#                     packet = self.buffer[idx:idx+128]
#                     self.buffer = self.buffer[idx+128:]
                    
#                     raw_plate_data = packet[10:-34]
#                     plate = bytes.fromhex(raw_plate_data).decode('ascii', errors='ignore').strip()
#                     # Bersihkan karakter non-alphanumeric
#                     plate = ''.join(e for e in plate if e.isalnum())
#                     return plate, True
#                 else:
#                     return "", False
#             else:
#                 if len(self.buffer) > 256:
#                     self.buffer = self.buffer[-128:]
#             return "", False
#         except Exception as e:
#             self.buffer = ""
#             return "", False
