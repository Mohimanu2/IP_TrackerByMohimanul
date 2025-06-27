#!/usr/bin/env python3
import os
import sys
import subprocess
import threading
import queue
import webbrowser
import time
import platform
import re
import shutil
import signal

def ensure_pip():
    try:
        import pip
    except ImportError:
        try:
            subprocess.check_call([sys.executable, "-m", "ensurepip"])
        except Exception:
            os.system("wget https://bootstrap.pypa.io/get-pip.py -O get-pip.py")
            os.system(f"{sys.executable} get-pip.py")
            os.remove("get-pip.py")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    except Exception:
        pass

ensure_pip()

def install_and_import(package):
    try:
        __import__(package)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

for pkg in ["flask", "requests", "pyngrok"]:
    install_and_import(pkg)

import requests
from flask import Flask, request
from pyngrok import ngrok, conf, exception

app = Flask(__name__)
visitor_queue = queue.Queue()
ngrok_tunnel = None
cloudflared_process = None

BANNER = """
===============================
     Made by Mohimanul-TVM
===============================
"""

def get_ip_geolocation(ip):
    try:
        url = f"https://ipinfo.io/{ip}/json"
        res = requests.get(url, timeout=5)
        res.raise_for_status()
        data = res.json()
        loc = data.get("loc", "")
        latitude, longitude = ("", "")
        if loc and "," in loc:
            latitude, longitude = loc.split(",")
        return {
            "ip": data.get("ip", ip),
            "city": data.get("city", "Unknown"),
            "region": data.get("region", "Unknown"),
            "country": data.get("country", "Unknown"),
            "latitude": latitude,
            "longitude": longitude
        }
    except Exception:
        return {"ip": ip, "error": "Could not fetch location data"}

def option_1_track_ip():
    while True:
        ip = input("\nEnter IP address to track (or 'back' to return): ").strip()
        if ip.lower() == "back":
            return
        if not ip:
            print("Please enter a valid IP.")
            continue
        info = get_ip_geolocation(ip)
        print("\n--- IP Information ---")
        for k, v in info.items():
            print(f"{k.capitalize()}: {v}")
        print("-----------------------\n")

@app.route("/")
def index():
    visitor_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    location_data = get_ip_geolocation(visitor_ip)
    visitor_queue.put(location_data)
    html = f"""
    <html>
    <head><title>Location Tracker</title></head>
    <body>
    <h2>Welcome!</h2>
    <p>Your IP: {visitor_ip}</p>
    <p>Approximate Location:</p>
    <ul>
        <li>City: {location_data.get("city")}</li>
        <li>Region: {location_data.get("region")}</li>
        <li>Country: {location_data.get("country")}</li>
        <li>Latitude: {location_data.get("latitude")}</li>
        <li>Longitude: {location_data.get("longitude")}</li>
    </ul>
    </body>
    </html>
    """
    return html

def run_flask_server():
    app.run(host="0.0.0.0", port=5000)

def get_or_ask_auth_token():
    token_file = "ngrok_token.txt"
    if os.path.exists(token_file):
        with open(token_file, "r") as f:
            token = f.read().strip()
            if token:
                return token
    print("\n[!] No ngrok auth token found!")
    print("Get your free ngrok auth token at: https://dashboard.ngrok.com/get-started/your-authtoken\n")
    token = input("Paste your ngrok auth token here: ").strip()
    with open(token_file, "w") as f:
        f.write(token)
    return token

def kill_process_on_port(port=5000):
    try:
        if platform.system() == "Windows":
            cmd_find = f'netstat -ano | findstr :{port}'
            output = subprocess.check_output(cmd_find, shell=True).decode()
            for line in output.strip().split('\n'):
                parts = line.strip().split()
                if len(parts) >= 5 and parts[1].endswith(f":{port}"):
                    pid = parts[-1]
                    subprocess.call(f"taskkill /PID {pid} /F", shell=True)
        else:
            cmd_find = f"lsof -ti:{port}"
            pids = subprocess.check_output(cmd_find, shell=True).decode().strip().split('\n')
            for pid in pids:
                if pid.isdigit():
                    subprocess.call(f"kill -9 {pid}", shell=True)
    except Exception:
        pass

def start_ngrok_tunnel():
    global ngrok_tunnel
    try:
        ngrok.kill()
    except Exception:
        pass
    auth_token = get_or_ask_auth_token()
    try:
        conf.get_default().auth_token = auth_token
        ngrok.set_auth_token(auth_token)
    except exception.PyngrokNgrokError:
        print("[!] Invalid ngrok auth token or unable to set token.")
        return None
    try:
        tunnel = ngrok.connect(5000)
        ngrok_tunnel = tunnel
        return tunnel
    except exception.PyngrokNgrokError as e:
        print(f"[!] Failed to start ngrok tunnel: {e}")
        return None

def option_2_public_tracker():
    kill_process_on_port(5000)
    flask_thread = threading.Thread(target=run_flask_server, daemon=True)
    flask_thread.start()
    print("[*] Starting ngrok tunnel...")
    tunnel = start_ngrok_tunnel()
    if not tunnel:
        print("[!] Ngrok tunnel failed to start.")
        return
    print(f"\n[+] Share this URL:\n\n    {tunnel.public_url}\n")
    try:
        while True:
            visitor = visitor_queue.get()
            for k, v in visitor.items():
                print(f"{k.capitalize()}: {v}")
            lat, lon = visitor.get('latitude'), visitor.get('longitude')
            if lat and lon:
                url = f"https://www.google.com/maps?q={lat},{lon}"
                print(f"Google Maps Link: {url}")
                choice = input("Open location in browser? (y/n): ").strip().lower()
                if choice == "y":
                    webbrowser.open(url)
            print()
    except KeyboardInterrupt:
        if ngrok_tunnel:
            ngrok.disconnect(ngrok_tunnel.public_url)
            ngrok.kill()

def install_cloudflared():
    if shutil.which("cloudflared"):
        return
    arch = platform.machine()
    url = ""
    sysname = platform.system()
    if sysname == "Linux":
        if "aarch64" in arch or "arm" in arch.lower():
            url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64"
        elif "x86_64" in arch:
            url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
        else:
            return
    elif sysname == "Darwin":
        url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-amd64"
    elif sysname == "Windows":
        url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
    else:
        return
    filename = "cloudflared"
    if sysname == "Windows":
        filename += ".exe"
    os.system(f"wget {url} -O {filename}")
    os.system(f"chmod +x {filename}")
    if sysname != "Windows":
        home_bin = os.path.expanduser("~/.local/bin")
        os.makedirs(home_bin, exist_ok=True)
        shutil.move(filename, os.path.join(home_bin, filename))
        print(f"[+] cloudflared installed to {home_bin}")

def start_cloudflared_tunnel():
    global cloudflared_process
    try:
        cloudflared_process = subprocess.Popen(
            ["cloudflared", "tunnel", "--url", "http://localhost:5000"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )
    except FileNotFoundError:
        print("[!] cloudflared not found, please install it first.")
        return None
        public_url = None
    pattern = re.compile(r"https?://[^\s]+trycloudflare.com")
    try:
        for line in iter(cloudflared_process.stdout.readline, ""):
            line = line.strip()
            match = pattern.search(line)
            if match:
                public_url = match.group(0)
                break
    except Exception:
        pass

    if not public_url:
        try:
            cloudflared_process.terminate()
        except Exception:
            pass
        return None
    return public_url

def option_3_cloudflare_tracker():
    kill_process_on_port(5000)
    flask_thread = threading.Thread(target=run_flask_server, daemon=True)
    flask_thread.start()
    install_cloudflared()
    print("[*] Starting cloudflared tunnel...")
    public_url = start_cloudflared_tunnel()
    if not public_url:
        print("[!] cloudflared tunnel failed.")
        return
    print(f"\n[+] Share this URL:\n\n    {public_url}\n")
    try:
        while True:
            visitor = visitor_queue.get()
            for k, v in visitor.items():
                print(f"{k.capitalize()}: {v}")
            lat, lon = visitor.get('latitude'), visitor.get('longitude')
            if lat and lon:
                url = f"https://www.google.com/maps?q={lat},{lon}"
                print(f"Google Maps Link: {url}")
                choice = input("Open location in browser? (y/n): ").strip().lower()
                if choice == "y":
                    webbrowser.open(url)
            print()
    except KeyboardInterrupt:
        if cloudflared_process:
            cloudflared_process.terminate()
            cloudflared_process.wait()

def main_menu():
    print(BANNER)
    while True:
        print("\n1) Track IP by input")
        print("2) Public shareable URL with ngrok")
        print("3) Public shareable URL with Cloudflare Tunnel")
        print("4) Exit")
        choice = input("Choice: ").strip()
        if choice == "1":
            option_1_track_ip()
        elif choice == "2":
            option_2_public_tracker()
        elif choice == "3":
            option_3_cloudflare_tracker()
        elif choice == "4":
            print("Exiting...")
            try:
                ngrok.kill()
            except Exception:
                pass
            try:
                if cloudflared_process:
                    cloudflared_process.terminate()
                    cloudflared_process.wait()
            except Exception:
                pass
            sys.exit(0)
        else:
            print("Invalid option, please choose 1-4.")

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\n[!] Interrupted by user, cleaning up...")
        try:
            ngrok.kill()
        except Exception:
            pass
        try:
            if cloudflared_process:
                cloudflared_process.terminate()
                cloudflared_process.wait()
        except Exception:
            pass
        sys.exit(0)
