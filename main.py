import os
import random
import string
import subprocess
import json
import requests
import time
import shutil
import ipaddress

def generate_random_string(length):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def generate_strong_password(length=20):
    special_characters = "!@#$%^&*()-+="
    
    lower = random.choice(string.ascii_lowercase)
    upper = random.choice(string.ascii_uppercase)
    digit = random.choice(string.digits)
    special = random.choice(special_characters)

    remaining = ''.join(random.choices(string.ascii_letters + string.digits + special_characters, k=length-4))

    password = lower + upper + digit + special + remaining
    password = ''.join(random.sample(password, len(password)))  # Mieszamy znaki
    
    return password

def get_azure_subscription_id():
    az_cmd = "az.cmd" if os.name == "nt" else "az"  
    try:
        result = subprocess.run([az_cmd, "account", "show", "--query", "id", "-o", "tsv"], 
                                capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        print("[!] Błąd: Nie jesteś zalogowany do Azure CLI.")
        print("[!] Wykonaj w terminalu: `az login` i spróbuj ponownie.")
        exit(1)

def get_public_ip():
    try:
        ip_response = requests.get("https://api64.ipify.org?format=json", timeout=5)
        user_ip = ip_response.json()["ip"]
        if isinstance(ipaddress.ip_address(user_ip), ipaddress.IPv4Address):
            return user_ip
        else:
            print("[!] Wykryto IPv6! Wymagane jest IPv4.")
            return input("[?] Wpisz swój adres IPv4 ręcznie: ")
    except requests.exceptions.RequestException:
        return input("[!] Nie można pobrać twojego IP. Wpisz je ręcznie: ")

def remove_directory(path):
    for _ in range(5): 
        try:
            shutil.rmtree(path, ignore_errors=True)
            if not os.path.exists(path):
                break
        except Exception as e:
            print(f"[-] Błąd podczas usuwania {path}: {e}")
            time.sleep(1)

subscription_id = get_azure_subscription_id()
session_id = generate_random_string(6)
username = generate_random_string(8)
password = generate_strong_password(20)  
user_ip = get_public_ip()

terraform_dir = os.path.join(os.getcwd(), f"terraform_session_{session_id}")
os.makedirs(terraform_dir, exist_ok=True)

terraform_cmd = "terraform.exe" if os.name == "nt" else "terraform"

terraform_template_dir = os.path.join(os.getcwd(), "terraform")
for file_name in ["main.tf", "variables.tf", "outputs.tf"]:
    src_path = os.path.join(terraform_template_dir, file_name)
    dst_path = os.path.join(terraform_dir, file_name)
    shutil.copy(src_path, dst_path)

tfvars_content = f"""
session_id = "{session_id}"
admin_username = "{username}"
admin_password = "{password}"
user_ip = "{user_ip}"
subscription_id = "{subscription_id}"
"""

with open(os.path.join(terraform_dir, "terraform.tfvars"), "w") as f:
    f.write(tfvars_content)

print("\n[+] Pobrano subscription_id:", subscription_id)

subprocess.run([terraform_cmd, "init"], cwd=terraform_dir)
subprocess.run([terraform_cmd, "apply", "-auto-approve"], cwd=terraform_dir)

output = subprocess.run([terraform_cmd, "output", "-json"], cwd=terraform_dir, capture_output=True, text=True)

try:
    output_json = json.loads(output.stdout)
    vm_ip = output_json["vm_ip"]["value"]
except (json.JSONDecodeError, KeyError):
    print("[-] Błąd: Nie udało się pobrać IP maszyny.")
    vm_ip = "Nieznane"

print(f"\n[+] Maszyna wirtualna dla sesji {session_id} została utworzona!")
print(f"[+] Login: {username}")
print(f"[+] Hasło: {password}")
print(f"[+] Adres IP: {vm_ip}")

while True:
    decision = input("\n[?] Zakończyć sesję? (tak/nie): ").strip().lower()

    if decision == "tak":
        print("[+] Usuwanie maszyny...")
        subprocess.run([terraform_cmd, "destroy", "-auto-approve"], cwd=terraform_dir)
        remove_directory(terraform_dir)
        print(f"[+] Maszyna dla sesji {session_id} została usunięta.")
        break

    elif decision == "nie":
        print("[+] Sesja nadal działa. Zapytam ponownie później.")

    else:
        print("[-] Niepoprawna opcja. Wpisz 'tak' lub 'nie'.")
