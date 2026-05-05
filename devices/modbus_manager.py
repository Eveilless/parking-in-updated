import os
from pymodbus.client import ModbusTcpClient
from pymodbus import FramerType
import threading

class ModbusManager:
    def __init__(self):
        host = os.getenv('ETH_HOST', '127.0.0.1')
        port = int(os.getenv('ETH_PORT', '502'))
        
        self.slave_id_input = 1
        self.slave_id_output = 1
        self.coil_address_input = 0x0081
        self.coil_address_output = 2
        self.input_count = 8
        self.coil_barrier_gate = 0
        
        # Input registers index
        self.LOOP_ONE = 0
        self.LOOP_TWO = 1
        self.BUTTON_TICKET = 2
        
        self.client = ModbusTcpClient(
            host=host,
            port=port,
            framer=FramerType.RTU,
            timeout=3,
            retries=1
        )
        self.lock = threading.Lock()

    def connect(self):
        with self.lock:
            if self.client.connect():
                print("✅ Modbus Connected")
                return True
            print("❌ Modbus Failed to connect")
            return False

    def disconnect(self):
        with self.lock:
            if self.client:
                self.client.close()
                print("🔌 Modbus Connection closed")

    def read_inputs(self):
        with self.lock:
            try:
                response = self.client.read_holding_registers(
                    address=self.coil_address_input,
                    count=self.input_count,
                    slave=self.slave_id_input
                )
                if response and not response.isError():
                    return response.registers
                return None
            except Exception as e:
                print(f"[Modbus] Read exception: {e}")
                return None

    def write_coil(self, address, state):
        with self.lock:
            try:
                result = self.client.write_coil(
                    address=self.coil_address_output + address,
                    value=bool(state),
                    slave=self.slave_id_output
                )
                if not result.isError():
                    print(f"✅ Coil {address} set to {'ON' if state else 'OFF'}")
                    return True
                return False
            except Exception as e:
                print(f"[Modbus] Write exception: {e}")
                return False
                
    def open_gate(self):
        self.write_coil(self.coil_barrier_gate, True)
        
    def close_gate(self):
        self.write_coil(self.coil_barrier_gate, False)
