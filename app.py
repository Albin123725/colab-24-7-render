"""
🚀 COLAB 24/7 - SIMPLE KEEP-ALIVE
Uses HTTP requests to ping Colab and keep it alive
"""

import os
import time
import logging
from datetime import datetime
from threading import Thread, Timer
from flask import Flask, render_template_string, jsonify
import requests

app = Flask(__name__)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Your Colab URL
COLAB_URL = os.environ.get('COLAB_URL', 'https://colab.research.google.com/drive/1jckV8xUJSmLhhol6wZwVJzpybsimiRw1')

# Global variables
monitoring = True
stats = {
    'total_pings': 0,
    'successful_pings': 0,
    'failed_pings': 0,
    'last_ping': None,
    'last_status': None
}

HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>🚀 Colab 24/7 Keep-Alive</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { 
            font-family: Arial, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0; padding: 20px; min-height: 100vh;
        }
        .container {
            max-width: 800px; margin: 0 auto; background: white;
            border-radius: 15px; padding: 30px; box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        .header { text-align: center; margin-bottom: 30px; }
        .header h1 { color: #333; margin: 0; font-size: 2em; }
        .status-box {
            background: #f8f9fa; padding: 20px; border-radius: 10px;
            margin: 20px 0; border-left: 5px solid #34a853;
        }
        .stats {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); 
            gap: 15px; margin: 20px 0;
        }
        .stat-card { 
            background: white; padding: 15px; border-radius: 8px; 
            box-shadow: 0 2px 5px rgba(0,0,0,0.1); text-align: center;
        }
        .stat-number { 
            font-size: 24px; font-weight: bold; color: #4285f4; 
            margin-bottom: 5px;
        }
        .stat-label { color: #666; font-size: 14px; }
        .controls {
            display: flex; gap: 10px; margin: 30px 0;
            justify-content: center; flex-wrap: wrap;
        }
        button {
            padding: 12px 24px; border: none; border-radius: 8px;
            background: #4285f4; color: white; cursor: pointer;
            font-weight: bold; transition: all 0.3s;
        }
        button:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.2); }
        .btn-success { background: #34a853; }
        .btn-warning { background: #fbbc05; color: #333; }
        .btn-danger { background: #ea4335; }
        .logs {
            background: #1e1e1e; color: #00ff00; padding: 15px;
            border-radius: 10px; font-family: 'Courier New', monospace;
            max-height: 200px; overflow-y: auto; margin-top: 20px;
            font-size: 14px;
        }
        .info-box {
            background: #e8f4fd; border: 2px solid #b6e0ff;
            border-radius: 10px; padding: 15px; margin: 20px 0;
        }
        .url-display {
            background: #f1f3f4; padding: 10px; border-radius: 5px;
            margin: 10px 0; word-break: break-all; font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Colab 24/7 Keep-Alive</h1>
            <p>Keeps your Colab session active 24/7</p>
        </div>
        
        <div class="info-box">
            <strong>📢 How it works:</strong> This service pings your Colab URL every 5 minutes 
            to reset the inactivity timer. Colab stays connected even when you close your laptop!
        </div>
        
        <div class="status-box">
            <h3>Service Status: <span id="statusText" style="color: #34a853;">RUNNING</span></h3>
            <div class="url-display">
                <strong>Monitoring:</strong><br>
                <span id="colabUrl">''' + COLAB_URL + '''</span>
            </div>
            <p>Last Ping: <span id="lastPing">Never</span></p>
            <p>Last Status: <span id="lastStatus">-</span></p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number" id="totalPings">0</div>
                <div class="stat-label">Total Pings</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="successPings">0</div>
                <div class="stat-label">Successful</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="failedPings">0</div>
                <div class="stat-label">Failed</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="uptime">00:00:00</div>
                <div class="stat-label">Uptime</div>
            </div>
        </div>
        
        <div class="controls">
            <button class="btn-success" onclick="forcePing()">📡 Force Ping Now</button>
            <button class="btn-warning" onclick="restartService()">🔄 Restart Service</button>
            <button onclick="location.reload()">↻ Refresh Page</button>
            <button class="btn-danger" onclick="toggleMonitoring()">⏸️ Pause</button>
        </div>
        
        <div>
            <h3>Live Logs:</h3>
            <div class="logs" id="logs">
                [Logs will appear here...]
            </div>
        </div>
        
        <div style="text-align: center; margin-top: 20px; color: #666; font-size: 12px;">
            Service started: <span id="startTime">Loading...</span>
        </div>
    </div>
    
    <script>
        let monitoring = true;
        let startTimestamp = Date.now();
        
        function forcePing() {
            fetch('/ping')
                .then(r => r.json())
                .then(data => {
                    addLog(`📡 Manual ping: ${data.status}`);
                    updateStats();
                });
        }
        
        function restartService() {
            if (confirm('Restart monitoring service?')) {
                fetch('/restart')
                    .then(r => r.json())
                    .then(data => {
                        addLog('🔄 Service restarted');
                        setTimeout(updateStats, 1000);
                    });
            }
        }
        
        function toggleMonitoring() {
            monitoring = !monitoring;
            const btn = document.querySelector('.btn-danger');
            if (monitoring) {
                btn.textContent = '⏸️ Pause';
                btn.className = 'btn-danger';
                addLog('▶️ Monitoring resumed');
            } else {
                btn.textContent = '▶️ Resume';
                btn.className = 'btn-success';
                addLog('⏸️ Monitoring paused');
            }
        }
        
        function addLog(message) {
            const logs = document.getElementById('logs');
            const time = new Date().toLocaleTimeString();
            const logEntry = `<div>[${time}] ${message}</div>`;
            logs.innerHTML = logEntry + logs.innerHTML;
            
            // Keep only last 20 logs
            const logDivs = logs.querySelectorAll('div');
            if (logDivs.length > 20) {
                for (let i = 20; i < logDivs.length; i++) {
                    logDivs[i].remove();
                }
            }
            
            logs.scrollTop = 0;
        }
        
        function updateStats() {
            fetch('/status')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('totalPings').textContent = data.stats.total_pings;
                    document.getElementById('successPings').textContent = data.stats.successful_pings;
                    document.getElementById('failedPings').textContent = data.stats.failed_pings;
                    document.getElementById('lastPing').textContent = data.stats.last_ping || 'Never';
                    document.getElementById('lastStatus').textContent = data.stats.last_status || '-';
                    document.getElementById('colabUrl').textContent = data.colab_url;
                    document.getElementById('startTime').textContent = new Date(data.start_time * 1000).toLocaleString();
                    
                    // Update uptime
                    const uptimeSeconds = Math.floor((Date.now() - startTimestamp) / 1000);
                    document.getElementById('uptime').textContent = formatTime(uptimeSeconds);
                });
        }
        
        function formatTime(seconds) {
            const hrs = Math.floor(seconds / 3600);
            const mins = Math.floor((seconds % 3600) / 60);
            const secs = Math.floor(seconds % 60);
            return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        }
        
        // Auto-update every 3 seconds
        setInterval(updateStats, 3000);
        
        // Initial update
        setTimeout(updateStats, 1000);
        
        // Add initial log
        addLog('🚀 Service started. Pinging Colab every 5 minutes...');
    </script>
</body>
</html>
'''

def ping_colab():
    """Ping Colab to keep session alive"""
    global stats
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
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
        
        response = requests.get(COLAB_URL, headers=headers, timeout=15, allow_redirects=True)
        
        stats['total_pings'] += 1
        stats['successful_pings'] += 1
        stats['last_ping'] = datetime.now().strftime("%H:%M:%S")
        stats['last_status'] = f"HTTP {response.status_code}"
        
        if response.status_code == 200:
            logger.info(f"✅ Ping successful: {response.status_code}")
            return {"status": "success", "code": response.status_code}
        else:
            logger.warning(f"⚠️ Ping status: {response.status_code}")
            return {"status": "warning", "code": response.status_code}
            
    except requests.exceptions.Timeout:
        stats['total_pings'] += 1
        stats['failed_pings'] += 1
        stats['last_ping'] = datetime.now().strftime("%H:%M:%S")
        stats['last_status'] = "Timeout"
        logger.warning("⏰ Request timeout")
        return {"status": "timeout"}
        
    except requests.exceptions.ConnectionError:
        stats['total_pings'] += 1
        stats['failed_pings'] += 1
        stats['last_ping'] = datetime.now().strftime("%H:%M:%S")
        stats['last_status'] = "Connection Error"
        logger.warning("🔌 Connection error")
        return {"status": "connection_error"}
        
    except Exception as e:
        stats['total_pings'] += 1
        stats['failed_pings'] += 1
        stats['last_ping'] = datetime.now().strftime("%H:%M:%S")
        stats['last_status'] = str(e)[:50]
        logger.error(f"❌ Ping error: {e}")
        return {"status": "error", "message": str(e)}

def keep_alive_worker():
    """Worker that pings Colab regularly"""
    global monitoring
    
    logger.info("🚀 Starting Colab keep-alive service")
    ping_count = 0
    
    while monitoring:
        try:
            ping_count += 1
            result = ping_colab()
            
            # Adjust interval based on result
            if result['status'] == 'success':
                wait_time = 300  # 5 minutes if successful
                logger.info(f"📊 Ping #{ping_count}: Success. Next in {wait_time//60} min")
            else:
                wait_time = 60  # 1 minute if failed
                logger.warning(f"📊 Ping #{ping_count}: {result['status']}. Retry in 1 min")
            
            # Wait for next ping
            for _ in range(wait_time // 10):
                if not monitoring:
                    break
                time.sleep(10)
                
        except Exception as e:
            logger.error(f"Worker error: {e}")
            time.sleep(30)

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/ping')
def ping():
    """Manual ping endpoint"""
    result = ping_colab()
    return jsonify(result)

@app.route('/restart')
def restart():
    """Restart monitoring"""
    global monitoring
    monitoring = False
    time.sleep(2)
    monitoring = True
    Thread(target=keep_alive_worker, daemon=True).start()
    return jsonify({"status": "restarted"})

@app.route('/status')
def status():
    return jsonify({
        'status': 'running' if monitoring else 'stopped',
        'colab_url': COLAB_URL,
        'stats': stats,
        'start_time': time.time() - 5,  # Approximate start time
        'timestamp': datetime.now().isoformat()
    })

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    # Start monitoring automatically
    monitoring = True
    worker_thread = Thread(target=keep_alive_worker, daemon=True)
    worker_thread.start()
    
    logger.info("=" * 60)
    logger.info("🚀 COLAB 24/7 KEEP-ALIVE SERVICE")
    logger.info("=" * 60)
    logger.info(f"📌 Monitoring: {COLAB_URL}")
    logger.info("⏰ Pinging every 5 minutes")
    logger.info("✅ Service started")
    
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
