#!/usr/bin/env python3
import os
import sys
import subprocess
import threading
import queue
import webbrowser
import time
import json
import shutil
import platform

def ensure_pip():
    try:
        import pip
    except ImportError:
        print("[*] pip not found. Attempting to install...")
        try:
            subprocess.check_call([sys.executable, "-m", "ensurepip"])
        except Exception:
            print("[!] ensurepip not available. Trying get-pip.py...")
            os.system("wget https://bootstrap.pypa.io/get-pip.py -O get-pip.py")
            os.system(f"{sys.executable} get-pip.py")
            os.remove("get-pip.py")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    except Exception:
        print("[!] Warning: Could not upgrade pip.")

ensure_pip()

def install_and_import(package):
    try:
        __import__(package)
    except ImportError:
        print(f"[+] Installing {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

for pkg in ["flask", "requests", "pyngrok"]:
    install_and_import(pkg)

import requests
from flask import Flask, request
from pyngrok import ngrok

def install_ngrok_binary():
    if shutil.which("ngrok") is not None:
        return
    print("[*] ngrok binary not found. Attempting to install...")
    arch = platform.machine()
    url = ""
    if "aarch64" in arch or "arm" in arch.lower():
        url = "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-stable-linux-arm.zip"
    elif "x86_64" in arch:
        url = "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-stable-linux-amd64.zip"
    else:
        print("[!] Unknown architecture. Please install ngrok manually.")
        return
    try:
        os.system(f"wget {url} -O ngrok.zip")
        os.system("unzip ngrok.zip")
        os.system("chmod +x ngrok")
        os.system("mv ngrok $PREFIX/bin/")
        os.remove("ngrok.zip")
        print("[+] ngrok installed successfully!")
    except Exception as e:
        print(f"[!] Failed to install ngrok automatically: {e}")

install_ngrok_binary()

BANNER = """
=====================================
        Made by Mohimanul-TVM
=====================================
"""

visitor_queue = queue.Queue()
app = Flask(__name__)
ngrok_tunnel = None

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
    except (requests.RequestException, json.JSONDecodeError):
        return {"ip": ip, "error": "Could not fetch location data"}

def option_1_track_ip():
    while True:
        ip = input("\nEnter IP address to track (or 'back' to return): ").strip()
        if ip.lower() == "back":
            return
        if not ip:
            print("Please enter a valid IP.")
            continue
        print("[*] Querying location...")
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
        <li>City: {location_data.get('city')}</li>
        <li>Region: {location_data.get('region')}</li>
        <li>Country: {location_data.get('country')}</li>
        <li>Latitude: {location_data.get('latitude')}</li>
        <li>Longitude: {location_data.get('longitude')}</li>
    </ul>
    <p>Thank you for visiting.</p>
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
    print("You need a free ngrok account. Get your auth token here:")
    print("   https://dashboard.ngrok.com/get-started/your-authtoken\n")
    token = input("Paste your ngrok auth token here: ").strip()
    with open(token_file, "w") as f:
        f.write(token)
    print("[+] Auth token saved to ngrok_token.txt for future runs.")
    return token

def start_ngrok_tunnel():
    ngrok.kill()
    try:
        auth_token = get_or_ask_auth_token()
        ngrok.set_auth_token(auth_token)
    except Exception as e:
        print(f"[!] Error setting auth token: {e}")
        return None
    try:
        tunnel = ngrok.connect(5000)
        return tunnel
    except Exception as e:
        print(f"[!] Failed to start ngrok tunnel: {e}")
        return None

def option_2_public_tracker():
    global ngrok_tunnel
    flask_thread = threading.Thread(target=run_flask_server, daemon=True)
    flask_thread.start()
    print("[*] Starting ngrok tunnel...")
    ngrok_tunnel = start_ngrok_tunnel()
    if not ngrok_tunnel:
        print("[!] Exiting this option due to tunnel error.")
        return
    print(f"\n[+] Share this URL:\n\n    {ngrok_tunnel.public_url}\n")
    while True:
        try:
            visitor = visitor_queue.get()
            print("\n=== New Visitor ===")
            for k, v in visitor.items():
                print(f"{k.capitalize()}: {v}")
            lat = visitor.get('latitude')
            lon = visitor.get('longitude')
            if lat and lon:
                maps_url = f"https://www.google.com/maps?q={lat},{lon}"
                print(f"\nGoogle Maps Link: {maps_url}")
                choice = input("Open this location in your browser? (y/n): ").strip().lower()
                if choice == "y":
                    webbrowser.open(maps_url)
            else:
                print("No valid latitude/longitude.")
            print("\n[*] Waiting for next visitor...\n")
            time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n[!] Interrupted. Shutting down...")
            if ngrok_tunnel:
                ngrok.disconnect(ngrok_tunnel.public_url)
                ngrok.kill()
            break
        except Exception as e:
            print(f"[!] Error: {e}")

def main_menu():
    print(BANNER)
    while True:
        print("\nSelect an option:")
        print("1) Track IP by input")
        print("2) Generate public shareable URL to track visitors")
        print("3) Exit")
        choice = input("Enter choice (1/2/3): ").strip()
        if choice == "1":
            option_1_track_ip()
        elif choice == "2":
            option_2_public_tracker()
        elif choice == "3":
            print("\nGoodbye!\n")
            sys.exit(0)
        else:
            print("\nInvalid choice. Please try again.")

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\nExiting gracefully. Goodbye!")
        try:
            ngrok.kill()
        except Exception:
            pass
