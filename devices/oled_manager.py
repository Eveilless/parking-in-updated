import os
import socket
from PIL import Image, ImageDraw, ImageFont

class OledManager:
    def __init__(self):
        self.device = None
        self.is_luma = False
        self.ip_address = self._get_ip_address()
        self.current_lines = ["", "", ""]
        
        try:
            # Mencoba library luma.oled (Modern)
            from luma.core.interface.serial import i2c
            from luma.oled.device import ssd1306
            serial = i2c(port=1, address=0x3C)
            self.device = ssd1306(serial)
            self.is_luma = True
            print("[OLED] Berhasil inisialisasi menggunakan luma.oled")
        except Exception as e_luma:
            try:
                # Fallback ke library lawas Adafruit_SSD1306
                import Adafruit_SSD1306
                self.device = Adafruit_SSD1306.SSD1306_128_64(rst=None)
                self.device.begin()
                self.device.clear()
                self.device.display()
                print("[OLED] Berhasil inisialisasi menggunakan Adafruit_SSD1306")
            except Exception as e_adafruit:
                print(f"[OLED] Tidak mendeteksi library OLED. (luma: {e_luma}) (adafruit: {e_adafruit})")
                self.device = None
            
        try:
            self.font = ImageFont.load_default()
        except:
            self.font = None

        # Tampilkan status awal
        self._update_display()

    def _get_ip_address(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def print_message(self, message):
        """Mencetak pesan ke baris 2-4 OLED dengan efek scrolling"""
        # Potong pesan jika terlalu panjang (layar OLED 128x64 dengan font default muat ~21 karakter per baris)
        max_chars = 21
        new_lines = [message[i:i+max_chars] for i in range(0, len(message), max_chars)]
        
        for line in new_lines:
            self.current_lines.append(line)
            
        # Simpan maksimal 3 baris teks log (baris ke-2 s/d 4)
        if len(self.current_lines) > 3:
            self.current_lines = self.current_lines[-3:]
            
        self._update_display()

    def _update_display(self):
        if not self.device:
            return
            
        width = 128
        height = 64
        image = Image.new('1', (width, height))
        draw = ImageDraw.Draw(image)
        
        # Baris 1: IP Address
        draw.text((0, 0), f"IP: {self.ip_address}", font=self.font, fill=255)
        
        # Garis pemisah Header
        draw.line((0, 12, width, 12), fill=255)
        
        # Baris 2 - 4: Isi Pesan
        y = 16
        for line in self.current_lines:
            draw.text((0, y), line, font=self.font, fill=255)
            y += 14
            
        try:
            if self.is_luma:
                self.device.display(image)
            else:
                self.device.image(image)
                self.device.display()
        except Exception as e:
            print(f"[OLED] Gagal update layar: {e}")
