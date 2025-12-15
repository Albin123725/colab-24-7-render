"""
🎮 COLAB KEEP-ALIVE SERVICE
Keeps your Colab Minecraft server running 24/7 by pinging it regularly
No Chrome browser needed - just HTTP requests!
"""

import os
import time
import logging
import requests
from threading import Thread, Lock
from flask import Flask, render_template_string, jsonify
from datetime import datetime

app = Flask(__name__)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Your Colab URL
COLAB_URL = os.environ.get('COLAB_URL', 'https://colab.research.google.com/drive/1jckV8xUJSmLhhol6wZwVJzpybsimiRw1')

# Global variables
monitoring = False
lock = Lock()
start_time = time.time()
session_start = datetime.now()
stats = {
    'ping_count': 0,
    'success_count': 0,
    'error_count': 0,
    'last_ping': None,
    'last_status': None,
    'uptime_seconds': 0
}

HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>🎮 Colab 24/7 Keep-Alive</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Arial, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            color: #333;
        }
        .container {
            max-width: 1000px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #e0e0e0;
        }
        .header h1 {
            color: #2d3436;
            font-size: 2.5em;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 15px;
        }
        .header p {
            color: #636e72;
            font-size: 1.1em;
        }
        .status-card {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            margin-bottom: 25px;
            border-left: 5px solid #00b894;
            transition: transform 0.3s;
        }
        .status-card.stopped { border-left-color: #d63031; }
        .status-card:hover { transform: translateY(-3px); }
        .status-label { color: #636e72; font-size: 0.9em; margin-bottom: 5px; }
        .status-value {
            font-size: 2em;
            font-weight: bold;
            color: #2d3436;
        }
        .status-value.running { color: #00b894; }
        .status-value.stopped { color: #d63031; }
        .controls {
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            margin: 30px 0;
            justify-content: center;
        }
        .btn {
            padding: 15px 30px;
            border: none;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            gap: 10px;
            min-width: 180px;
            justify-content: center;
        }
        .btn-start { background: #00b894; color: white; }
        .btn-stop { background: #d63031; color: white; }
        .btn-restart { background: #0984e3; color: white; }
        .btn-refresh { background: #6c5ce7; color: white; }
        .btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 7px 20px rgba(0,0,0,0.2);
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }
        .stat-box {
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 3px 10px rgba(0,0,0,0.1);
            text-align: center;
        }
        .stat-number {
            font-size: 2.2em;
            font-weight: bold;
            color: #0984e3;
            margin-bottom: 5px;
        }
        .stat-label {
            color: #636e72;
            font-size: 0.9em;
        }
        .logs-container {
            background: #2d3436;
            color: #dfe6e9;
            padding: 20px;
            border-radius: 15px;
            margin-top: 30px;
            max-height: 300px;
            overflow-y: auto;
        }
        .log-entry {
            padding: 8px 0;
            border-bottom: 1px solid #404040;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 13px;
        }
        .log-time { color: #81ecec; }
        .log-info { color: #00b894; }
        .log-warning { color: #fdcb6e; }
        .log-error { color: #ff7675; }
        .info-box {
            background: #ffeaa7;
            border: 2px solid #fdcb6e;
            border-radius: 12px;
            padding: 20px;
            margin: 20px 0;
        }
        .url-display {
            background: #f1f3f4;
            padding: 15px;
            border-radius: 10px;
            margin: 20px 0;
            word-break: break-all;
            font-family: monospace;
        }
        @media (max-width: 768px) {
            .container { padding: 15px; }
            .btn { min-width: 100%; }
            .status-value { font-size: 1.5em; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎮 Colab 24/7 Keep-Alive</h1>
            <p>Keeps your Minecraft Colab server running continuously</p>
        </div>
        
        <div class="info-box">
            <strong>📌 How it works:</strong> This service pings your Colab URL every 5 minutes to keep the session alive.
            No browser automation needed - just simple HTTP requests!
        </div>
        
        <div class="url-display">
            <strong>Monitoring URL:</strong><br>
            <span id="colabUrl">''' + COLAB_URL + '''</span>
        </div>
        
        <div class="status-card" id="statusCard">
            <div class="status-label">SERVICE STATUS</div>
            <div class="status-value" id="statusText">STOPPED</div>
            <div class="status-label" id="statusDetail">Not monitoring</div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-box">
                <div class="stat-number" id="pingCount">0</div>
                <div class="stat-label">Total Pings</div>
            </div>
            <div class="stat-box">
                <div class="stat-number" id="successCount">0</div>
                <div class="stat-label">Successful</div>
            </div>
            <div class="stat-box">
                <div class="stat-number" id="errorCount">0</div>
                <div class="stat-label">Errors</div>
            </div>
            <div class="stat-box">
                <div class="stat-number" id="uptime">00:00:00</div>
                <div class="stat-label">Uptime</div>
            </div>
        </div>
        
        <div class="controls">
            <button class="btn btn-start" onclick="control('start')">
                <span>▶</span> Start Monitoring
            </button>
            <button class="btn btn-stop" onclick="control('stop')">
                <span>⏹</span> Stop
            </button>
            <button class="btn btn-restart" onclick="control('restart')">
                <span>🔄</span> Restart
            </button>
            <button class="btn btn-refresh" onclick="location.reload()">
                <span>↻</span> Refresh Page
            </button>
        </div>
        
        <div class="logs-container">
            <h3 style="color: white; margin-bottom: 15px;">Live Logs</h3>
            <div id="logs">
                <div class="log-entry"><span class="log-time">[--:--:--]</span> <span class="log-info">Logs will appear here...</span></div>
            </div>
        </div>
        
        <div style="text-align: center; margin-top: 20px; color: #636e72; font-size: 0.9em;">
            Last updated: <span id="updateTime">--:--:--</span>
        </div>
    </div>
    
    <script>
        function control(action) {
            fetch('/' + action)
                .then(r => r.text())
                .then(msg => {
                    alert(msg);
                    updateStatus();
                })
                .catch(err => alert('Error: ' + err));
        }
        
        function updateStatus() {
            fetch('/status')
                .then(r => r.json())
                .then(data => {
                    // Update status
                    const statusText = document.getElementById('statusText');
                    const statusCard = document.getElementById('statusCard');
                    const statusDetail = document.getElementById('statusDetail');
                    
                    statusText.textContent = data.status.toUpperCase();
                    statusDetail.textContent = data.detail;
                    
                    if (data.status === 'running') {
                        statusText.className = 'status-value running';
                        statusCard.className = 'status-card';
                    } else {
                        statusText.className = 'status-value stopped';
                        statusCard.className = 'status-card stopped';
                    }
                    
                    // Update stats
                    document.getElementById('pingCount').textContent = data.stats.ping_count;
                    document.getElementById('successCount').textContent = data.stats.success_count;
                    document.getElementById('errorCount').textContent = data.stats.error_count;
                    document.getElementById('uptime').textContent = formatTime(data.stats.uptime_seconds);
                    
                    // Update logs
                    fetch('/get_logs')
                        .then(r => r.text())
                        .then(logs => {
                            const logsDiv = document.getElementById('logs');
                            logsDiv.innerHTML = logs;
                            logsDiv.scrollTop = logsDiv.scrollHeight;
                        });
                    
                    // Update timestamp
                    document.getElementById('updateTime').textContent = new Date().toLocaleTimeString();
                })
                .catch(err => console.error('Status update error:', err));
        }
        
        function formatTime(seconds) {
            const hrs = Math.floor(seconds / 3600);
            const mins = Math.floor((seconds % 3600) / 60);
            const secs = Math.floor(seconds % 60);
            return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        }
        
        // Auto-update every 5 seconds
        setInterval(updateStatus, 5000);
        
        // Initial update
        updateStatus();
        
        // Auto-start monitoring
        setTimeout(() => {
            if (document.getElementById('statusText').textContent === 'STOPPED') {
                control('start');
            }
        }, 1000);
    </script>
</body>
</html>
'''

def ping_colab():
    """Ping Colab URL to keep session alive"""
    global stats
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        }
        
        # Make the request
        response = requests.get(COLAB_URL, headers=headers, timeout=15, allow_redirects=True)
        
        # Update stats
        stats['ping_count'] += 1
        stats['success_count'] += 1
        stats['last_ping'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        stats['last_status'] = f"HTTP {response.status_code}"
        stats['uptime_seconds'] = int(time.time() - start_time)
        
        if response.status_code == 200:
            logger.info(f"✅ Ping successful (Status: {response.status_code})")
            return True
        else:
            logger.warning(f"⚠️ Ping returned status: {response.status_code}")
            return True  # Still counts as success for our purposes
            
    except requests.exceptions.Timeout:
        stats['ping_count'] += 1
        stats['error_count'] += 1
        stats['last_ping'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        stats['last_status'] = "Timeout"
        logger.warning("⏰ Request timeout")
        return False
        
    except requests.exceptions.ConnectionError:
        stats['ping_count'] += 1
        stats['error_count'] += 1
        stats['last_ping'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        stats['last_status'] = "Connection Error"
        logger.warning("🔌 Connection error")
        return False
        
    except Exception as e:
        stats['ping_count'] += 1
        stats['error_count'] += 1
        stats['last_ping'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        stats['last_status'] = str(e)[:50]
        logger.error(f"❌ Ping error: {e}")
        return False

def keep_alive_worker():
    """Worker thread that pings Colab regularly"""
    global monitoring
    logger.info("🚀 Starting Colab keep-alive service")
    
    ping_interval = 300  # 5 minutes
    
    while monitoring:
        try:
            success = ping_colab()
            
            if not success:
                # If failed, try again sooner
                time.sleep(60)
            else:
                # Wait for next ping
                for _ in range(ping_interval // 10):
                    if not monitoring:
                        break
                    time.sleep(10)
                    
        except Exception as e:
            logger.error(f"Worker error: {e}")
            time.sleep(30)

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/start')
def start():
    global monitoring
    with lock:
        if not monitoring:
            monitoring = True
            Thread(target=keep_alive_worker, daemon=True).start()
            return "✅ Colab keep-alive started! Pinging every 5 minutes to keep your Minecraft server running."
        return "⚠️ Service is already running."

@app.route('/stop')
def stop():
    global monitoring
    with lock:
        monitoring = False
        return "⏹️ Service stopped."

@app.route('/restart')
def restart():
    global monitoring
    with lock:
        monitoring = False
        time.sleep(2)
        monitoring = True
        Thread(target=keep_alive_worker, daemon=True).start()
        return "🔄 Service restarted!"

@app.route('/status')
def status():
    uptime_seconds = time.time() - start_time
    stats['uptime_seconds'] = int(uptime_seconds)
    
    status_text = 'running' if monitoring else 'stopped'
    detail = f"Pinging {COLAB_URL.split('/')[-1][:20]}..." if monitoring else "Not monitoring"
    
    return jsonify({
        'status': status_text,
        'detail': detail,
        'colab_url': COLAB_URL,
        'stats': stats,
        'start_time': session_start.isoformat(),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/get_logs')
def get_logs():
    # Return formatted logs
    logs = []
    logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Current Status: {'RUNNING' if monitoring else 'STOPPED'}")
    logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Total Pings: {stats['ping_count']}")
    logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Success: {stats['success_count']}")
    logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Errors: {stats['error_count']}")
    
    if stats['last_ping']:
        logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Last Ping: {stats['last_ping']}")
        logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Last Status: {stats['last_status']}")
    
    return '<br>'.join([f'<div class="log-entry"><span class="log-time">{log.split("]")[0]}]</span> <span class="log-info">{log.split("]")[1].strip()}</span></div>' for log in logs])

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'monitoring': monitoring,
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    # Start monitoring automatically
    monitoring = True
    worker_thread = Thread(target=keep_alive_worker, daemon=True)
    worker_thread.start()
    
    logger.info(f"🚀 Colab Keep-Alive Service Started")
    logger.info(f"📌 Monitoring: {COLAB_URL}")
    logger.info(f"⏰ Start Time: {session_start}")
    logger.info("✅ Service is now pinging Colab every 5 minutes")
    
    # Run Flask
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
