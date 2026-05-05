# 🚀 Tugas Implementasi: Sistem "Parking In" (Entry Gate)

## 📊 Bagian 1: Hasil Analisa Proyek Saat Ini
Berdasarkan analisa pada sistem `parking-in` yang ada, proyek ini adalah aplikasi Desktop/IoT berbasis Python yang berfungsi sebagai pengontrol gerbang masuk parkir otomatis (Entry Gate). Sistem ini terhubung dengan berbagai hardware dan server backend.

### Komponen Utama:
1. **Bahasa & Framework**: Python 3, PyQt5 (untuk GUI), `pymodbus` (kontrol I/O via Modbus TCP), `pyserial` (pembacaan E-Money & RFID), `python-escpos` (printer termal), `requests` (API HTTP server).
2. **Hardware yang Didukung**:
   - **Modbus I/O Module**: Untuk membaca input Loop Sensor (deteksi kendaraan), Tombol Tiket, dan mengontrol output Relay Barrier Gate (palang pintu).
   - **Serial Readers**: Pembaca kartu E-Money (Mandiri, Flazz, Brizzi, Tapcash) dan pembaca RFID.
   - **Printer Termal USB**: Epson TM-T88III (atau printer thermal USB kompatibel) untuk mencetak struk parkir.
   - **Kamera (IPCam & LPR)**: Mengambil foto kendaraan dan membaca plat nomor kendaraan (LPR) yang gambarnya disimpan sementara di direktori lokal (`lpr.txt`, folder `ipcam`, dan folder `lpr`).
3. **Alur Kerja (Workflow)**:
   - Sistem *standby* (Welcome Screen di UI) menunggu *Loop Sensor* mendeteksi kendaraan di depan gerbang.
   - Jika kendaraan masuk/menginjak sensor, sistem memainkan suara sambutan (opsional) dan merubah UI untuk meminta tap kartu atau menekan tombol tiket.
   - **Metode Masuk 1 (Tombol Tiket)**: Sistem akan memvalidasi ke server (Online), memprint tiket (barcode/QR), dan membuka palang. Jika server mati/terputus (Offline), sistem akan men-generate tiket offline, menyimpannya di `ticket-offline.txt`, memprint tiket, lalu membuka palang.
   - **Metode Masuk 2 (E-Money)**: Sistem membaca UID & detail kartu dari port Serial, memvalidasi data ke server, melakukan pemotongan saldo (jika dikonfigurasi), dan membuka palang.
   - **Metode Masuk 3 (RFID)**: Sistem membaca tag RFID, memvalidasi aksesnya ke server, dan membuka palang.
   - Setelah kendaraan pergi (Loop sensor mati), UI kembali ke status siap dan palang ditutup kembali (diturunkan).
4. **Keamanan & Konkurensi**: Menggunakan `threading` dan `Lock` (Mutex) di Python untuk memastikan tidak ada bentrokan atau *race condition* antara proses pembacaan I/O sensor, RFID, dan E-Money yang berjalan secara simultan.

---

## 🛠️ Bagian 2: Tahapan Implementasi (Panduan untuk Junior Programmer / AI)

Dokumen ini adalah instruksi langkah demi langkah untuk membangun ulang, menstandarisasi, atau melanjutkan pengembangan proyek ini. Kerjakan setiap fase secara berurutan.

### Fase 1: Setup Proyek & Struktur Dasar
1. **Inisialisasi Proyek**:
   - Buat direktori aplikasi dan jalankan inisiasi *virtual environment* Python (`python -m venv venv`).
   - Buat file `requirements.txt` dan isi dependensi utama: `PyQt5`, `pymodbus`, `pyserial`, `python-escpos`, `requests`, `python-dotenv`, `psutil`, `pytz`.
   - Jalankan instalasi dependensi (`pip install -r requirements.txt`).
2. **Pembuatan Struktur Direktori**:
   - Buat folder `assets/` (untuk aset UI: background, logo, dll).
   - Buat folder `handlers/` (untuk merapikan handler spesifik seperti Oled atau Audio jika ada).
   - Buat folder sementara `ipcam/` dan `lpr/` untuk menampung gambar *snapshot* kamera lokal.
3. **Konfigurasi Lingkungan (`config.py`)**:
   - Buat file `.env` sebagai tempat menyimpan kredensial dan konfigurasi (contoh: URL Server, endpoint API, COM port, alamat Modbus, id device printer).
   - Buat `config.py` yang berisi fungsi `load_config()` untuk membaca nilai dari file `.env` (menggunakan `os.getenv`) dan menampungnya ke dalam variabel global agar mudah diakses file lain.

### Fase 2: Implementasi Modul API & Transaksi (`transaction.py`)
1. **Fungsi API Validation**:
   - Buat fungsi `validate_ticket()`, `validate_emoney()`, dan `validate_rfid()`.
   - Gunakan pustaka `requests` untuk melakukan `POST` request payload JSON ke *backend* server.
   - Wajib berikan batas waktu permintaan (`timeout=15`) dan penanganan `try-except` agar aplikasi bisa merespons (misal beralih ke Mode Offline) jika server sedang bermasalah.
2. **Logika E-Money Deduction (Pengurangan Saldo)**:
   - Buat fungsi `process_deduction()` dan `deduct()` yang bertugas mengirimkan *command array byte/hexadecimal* (seperti `EF0103...`) via Serial ke perangkat *reader* fisik E-Money.
   - Buat fungsi kalkulasi verifikasi byte (`calculate_lrc()`) untuk memastikan integritas komunikasi data (XOR dari nilai byte) ke mesin pembaca E-money.

### Fase 3: Pembangunan User Interface / GUI (`ui.py`)
1. **Konfigurasi Frame Dasar**:
   - Menggunakan PyQt5, buat kelas `CustomWidget(QWidget)` dan set metode *rendering* untuk berjalan secara Layar Penuh (`showFullScreen()`).
   - Sembunyikan kursor dari layar dengan `setCursor(Qt.BlankCursor)`.
2. **Pembuatan Mode Tampilan**:
   - **Mode Welcome**: Gunakan `QPainter` (paintEvent) untuk menggambar UI yang terbagi menjadi 3 baris: Header (Tanggal & Jam), Content Area (Background & Instruksi), dan Footer.
   - **Mode Payment**: Modifikasi layarnya untuk menampilkan struktur *Grid/Split* di bagian tengah. Sisi kiri menampilkan "Detail Tiket / Data Parkir" (nomor, tarif, jenis pembayaran). Sisi kanan memuat foto *snapshot* dari CCTV (`ipcam/`) dan LPR (`lpr/`).
3. **Interval Pembaruan Layar (Timer)**:
   - Daftarkan `QTimer` yang secara konstan memicu fungsi `.update()` (misal: tiap 30 ms) agar jam di UI bisa berjalan dan perubahan state gambar selalu di-*render* instan.

### Fase 4: Integrasi Modbus I/O & Hardware Printer
1. **Komunikasi I/O Modbus (`main.py`)**:
   - Konfigurasi objek `ModbusTcpClient` (`pymodbus`).
   - Tetapkan konstanta `SLAVE_ID`, `COIL_ADDRESS`, dsb berdasarkan spesifikasi panel relay.
   - Siapkan utilitas `write_coil(address, state)` untuk menyalakan/mematikan alat (seperti *Barrier Gate*).
2. **Mesin Printer Thermal**:
   - Gunakan metode `Usb()` dari `escpos.printer`. Parameter ID Vendor dan ID Produk diambil dari file konfigurasi.
   - Implementasikan fungsi format cetakan `_print_ticket_layout()`. Gunakan perintah `text()` dengan berbagai ukuran (align center, bold), tambahkan fungsi generasikan *QR Code* (`qr()`), dan akhiri dengan perintah potong otomatis (`cut()`).

### Fase 5: Implementasi *Multi-Threading* & *Event Looping*
Sistem ini menggunakan struktur asinkron primitif berbasis Threads. Buat fungsi fungsi *looping* berikut lalu panggil menggunakan `threading.Thread(target=..., daemon=True).start()`:
1. **Loop Modbus (Pembacaan Input Sensor)**:
   - Mengambil status register `count=8` setiap 0.5 detik.
   - Jika `Loop Sensor 1` = menyala, perbarui state `vehicle_detected = True`, tampilkan pesan di GUI, serta reset *buffer* Serial.
   - Jika mendeteksi transisi sinyal pada register `Tombol Tiket` (dari 0 ke 1) DAN `vehicle_detected` aktif: Jalankan fungsi `handle_print_ticket`. Validasi ke server, print tiket, lalu buka palang.
2. **Loop Pembacaan RFID & E-Money**:
   - Dua *loop thread* terpisah (`rfid_loop` dan `emoney_loop`) yang secara persisten memantau port Serial `.readline()`.
   - Gunakan mekanisme *reconnect* otomatis (`try-except` SerialException) agar apabila kabel USB reader tercabut, program tidak mogok dan akan mencoba koneksi ulang.
   - Jika terdapat bacaan masuk saat mobil terdeteksi, lakukan pemrosesan LRC/Hex, validasi API, pemotongan, buka gerbang, dan ubah status tampilan GUI ke "Sukses".
3. **Pengelolaan State dengan Mutex**:
   - Daftarkan `lock = threading.Lock()`.
   - Gunakan instruksi `with lock:` setiap kali mengakses objek Modbus I/O atau memanipulasi bendera state kritikal (seperti *flag* boolean `is_busy` agar sistem tidak memproses input kartu jika sedang sibuk memprint tiket).

### Fase 6: Penanganan Kondisi Offline & Pembersihan (Clean-up)
1. **Mode Fallback (Offline)**:
   - Pada metode cetak tiket, ketika validasi `validate_ticket` *fail*, susun dictionary data secara manual di sisi lokal dengan kode tiket menggunakan UNIX timestamp (contoh: `PRK171...`). Simpan baris tersebut ke `ticket-offline.txt` (untuk nantinya di-sync). Tetap print tiket dan buka palang.
2. **Reset Kedatangan (Vehicle Departure)**:
   - Ketika kendaraan maju masuk area parkir dan melepaskan injakan pada `Loop Sensor` (kembali ke nilai 0).
   - Tutup *Barrier Gate* dengan `write_coil(False)`.
   - Jalankan rutinitas `cleanup_vehicle_images()` untuk menghapus secara fisik gambar plat/kamera di direktori lokal.
   - Kembalikan GUI ke mode "Welcome" dan bebaskan *flag* `is_busy`.

### Fase 7: Testing dan Deployment
1. **Penyediaan Mock/Simulasi**:
   - Jika tidak ada hardware fisik di fase *Development*, gunakan *Modbus Server Simulator* (contoh: ModRSsim2, PyModbus Server) dan buat skrip kecil untuk mengirim string acak ke Virtual COM Port (menstimulasikan input RFID).
2. **Deployment Lingkungan Produksi**:
   - (Diasumsikan berjalan di *Raspberry Pi* / Mini PC Linux): Pastikan direktori *mount* USB valid.
   - Buat *Service Systemd* (`parking-in.service`) yang memuat *path environment* Python yang benar serta mengalokasikan memori/log agar aplikasi selalu otomatis *restart* saat perangkat dinyalakan.
