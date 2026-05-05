import os
import requests
import json

class ApiClient:
    def __init__(self):
        self.server_url = os.getenv("SERVER", "")
        self.timeout = 15

    def validate_ticket(self, type_vehicle, plate):
        url = self.server_url + os.getenv("VALIDATE_TICKET", "")
        try:
            headers = {'Content-Type': 'application/json'}
            response = requests.post(
                url, 
                json={"iddev": type_vehicle, "plate": plate}, 
                headers=headers, 
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            if data.get("status") == "success":
                return True, data.get("transaction", {})
            return False, "Ticket tidak valid"
        except Exception as e:
            print(f"[API] Error validating ticket: {e}")
            return False, "Error komunikasi API"

    def validate_rfid(self, rfid_data, type_vehicle):
        url = self.server_url + os.getenv("VALIDATE_RFID", "")
        try:
            headers = {'Content-Type': 'application/json'}
            response = requests.post(
                url,
                json={"rfid": rfid_data, "iddev": type_vehicle},
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            if data.get("status") == "open":
                return True, data.get("transaction", {})
            else:
                return False, data.get("message", "Transaction not valid")
        except Exception as e:
            print(f"[API] Error validating RFID: {e}")
            return False, "Error komunikasi API"

    def validate_emoney(self, card_number, card_name, plate, type_vehicle):
        url = self.server_url + os.getenv("VALIDATE_EMONEY", "")
        try:
            headers = {'Content-Type': 'application/json'}
            response = requests.post(
                url,
                json={
                    "iddev": type_vehicle,
                    "card_number": card_number,
                    "card_type": card_name,
                    "plate": plate
                },
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            if data.get("status") == "success":
                return True, data.get("message"), data.get("transaction")
            return False, "Transaksi tidak valid", None
        except Exception as e:
            print(f"[API] Error checking e-money transaction: {e}")
            return False, "Error komunikasi dengan server", None
