import os
from escpos.printer import Usb

class PrinterManager:
    def __init__(self):
        vendor_str = os.getenv('PRINTER_VENDOR')
        product_str = os.getenv('PRINTER_PRODUCT')
        
        try:
            self.vendor_id = int(vendor_str, 16) if vendor_str else None
            self.product_id = int(product_str, 16) if product_str else None
        except (ValueError, TypeError):
            self.vendor_id = None
            self.product_id = None

    def _get_printer(self):
        try:
            if self.vendor_id and self.product_id:
                printer = Usb(
                    self.vendor_id,
                    self.product_id,
                    timeout=5000,
                    profile="TM-T88III"
                )
                printer.open()
                return printer
        except Exception as e:
            print(f"[Printer] Initialization error: {e}")
            
        try:
            printer = Usb(0x0483, 0x5743, timeout=5000, profile="TM-T88III")
            printer.open()
            return printer
        except Exception as e:
            print(f"[Printer] Fallback initialization error: {e}")
            return None

    def print_ticket(self, data):
        printer = self._get_printer()
        if not printer:
            print("[Printer] Gagal Inisialisasi Printer. Transaksi tetap lanjut.")
            return False

        # Selalu usahakan baca plat terbaru dari lpr.txt saat mencetak
        plate = data.get('plat', '')
        try:
            if os.path.exists("lpr.txt"):
                with open("lpr.txt", "r") as f:
                    lines = f.readlines()
                    if lines and lines[0].strip():
                        plate = lines[0].strip()
        except Exception as e:
            print(f"[Printer] Gagal membaca lpr.txt: {e}")

        try:
            printer.set(align='center', bold=True, width=2, height=2)
            printer.text("TIKET MASUK\n\n")

            printer.set(align='left', bold=True, width=1, height=1)
            printer.text(f"{os.getenv('LABEL_UP', '')}\n\n")

            printer.set(align='left', bold=False, width=1, height=1)
            text = (
                f"{'ID':13}: {data.get('ticket_code', '')}\n"
                f"{'Pintu':13}: {data.get('device_name', '')}\n"
                f"{'Waktu Masuk':13}: {data.get('start_time', '')}\n"
                f"{'Plat Nomor':13}: {plate}\n"
                f"{'Status':13}: {data.get('status', '')}\n"
            )
            printer.text(text)

            printer.set(align='center')
            printer.qr(str(data.get('ticket_code', '')), size=8)
            printer.text("\n\n")

            printer.set(align='center', bold=False)
            printer.text(f"{os.getenv('LABEL_CENTER', '')}\n")
            printer.text(f"{os.getenv('LABEL_DOWN', '')}\n\n")

            printer.cut()
            return True
        except Exception as e:
            print(f"[Printer] Gagal print tiket: {e}")
            return False
        finally:
            printer.close()
