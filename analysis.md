# 🛠️ Panduan Refactoring dan Solusi Arsitektur Sistem "Parking In"

Dokumen ini adalah panduan teknis yang disusun untuk Junior Programmer atau Model AI dalam melakukan **Refactoring (Penulisan Ulang)** sistem `parking-in`. 
**Aturan Utama**: JANGAN MENGUBAH FUNGSIONALITAS BISNIS (perilaku gerbang, integrasi Modbus, RFID, EMoney, UI, Mode Offline). Fokus pada peningkatan struktur kode, stabilitas, dan skalabilitas.

---

## 💡 Bagian 1: Solusi & *Best Practices* (Menjawab Kekurangan Sistem Saat Ini)

Berdasarkan hasil analisa sebelumnya, berikut adalah perbaikan arsitektur yang akan diterapkan:

1. **Pemecahan Arsitektur Monolitik (Modularisasi)**
   - **Masalah**: `main.py` terlalu besar dan menangani logika UI, Modbus, API, dan hardware sekaligus.
   - **Solusi**: Terapkan konsep *Separation of Concerns* (OOP). Pisahkan sistem ke dalam modul-modul independen (contoh: folder `devices/` untuk mengurus koneksi hardware, `services/` untuk komunikasi HTTP/API, dan `core/` untuk logika utama).

2. **Penggantian Variabel Global menjadi *State Machine* (FSM)**
   - **Masalah**: Penggunaan variabel global seperti `is_busy`, `vehicle_detected`, dan `lock` rentan menyebabkan kode macet (*race conditions*).
   - **Solusi**: Bungkus *state* sistem di dalam sebuah *Class* (misal: `ParkingController`). Pengaturan pergantian *state* hanya boleh dilakukan oleh fungsi *setter* berproteksi mutex di dalam kelas tersebut.

3. **Penanganan *Error & Reconnection* yang Lebih Elegan**
   - **Masalah**: Kegagalan pembacaan serial menyebabkan *spam* log atau program macet sementara.
   - **Solusi**: Implementasikan pola *Exponential Backoff* pada koneksi serial/modbus. Jika kabel dicabut, perangkat mencoba menghubungkan ulang dengan jeda (delay) yang bertahap, bukan di-spam secara brutal.

4. **Isolasi Logika Sinkronisasi Offline**
   - **Solusi**: Bungkus logika "menulis ke file `ticket-offline.txt`" ke dalam satu class terpisah (misal `OfflineStorage`). Meskipun fungsionalitas belum berubah (tetap menulis ke text file), ini memudahkan jika di masa depan kita ingin menggantinya menjadi database SQLite tanpa merombak logika di `main.py`.

---

## 🏗️ Bagian 2: Tahapan Implementasi Refactoring

Kerjakan langkah-langkah di bawah ini secara bertahap. Pastikan *testing* dilakukan setiap kali satu Fase diselesaikan. File utama baru yang akan kita bangun adalah **`parking.py`**.

### Fase 1: Restrukturisasi Direktori dan Persiapan
1. Biarkan file lama (`main.py`) tetap ada sebagai referensi.
2. Buat struktur folder baru sebagai berikut:
   ```text
   /core/          # Logika pengatur state & threading
   /devices/       # Abstraksi koneksi hardware (Serial, Modbus, Printer)
   /services/      # Logika panggilan API (API Validasi)
   parking.py      # Entry point aplikasi (Skrip Utama Baru)
   ```

### Fase 2: Ekstraksi Modul Hardware (`/devices`)
Pindahkan logika terkait hardware dari `main.py` menjadi kelas berorientasi objek (OOP):
1. **`devices/modbus_manager.py`**:
   - Buat `class ModbusManager`.
   - Pindahkan fungsi `connect()`, `disconnect()`, baca register (Loop Sensor & Tombol), dan `write_coil()` ke dalam kelas ini.
2. **`devices/emoney_reader.py` & `devices/rfid_reader.py`**:
   - Buat kelas untuk membungkus `serial.Serial()`.
   - Enkapsulasi fungsi pemrosesan heksadesimal (`process_emoney_data`, kalkulasi LRC) di dalam kelas E-Money.
   - Sertakan kemampuan `auto_reconnect` jika perangkat putus/hilang.
3. **`devices/printer_manager.py`**:
   - Buat kelas `PrinterManager` yang menangani inisialisasi `escpos.printer.Usb` dan membungkus logika `print_ticket_layout()`.

### Fase 3: Ekstraksi Layanan Transaksi (`/services`)
Rapikan file `transaction.py`:
1. Buat **`services/api_client.py`**:
   - Buat `class ApiClient` yang berisi *method* seperti `validate_ticket()`, `validate_emoney()`, `validate_rfid()`.
   - Gunakan kelas ini untuk menampung seluruh proses request HTTP dan *Error handling* (Timeout).
2. Buat **`services/offline_manager.py`**:
   - Buat kelas untuk mengelola penyimpanan lokal (seperti `save_to_txt()` atau baca `ticket_data.json`).

### Fase 4: Pembangunan *State Manager* (`/core/controller.py`)
Ini adalah "Otak" sistem yang menggantikan fungsi-fungsi di `main.py`.
1. Buat **`class ParkingController`**.
2. Deklarasikan parameter *state* di dalam method `__init__`:
   ```python
   self.vehicle_detected = False
   self.is_busy = False
   self.lock = threading.Lock()
   ```
3. Pindahkan *event-loop* (seperti `process_inputs_loop`, `emoney_loop`, `rfid_loop`) ke dalam kelas ini sebagai *method*.
4. Gunakan prinsip **Dependency Injection**: Pada saat membuat objek `ParkingController`, masukkan modul Modbus, API Client, dan UI Manager yang sudah dibuat di Fase 2 & 3.

### Fase 5: Penulisan Entry Point Baru (`parking.py`)
Fokus pada file `parking.py`. File ini hanya akan bertugas sebagai "Penghubung" komponen dan memulai aplikasi.
1. Baca dan muat konfigurasi (`config.py`).
2. Lakukan inisialisasi semua hardware:
   ```python
   modbus = ModbusManager(host, port)
   printer = PrinterManager(vendor_id, product_id)
   api_client = ApiClient(server_url)
   ```
3. Inisialisasi UI (mengambil dari `ui.py` yang lama).
4. Buat instansiasi dari `ParkingController` dan serahkan komponen-komponen di atas.
5. Panggil fungsi `.start()` pada `ParkingController` (yang akan otomatis menjalankan `threading` bagi RFID, Emoney, dan Modbus).
6. Jalankan Qt Event Loop untuk me-render UI secara berkelanjutan (`app.exec_()`).

### Fase 6: Uji Coba Transisi (*Regression Testing*)
- Pastikan **Fungsi Tetap Sama**: 
  1. Apakah mobil mendeteksi *loop sensor*? (Modbus Read)
  2. Apakah UI berpindah mode dengan benar?
  3. Apakah palang gerbang terbuka saat E-money sukses? (Modbus Write)
  4. Apakah mode cetak tiket Offline bekerja?
- Jika uji coba berhasil, `main.py` yang lama bisa dihapus, lalu aplikasi di-*deploy* ulang dengan sistem kode yang baru dan lebih rapi.
