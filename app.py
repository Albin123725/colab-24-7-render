"""
🚀 COLAB 24/7 - RENDER HOSTED BROWSER
Render opens Colab in virtual browser and keeps it running 24/7
Even when your laptop is closed!
"""

import os
import time
import logging
import json
import random
import base64
from datetime import datetime
from threading import Thread, Lock
from flask import Flask, render_template_string, jsonify, request, send_file
import requests
from io import BytesIO

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

# Browserless API (Virtual browser service)
BROWSERLESS_API = "https://chrome.browserless.io"
BROWSERLESS_TOKEN = os.environ.get('BROWSERLESS_TOKEN', '')  # Get free token from browserless.io

# Global variables
session_active = False
lock = Lock()
start_time = time.time()
session_start = datetime.now()
stats = {
    'browser_sessions': 0,
    'colab_pings': 0,
    'auto_clicks': 0,
    'errors': 0,
    'last_action': None
}

HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>🚀 Colab 24/7 - Render Hosted Browser</title>
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
            max-width: 1400px;
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
        }
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .status-card {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            border-left: 5px solid #00b894;
        }
        .status-card.inactive { border-left-color: #d63031; }
        .browser-window {
            background: #2d3436;
            border-radius: 15px;
            padding: 20px;
            margin: 30px 0;
            color: white;
        }
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
        }
        .btn-start { background: #00b894; color: white; }
        .btn-stop { background: #d63031; color: white; }
        .btn-screenshot { background: #0984e3; color: white; }
        .btn-auto-click { background: #fdcb6e; color: #2d3436; }
        .btn:hover { transform: translateY(-3px); box-shadow: 0 7px 20px rgba(0,0,0,0.2); }
        .browser-frame {
            width: 100%;
            height: 600px;
            border: 3px solid #444;
            border-radius: 10px;
            overflow: hidden;
            background: white;
        }
        .browser-frame iframe {
            width: 100%;
            height: 100%;
            border: none;
        }
        .logs {
            background: #1e1e1e;
            color: #00ff00;
            padding: 20px;
            border-radius: 15px;
            font-family: monospace;
            max-height: 300px;
            overflow-y: auto;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Colab 24/7 - Render Hosted Browser</h1>
            <p>Colab runs in virtual browser on Render - Works even when your laptop is closed!</p>
        </div>
        
        <div class="status-grid">
            <div class="status-card" id="statusCard">
                <h3>VIRTUAL BROWSER STATUS</h3>
                <div class="status-value" id="statusText">INACTIVE</div>
                <p>Colab URL: <span id="colabUrl">Loading...</span></p>
            </div>
            
            <div class="status-card">
                <h3>ACTIVITY STATS</h3>
                <div>Browser Sessions: <span id="sessions">0</span></div>
                <div>Auto-Clicks: <span id="clicks">0</span></div>
                <div>Last Action: <span id="lastAction">Never</span></div>
            </div>
        </div>
        
        <div class="browser-window">
            <h3>🎮 LIVE COLAB BROWSER (Running on Render)</h3>
            <div class="browser-frame">
                <iframe id="colabFrame" src="about:blank" title="Colab Virtual Browser"></iframe>
            </div>
            <p class="browser-info">This is a REAL browser running on Render servers. Your Colab stays open here 24/7!</p>
        </div>
        
        <div class="controls">
            <button class="btn btn-start" onclick="startBrowser()">
                <span>🚀</span> Start Virtual Browser
            </button>
            <button class="btn btn-screenshot" onclick="takeScreenshot()">
                <span>📸</span> Take Screenshot
            </button>
            <button class="btn btn-auto-click" onclick="autoClick()">
                <span>🤖</span> Auto-Click Reconnect
            </button>
            <button class="btn" onclick="refreshBrowser()" style="background: #6c5ce7; color: white;">
                <span>🔄</span> Refresh Browser
            </button>
        </div>
        
        <div class="logs" id="logs">
            [Logs will appear here...]
        </div>
    </div>
    
    <script>
        let browserSession = null;
        
        function startBrowser() {
            fetch('/start_browser')
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        document.getElementById('colabFrame').src = data.view_url;
                        document.getElementById('statusText').textContent = 'ACTIVE';
                        document.getElementById('statusText').style.color = '#00b894';
                        updateLog(`✅ Virtual browser started: ${data.session_id}`);
                    } else {
                        alert('Error: ' + data.error);
                    }
                })
                .catch(err => {
                    alert('Failed to start browser: ' + err);
                });
        }
        
        function takeScreenshot() {
            fetch('/screenshot')
                .then(r => r.blob())
                .then(blob => {
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'colab-screenshot.png';
                    a.click();
                    updateLog('📸 Screenshot taken');
                });
        }
        
        function autoClick() {
            fetch('/auto_click')
                .then(r => r.json())
                .then(data => {
                    updateLog(`🤖 ${data.message}`);
                });
        }
        
        function refreshBrowser() {
            document.getElementById('colabFrame').src = 
                document.getElementById('colabFrame').src;
            updateLog('🔄 Browser refreshed');
        }
        
        function updateLog(message) {
            const logs = document.getElementById('logs');
            const time = new Date().toLocaleTimeString();
            logs.innerHTML = `[${time}] ${message}<br>` + logs.innerHTML;
        }
        
        // Auto-start browser
        setTimeout(startBrowser, 2000);
        
        // Update stats every 5 seconds
        setInterval(() => {
            fetch('/status')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('sessions').textContent = data.stats.browser_sessions;
                    document.getElementById('clicks').textContent = data.stats.auto_clicks;
                    document.getElementById('lastAction').textContent = data.stats.last_action || 'Never';
                    document.getElementById('colabUrl').textContent = data.colab_url;
                });
        }, 5000);
    </script>
</body>
</html>
'''

def start_virtual_browser():
    """Start a virtual browser session on Browserless"""
    global stats
    
    try:
        # Browserless API endpoint
        browserless_url = f"{BROWSERLESS_API}/content?token={BROWSERLESS_TOKEN}"
        
        # Prepare request
        payload = {
            "url": COLAB_URL,
            "gotoOptions": {
                "waitUntil": "networkidle0",
                "timeout": 30000
            },
            "setViewport": {
                "width": 1920,
                "height": 1080
            },
            "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        # Start browser session
        response = requests.post(
            browserless_url,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            stats['browser_sessions'] += 1
            stats['last_action'] = "Browser started"
            
            # Get session ID from response
            session_data = response.json()
            session_id = session_data.get('id', f'session_{int(time.time())}')
            
            logger.info(f"✅ Virtual browser started: {session_id}")
            
            return {
                "success": True,
                "session_id": session_id,
                "view_url": f"https://chrome.browserless.io/session/{session_id}",
                "screenshot_url": f"{BROWSERLESS_API}/screenshot?token={BROWSERLESS_TOKEN}&sessionId={session_id}"
            }
        else:
            logger.error(f"❌ Browserless error: {response.status_code}")
            return {
                "success": False,
                "error": f"Browserless API error: {response.status_code}"
            }
            
    except Exception as e:
        logger.error(f"❌ Failed to start browser: {e}")
        return {
            "success": False,
            "error": str(e)
        }

def auto_click_reconnect():
    """Automatically click reconnect/run buttons in Colab"""
    global stats
    
    try:
        if not BROWSERLESS_TOKEN:
            return {"success": False, "message": "Browserless token not configured"}
        
        # JavaScript to auto-click buttons
        click_script = """
        function autoClickColab() {
            // Click reconnect button
            const reconnect = document.querySelector('[aria-label="Reconnect"], [aria-label="Connect"]');
            if (reconnect) {
                reconnect.click();
                console.log('Clicked reconnect');
                
                // Wait and click run
                setTimeout(() => {
                    const runBtn = document.querySelector('[aria-label="Run all"]');
                    if (runBtn) {
                        runBtn.click();
                        console.log('Clicked run');
                        return 'reconnected_and_ran';
                    }
                }, 5000);
                return 'reconnected';
            }
            
            // Click run button
            const runBtn = document.querySelector('[aria-label="Run all"]');
            if (runBtn) {
                runBtn.click();
                console.log('Clicked run');
                return 'ran';
            }
            
            return 'no_buttons';
        }
        
        return autoClickColab();
        """
        
        # Execute JavaScript in browser
        execute_url = f"{BROWSERLESS_API}/execute?token={BROWSERLESS_TOKEN}"
        payload = {
            "code": click_script,
            "context": {}
        }
        
        response = requests.post(execute_url, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            stats['auto_clicks'] += 1
            stats['last_action'] = f"Auto-click at {datetime.now().strftime('%H:%M:%S')}"
            
            logger.info(f"✅ Auto-click executed: {result.get('result', 'unknown')}")
            return {
                "success": True,
                "message": f"Auto-click performed: {result.get('result', 'Success')}"
            }
        else:
            return {
                "success": False,
                "message": f"Failed to execute click: {response.status_code}"
            }
            
    except Exception as e:
        logger.error(f"❌ Auto-click error: {e}")
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }

def take_browser_screenshot():
    """Take screenshot of virtual browser"""
    try:
        if not BROWSERLESS_TOKEN:
            return None
        
        screenshot_url = f"{BROWSERLESS_API}/screenshot?token={BROWSERLESS_TOKEN}"
        payload = {
            "options": {
                "fullPage": True,
                "type": "png"
            }
        }
        
        response = requests.post(screenshot_url, json=payload, timeout=30)
        
        if response.status_code == 200:
            return response.content
        else:
            logger.error(f"Screenshot failed: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"Screenshot error: {e}")
        return None

# Flask Routes
@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/start_browser')
def start_browser():
    """Start virtual browser session"""
    result = start_virtual_browser()
    return jsonify(result)

@app.route('/auto_click')
def perform_auto_click():
    """Perform auto-click in browser"""
    result = auto_click_reconnect()
    return jsonify(result)

@app.route('/screenshot')
def screenshot():
    """Get browser screenshot"""
    screenshot_data = take_browser_screenshot()
    if screenshot_data:
        return send_file(
            BytesIO(screenshot_data),
            mimetype='image/png',
            as_attachment=True,
            download_name='colab_screenshot.png'
        )
    else:
        # Return placeholder
        return "No screenshot available", 404

@app.route('/status')
def status():
    uptime_seconds = time.time() - start_time
    return jsonify({
        'status': 'active' if stats['browser_sessions'] > 0 else 'inactive',
        'uptime': int(uptime_seconds),
        'colab_url': COLAB_URL,
        'stats': stats,
        'start_time': session_start.isoformat(),
        'browserless_configured': bool(BROWSERLESS_TOKEN)
    })

@app.route('/keep_alive')
def keep_alive():
    """Simple endpoint to keep Render awake"""
    return jsonify({
        'alive': True,
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    logger.info(f"🚀 Colab 24/7 Virtual Browser Service")
    logger.info(f"📌 Colab URL: {COLAB_URL}")
    logger.info(f"🌐 Browserless API: {'Configured' if BROWSERLESS_TOKEN else 'Not configured'}")
    
    # Start a browser session automatically
    if BROWSERLESS_TOKEN:
        logger.info("🔄 Starting virtual browser automatically...")
        Thread(target=start_virtual_browser, daemon=True).start()
    
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
