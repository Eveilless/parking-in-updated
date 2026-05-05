import serial
import time
import sys
import os

# --- Konfigurasi ---
PORT = '/dev/ttyACM0'
BAUDRATE = 9600
TIMEOUT = 1
OUTPUT_FILE = 'lpr.txt'  # Nama file output

def write_to_file(plate_str):
    """
    Fungsi untuk menulis teks pelat nomor ke dalam file.
    Mode 'w' (write) digunakan agar isi file selalu tertimpa.
    """
    try:
        # Menggunakan mode 'w' akan menghapus isi lama dan menimpa dengan yang baru
        with open(OUTPUT_FILE, 'w') as f:
            f.write(plate_str)
        print(f"[FILE DISIMPAN] '{plate_str}' telah ditulis ke {OUTPUT_FILE}")
    except IOError as e:
        print(f"[ERROR IO] Gagal menulis ke file: {e}")

def parse_lpr_data(buffer):
    """
    Fungsi untuk memotong buffer data yang masuk sesuai dengan 
    protokol Hex: Header [bb 88 aa] dengan panjang total 32 byte.
    """
    detected_plates = []
    
    while True:
        # Mencari posisi header
        header_idx = buffer.find(b'\xbb\x88\xaa')
        
        if header_idx == -1:
            break
            
        # Pastikan panjang buffer cukup untuk 1 paket (32 byte)
        if len(buffer) < header_idx + 32:
            break 
            
        # Potong 1 paket utuh
        packet = buffer[header_idx : header_idx + 32]
        
        # Ekstrak data pelat
        plate_bytes = packet[6:22]
        
        # Bersihkan karakter Null dan decode ke string
        plate_str = plate_bytes.split(b'\x00')[0].decode('ascii', errors='ignore').strip()
        
        # Validasi ringan: abaikan hasil jika kosong atau terlalu pendek
        if plate_str and len(plate_str) > 2:
            detected_plates.append(plate_str)
            
        # Potong buffer untuk memproses paket selanjutnya (jika ada tumpukan data)
        buffer = buffer[header_idx + 32:]
        
    return detected_plates, buffer

def main():
    # Buat file kosong di awal jika belum ada
    if not os.path.exists(OUTPUT_FILE):
        open(OUTPUT_FILE, 'w').close()
        
    try:
        print(f"[*] Membuka {PORT} pada baudrate {BAUDRATE}...")
        ser = serial.Serial(
            port=PORT,
            baudrate=BAUDRATE,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=TIMEOUT
        )
        time.sleep(1)
        
        if ser.is_open:
            print(f"[+] Port terbuka! Menunggu data pelat...\n")
            print(f"[*] File output: {os.path.abspath(OUTPUT_FILE)}")
            print("-" * 50)
            
            data_buffer = b''
            
            while True:
                if ser.in_waiting > 0:
                    raw_bytes = ser.read(ser.in_waiting)
                    data_buffer += raw_bytes
                    
                    plates, data_buffer = parse_lpr_data(data_buffer)
                    
                    for plate in plates:
                        print(f"[PLAT DETEKSI] -> {plate}")
                        # Panggil fungsi penulisan file setiap ada pelat
                        write_to_file(plate)
                
                time.sleep(0.05)

    except serial.SerialException as e:
        print(f"\n[ERROR] Port terputus.\nDetail: {e}")
    except KeyboardInterrupt:
        print("\n\n[*] Program dihentikan.")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()

if __name__ == '__main__':
    main()