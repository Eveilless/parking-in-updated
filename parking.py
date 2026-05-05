import os
import sys
import glob
import shutil
from dotenv import load_dotenv

from core.controller import ParkingController
from devices.modbus_manager import ModbusManager
from devices.printer_manager import PrinterManager
from devices.serial_readers import EmoneyReader, RfidReader
from devices.oled_manager import OledManager
from services.api_client import ApiClient
from services.offline_manager import OfflineManager
import ui  # Menggunakan ui.py yang sudah ada

def setup_environment():
    local_env = "/home/pi/parking-in/.env"
    env_files = glob.glob('/media/pi/*/.env')
    
    if env_files:
        ENV_PATH = env_files[0]
        print(f"Konfigurasi ditemukan di flashdisk: {ENV_PATH}")
        try:
            shutil.copy2(ENV_PATH, local_env)
            print("Berhasil menyalin .env dari flashdisk ke direktori proyek.")
        except Exception as e:
            print(f"Gagal menyalin .env: {e}")
    else:
        if not os.path.exists(local_env):
            print("ERROR: File .env tidak ditemukan di /media/pi/ maupun lokal. Pastikan flashdisk terpasang.")
            sys.exit(1)
        else:
            print("Flashdisk tidak ditemukan. Memuat konfigurasi dari direktori lokal proyek.")

    load_dotenv(local_env, override=True)

def main():
    print("🚀 Memulai Sistem Parking In (Refactored)...")
    setup_environment()
    
    # 1. Inisialisasi Perangkat Hardware
    modbus = ModbusManager()
    printer = PrinterManager()
    emoney = EmoneyReader()
    rfid = RfidReader()
    oled = OledManager()
    
    # 2. Inisialisasi Layanan
    api = ApiClient()
    offline = OfflineManager()
    
    # 3. Inisialisasi UI
    ui.cleanup_vehicle_images()
    main_widget = ui.show_ui()
    
    # 4. Inisialisasi Controller
    controller = ParkingController(
        modbus=modbus,
        printer=printer,
        emoney=emoney,
        rfid=rfid,
        oled=oled,
        api=api,
        offline=offline,
        ui_manager=ui
    )
    
    # 5. Jalankan Sistem
    try:
        controller.start()
        print("✅ Sistem berjalan. Tekan Ctrl+C untuk berhenti.")
        # Render UI loop (blocking)
        ui.app.exec_()
    except KeyboardInterrupt:
        print("\n🛑 Shutdown...")
    finally:
        controller.stop()

if __name__ == "__main__":
    main()
