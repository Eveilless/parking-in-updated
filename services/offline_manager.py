import os
import json
import time

class OfflineManager:
    @staticmethod
    def get_plate():
        plate = ""
        if os.path.exists("lpr.txt"):
            try:
                with open("lpr.txt", "r") as f:
                    lines = f.readlines()
                    if len(lines) >= 1:
                        plate = lines[0].strip()
            except Exception as e:
                print(f"[OfflineManager] Error reading plate: {e}")
        return plate

    @staticmethod
    def save_transaction(ticket_data):
        try:
            filename = "ticket_data.json"
            with open(filename, "w") as f:
                json.dump(ticket_data, f)
                
            nameCSV = str(ticket_data.get('ticket_code')) + ".tyto"
            with open(nameCSV, 'w') as f:
                f.write(ticket_data.get('ticket_code') + "\n")
            return True
        except Exception as e:
            print(f"[OfflineManager] Failed to write JSON: {e}")
            return False

    @staticmethod
    def generate_offline_ticket(type_vehicle, plate):
        now = time.time()
        from datetime import datetime
        ticket_time = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        ticket_code = f"{type_vehicle}&PRK{int(now)}"
        
        ticket_data = {
            "ticket_code": ticket_code,
            "device_name": type_vehicle,
            "start_time": ticket_time,
            "plat": plate,
            "status": "Offline"
        }
        
        try:
            with open("ticket-offline.txt", "a") as f:
                f.write(ticket_code + "\n")
        except Exception as e:
            print(f"[OfflineManager] Failed to write offline txt: {e}")
            
        return ticket_data
