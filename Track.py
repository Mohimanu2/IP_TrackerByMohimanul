import requests
import datetime
import os
import time
from flask import Flask, request, render_template_string
from threading import Thread
import subprocess

app = Flask(__name__)
HTML_PAGE = """
<!doctype html>
<html><head><title>Welcome</title></head>
<body><h2>Thanks for visiting</h2><p>Your IP has been logged.</p></body>
</html>
"""

def banner():
    print("\033[92m" + """
╔════════════════════════════════════════════════╗
║              Made by Mohimanul-TVM             ║
╚════════════════════════════════════════════════╝
""" + "\033[0m")

def get_location(ip):
    try:
        res = requests.get(f"http://ip-api.com/json/{ip}", timeout=5)
        data = res.json()
        if data["status"] == "success":
            return {
                "IP": ip,
                "City": data.get("city"),
                "Region": data.get("regionName"),
                "Country": data.get("country"),
                "Latitude": data.get("lat"),
                "Longitude": data.get("lon"),
                "ISP": data.get("isp"),
                "Map": f"https://www.google.com/maps?q={data.get('lat')},{data.get('lon')}",
                "Time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
    except Exception as e:
        return {"IP": ip, "Error": str(e)}
    return {"IP": ip, "Error": "Unknown error"}

@app.route('/')
def index():
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    info = get_location(ip)
    print("\n\033[96m--- New Visitor ---\033[0m")
    for k, v in info.items():
        print(f"{k}: {v}")
    print("\033[96m-------------------\033[0m\n")
    return render_template_string(HTML_PAGE)

def start_ngrok():
    token = input("Enter your Ngrok Authtoken: ").strip()
    os.system(f"./ngrok authtoken {token}")
    print("\n\033[93m[•] Starting Ngrok tunnel on port 5000...\033[0m")
    subprocess.Popen(["./ngrok", "http", "5000"])
    time.sleep(3)
    try:
        url = requests.get("http://localhost:4040/api/tunnels").json()['tunnels'][0]['public_url']
        print(f"\n\033[92m[✓] Share this link: {url}\033[0m\n")
    except:
        print("\033[91m[✗] Failed to get ngrok public URL.\033[0m")

def generate_link():
    if not os.path.isfile("ngrok"):
        print("\033[93m[•] Downloading Ngrok...\033[0m")
        os.system("wget https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-linux-arm.zip")
        os.system("unzip ngrok-stable-linux-arm.zip && rm ngrok-stable-linux-arm.zip")
        os.system("chmod +x ngrok")
    Thread(target=start_ngrok).start()
    app.run(host="0.0.0.0", port=5000)

def ip_lookup():
    ip = input("Enter target IP address: ").strip()
    data = get_location(ip)
    print("\n\033[96m--- IP Info ---\033[0m")
    for k, v in data.items():
        print(f"{k}: {v}")
    print("\033[96m----------------\033[0m")

def menu():
    banner()
    while True:
        print("\n\033[93m[1]\033[0m Track location using IP")
        print("\033[93m[2]\033[0m Generate link & capture visitor IP")
        print("\033[93m[0]\033[0m Exit")
        choice = input("Select an option: ").strip()
        if choice == '1':
            ip_lookup()
        elif choice == '2':
            generate_link()
        elif choice == '0':
            print("Exiting...")
            break
        else:
            print("Invalid option.")

if __name__ == '__main__':
    menu()
