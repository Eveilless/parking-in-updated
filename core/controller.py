import threading
import time
import os

class ParkingController:
    def __init__(self, modbus, printer, emoney, rfid, oled, api, offline, ui_manager):
        self.modbus = modbus
        self.printer = printer
        self.emoney = emoney
        self.rfid = rfid
        self.oled = oled
        self.api = api
        self.offline = offline
        self.ui = ui_manager
        
        self.running = False
        self.vehicle_detected = False
        self.type_vehicle = None
        self.is_busy = False
        self.lock = threading.Lock()
        
    def start(self):
        self.running = True
        self.modbus.connect()
        if self.oled:
            self.oled.print_message("Sistem Siap!")
            self.oled.print_message("Menunggu Mobil..")
        
        threading.Thread(target=self.modbus_loop, daemon=True).start()
        threading.Thread(target=self.emoney_loop, daemon=True).start()
        threading.Thread(target=self.rfid_loop, daemon=True).start()

    def stop(self):
        self.running = False
        self.modbus.disconnect()
        self.emoney.close()
        self.rfid.close()

    def modbus_loop(self):
        prev_button = None
        while self.running:
            registers = self.modbus.read_inputs()
            if registers:
                loop_one = registers[self.modbus.LOOP_ONE]
                loop_two = registers[self.modbus.LOOP_TWO]
                button_ticket = registers[self.modbus.BUTTON_TICKET]
                
                # Vehicle Detection
                if loop_one == 1: # and loop_two == 1:
                    local_type = os.getenv("IDLOOP1") if loop_two == 0 else os.getenv("IDLOOP2")
                    with self.lock:
                        if not self.vehicle_detected:
                            self.vehicle_detected = True
                            self.type_vehicle = local_type
                            self.emoney.flush()
                            self.rfid.flush()
                            if self.oled:
                                self.oled.print_message(f"Mobil Terdeteksi!")
                                self.oled.print_message(f"Tipe: {self.type_vehicle}")
                            if self.ui:
                                if hasattr(self.ui, 'main_widget') and self.ui.main_widget:
                                    self.ui.main_widget.mode = "welcome"
                                    self.ui.main_widget.update()
                                self.ui.set_welcome_text("SILAHKAN TEMPELKAN KARTU ATAU TEKAN TOMBOL TICKET")
                # elif loop_one == 1 or loop_two == 1:
                    # motor
                else:
                    if self.vehicle_detected:
                        # self.modbus.close_gate()
                        if self.is_busy:
                            if os.path.exists("ticket_data.json"): os.remove("ticket_data.json")
                            self.is_busy = False
                        self.vehicle_detected = False
                        self.type_vehicle = None
                        if self.oled:
                            self.oled.print_message("Mobil Keluar")
                            self.oled.print_message("Menunggu Mobil..")
                        if self.ui:
                            if hasattr(self.ui, 'main_widget') and self.ui.main_widget:
                                self.ui.main_widget.mode = "welcome"
                                self.ui.main_widget.update()
                            self.ui.set_welcome_text(os.getenv("WELCOME_TEXT", "SELAMAT DATANG"))
                            if hasattr(self.ui, 'cleanup_vehicle_images'):
                                self.ui.cleanup_vehicle_images()
                
                # Button Detection
                # print("[DEBUG controller] Button state: ", button_ticket, flush=True)
                if prev_button == 0 and button_ticket == 1:
                    with self.lock:
                        if not self.is_busy and self.vehicle_detected:
                            self.is_busy = True
                            threading.Thread(target=self.handle_print_ticket, args=(self.type_vehicle,), daemon=True).start()
                prev_button = button_ticket
            time.sleep(0.5)

    def wait_and_show_payment_ui(self):
        if not self.ui or not hasattr(self.ui, 'switch_to_payment_mode_with_data'):
            return
            
        import glob
        # Wait up to 5 seconds for at least one image to appear
        for _ in range(50):
            has_ipcam = len([f for f in glob.glob("ipcam/*") if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))]) > 0
            has_lpr = len([f for f in glob.glob("lpr/*") if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))]) > 0
            
            if has_ipcam or has_lpr:
                time.sleep(0.5)
                break
            time.sleep(0.1)
            
        self.ui.switch_to_payment_mode_with_data()

    def handle_print_ticket(self, vehicle_type):
        plate = self.offline.get_plate()
        success, response = self.api.validate_ticket(vehicle_type, plate)
        
        if success:
            self.offline.save_transaction(response)
            self.printer.print_ticket(response)
            self.modbus.open_gate()
            if self.oled: self.oled.print_message("Gerbang Terbuka!")
            self.wait_and_show_payment_ui()
        else:
            ticket_data = self.offline.generate_offline_ticket(vehicle_type, plate)
            if self.offline.save_transaction(ticket_data):
                self.printer.print_ticket(ticket_data)
                self.modbus.open_gate()
                if self.oled: self.oled.print_message("Gerbang Terbuka! (Offline)")
                self.wait_and_show_payment_ui()
        
        with self.lock:
            self.is_busy = False

    def emoney_loop(self):
        ALLOWED_CARDS = ["02", "03", "04", "05"]
        while self.running:
            if not self.emoney.connect():
                time.sleep(1)
                continue
            if not self.vehicle_detected:
                time.sleep(0.1)
                continue
                
            in_waiting = self.emoney.serial_conn.in_waiting if self.emoney.serial_conn else 0
            if in_waiting > 0:
                raw = self.emoney.read_bytes(in_waiting)
                if raw:
                    print(f"[Emoney Debug] Menerima data: {raw.hex().upper()}")
                    card_info = self.emoney.process_stream(raw)
                    if card_info:
                        print(f"[Emoney Debug] Kartu Valid: {card_info}")
                        with self.lock:
                            print(f"[Emoney Debug] Lock acquired. is_busy={self.is_busy}, vehicle_detected={self.vehicle_detected}")
                            if not self.is_busy and self.vehicle_detected:
                                self.is_busy = True
                                vehicle_type = self.type_vehicle
                                
                                try:
                                    print(f"[Emoney Debug] Memeriksa tipe kartu: {card_info['cardType']} in {ALLOWED_CARDS}")
                                    if card_info["cardType"] in ALLOWED_CARDS:
                                        print(f"[Emoney Debug] Memvalidasi ke API Server...")
                                        success, msg, tx = self.api.validate_emoney(
                                            card_info["cardNo"], card_info["cardType"], 
                                            self.offline.get_plate(), vehicle_type
                                        )
                                        print(f"[Emoney Debug] Hasil API: success={success}, msg={msg}")
                                        if success:
                                            print("[Emoney Debug] Transaksi Sukses! Buka gerbang.")
                                            self.modbus.open_gate()
                                            if self.oled: self.oled.print_message("Gerbang Terbuka! (Emoney)")
                                            self.offline.save_transaction(tx)
                                            self.wait_and_show_payment_ui()
                                        else:
                                            print(f"[Emoney Debug] Transaksi Gagal! Pesan: {msg}")
                                            if self.ui:
                                                self.ui.set_welcome_text(msg)
                                    else:
                                        print("[Emoney Debug] Tipe kartu tidak diizinkan.")
                                    self.emoney.flush()
                                finally:
                                    self.is_busy = False
                            else:
                                print("[Emoney Debug] Diabaikan karena sedang sibuk atau mobil belum terdeteksi penuh.")
            time.sleep(0.05)

    def rfid_loop(self):
        while self.running:
            if not self.rfid.connect(): continue
            if not self.vehicle_detected:
                time.sleep(0.1)
                continue
                
            raw = self.rfid.read_line()
            if raw and len(raw) >= 3:
                with self.lock:
                    if not self.is_busy and self.vehicle_detected:
                        self.is_busy = True
                        vehicle_type = self.type_vehicle
                        
                        try:
                            data_rfid, valid = self.rfid.parse_data(raw)
                            if valid:
                                success, tx = self.api.validate_rfid(data_rfid, vehicle_type)
                                if success:
                                    self.modbus.open_gate()
                                    if self.oled: self.oled.print_message("Gerbang Terbuka! (RFID)")
                            self.rfid.flush()
                        finally:
                            self.is_busy = False
            time.sleep(0.05)
