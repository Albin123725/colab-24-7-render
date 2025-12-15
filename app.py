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
from threading import Thread, Lock, Timer
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

# Browserless API (Virtual browser service) - USING YOUR TOKEN!
BROWSERLESS_API = "https://chrome.browserless.io"
BROWSERLESS_TOKEN = "2TblDXmlzjAZKPE6ae95231b83bb3c4112c62fce83c993b43"  # Your token!

# Global variables
browser_session = None
lock = Lock()
start_time = time.time()
session_start = datetime.now()
stats = {
    'browser_sessions': 0,
    'colab_pings': 0,
    'auto_clicks': 0,
    'errors': 0,
    'last_action': None,
    'session_active': False
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
        .header p {
            color: #636e72;
            font-size: 1.1em;
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
        .info-box {
            background: #ffeaa7;
            border: 2px solid #fdcb6e;
            border-radius: 12px;
            padding: 20px;
            margin: 20px 0;
        }
        .stat-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        .stat-box {
            background: white;
            padding: 15px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 3px 10px rgba(0,0,0,0.1);
        }
        .stat-number {
            font-size: 24px;
            font-weight: bold;
            color: #0984e3;
        }
        .stat-label {
            color: #636e72;
            font-size: 14px;
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Colab 24/7 - Render Hosted Browser</h1>
            <p>Colab runs in virtual browser on Render - Works even when your laptop is closed!</p>
        </div>
        
        <div class="info-box">
            <strong>✅ READY TO GO!</strong> Your Browserless token is configured. 
            Colab will run in a cloud browser 24/7 on Render servers.
        </div>
        
        <div class="status-grid">
            <div class="status-card" id="statusCard">
                <h3>VIRTUAL BROWSER STATUS</h3>
                <div class="status-value" id="statusText" style="font-size: 28px; font-weight: bold; color: #d63031;">INACTIVE</div>
                <p>Colab URL: <span id="colabUrl">''' + COLAB_URL + '''</span></p>
                <p>Session ID: <span id="sessionId">None</span></p>
            </div>
            
            <div class="status-card">
                <h3>ACTIVITY STATS</h3>
                <div class="stat-grid">
                    <div class="stat-box">
                        <div class="stat-number" id="sessions">0</div>
                        <div class="stat-label">Sessions</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number" id="clicks">0</div>
                        <div class="stat-label">Auto-Clicks</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number" id="pings">0</div>
                        <div class="stat-label">Pings</div>
                    </div>
                </div>
                <p>Last Action: <span id="lastAction">Never</span></p>
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
            <button class="btn" onclick="restartSession()" style="background: #00cec9; color: white;">
                <span>⚡</span> Restart Session
            </button>
        </div>
        
        <div class="logs" id="logs">
            [Logs will appear here...]
        </div>
    </div>
    
    <script>
        let currentSessionId = null;
        
        function startBrowser() {
            showLoading('Starting virtual browser...');
            fetch('/start_browser')
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        currentSessionId = data.session_id;
                        document.getElementById('colabFrame').src = data.view_url;
                        document.getElementById('statusText').textContent = 'ACTIVE';
                        document.getElementById('statusText').style.color = '#00b894';
                        document.getElementById('sessionId').textContent = data.session_id;
                        updateLog(`✅ Virtual browser started: ${data.session_id}`);
                        
                        // Start auto-ping
                        startAutoPing();
                    } else {
                        updateLog(`❌ Error: ${data.error}`);
                        alert('Error: ' + data.error);
                    }
                })
                .catch(err => {
                    updateLog(`❌ Failed to start: ${err}`);
                    alert('Failed to start browser: ' + err);
                })
                .finally(() => hideLoading());
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
                })
                .catch(err => {
                    updateLog(`❌ Screenshot failed: ${err}`);
                });
        }
        
        function autoClick() {
            fetch('/auto_click')
                .then(r => r.json())
                .then(data => {
                    updateLog(`🤖 ${data.message}`);
                })
                .catch(err => {
                    updateLog(`❌ Auto-click failed: ${err}`);
                });
        }
        
        function refreshBrowser() {
            if (document.getElementById('colabFrame').src !== 'about:blank') {
                document.getElementById('colabFrame').src = 
                    document.getElementById('colabFrame').src;
                updateLog('🔄 Browser refreshed');
            }
        }
        
        function restartSession() {
            if (confirm('Restart browser session?')) {
                fetch('/restart_session')
                    .then(r => r.json())
                    .then(data => {
                        if (data.success) {
                            startBrowser();
                        }
                    });
            }
        }
        
        function startAutoPing() {
            // Ping every 30 seconds to keep alive
            setInterval(() => {
                fetch('/ping')
                    .then(r => r.json())
                    .then(data => {
                        if (data.success) {
                            updateLog(`📡 Ping: ${data.message}`);
                        }
                    });
            }, 30000);
            
            // Auto-click every 5 minutes
            setInterval(() => {
                autoClick();
            }, 300000);
        }
        
        function updateLog(message) {
            const logs = document.getElementById('logs');
            const time = new Date().toLocaleTimeString();
            logs.innerHTML = `<span style="color: #81ecec">[${time}]</span> ${message}<br>` + logs.innerHTML;
            logs.scrollTop = 0;
        }
        
        function showLoading(message) {
            updateLog(`⏳ ${message}`);
        }
        
        function hideLoading() {
            // Nothing to hide
        }
        
        // Auto-start on page load
        window.onload = function() {
            setTimeout(startBrowser, 2000);
        };
        
        // Update stats every 3 seconds
        setInterval(() => {
            fetch('/status')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('sessions').textContent = data.stats.browser_sessions;
                    document.getElementById('clicks').textContent = data.stats.auto_clicks;
                    document.getElementById('pings').textContent = data.stats.colab_pings;
                    document.getElementById('lastAction').textContent = data.stats.last_action || 'Never';
                    
                    // Update status color
                    const statusText = document.getElementById('statusText');
                    if (data.status === 'active') {
                        statusText.style.color = '#00b894';
                    } else {
                        statusText.style.color = '#d63031';
                    }
                })
                .catch(err => console.error('Status update error:', err));
        }, 3000);
    </script>
</body>
</html>
'''

def start_virtual_browser():
    """Start a virtual browser session on Browserless"""
    global stats, browser_session
    
    try:
        # Browserless API endpoint
        browserless_url = f"{BROWSERLESS_API}/content?token={BROWSERLESS_TOKEN}"
        
        # Prepare request
        payload = {
            "url": COLAB_URL,
            "gotoOptions": {
                "waitUntil": "networkidle0",
                "timeout": 60000  # 60 second timeout
            },
            "setViewport": {
                "width": 1920,
                "height": 1080
            },
            "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "stealth": True
        }
        
        logger.info(f"🚀 Starting virtual browser for: {COLAB_URL}")
        
        # Start browser session
        response = requests.post(
            browserless_url,
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            stats['browser_sessions'] += 1
            stats['last_action'] = f"Browser started at {datetime.now().strftime('%H:%M:%S')}"
            stats['session_active'] = True
            
            # Get session ID from response
            session_data = response.json()
            session_id = session_data.get('id', f'session_{int(time.time())}')
            browser_session = session_id
            
            logger.info(f"✅ Virtual browser started: {session_id}")
            logger.info(f"🔗 View URL: https://chrome.browserless.io/session/{session_id}")
            
            # Start auto-maintenance thread
            Thread(target=auto_maintenance, args=(session_id,), daemon=True).start()
            
            return {
                "success": True,
                "session_id": session_id,
                "view_url": f"https://chrome.browserless.io/session/{session_id}",
                "screenshot_url": f"{BROWSERLESS_API}/screenshot?token={BROWSERLESS_TOKEN}&sessionId={session_id}"
            }
        else:
            error_msg = f"Browserless API error: {response.status_code} - {response.text}"
            logger.error(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }
            
    except Exception as e:
        error_msg = f"Failed to start browser: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return {
            "success": False,
            "error": error_msg
        }

def auto_maintenance(session_id):
    """Auto-maintenance for browser session"""
    global stats
    
    try:
        while stats['session_active']:
            # Ping every 30 seconds
            time.sleep(30)
            
            # Send keep-alive ping
            try:
                ping_url = f"{BROWSERLESS_API}/content?token={BROWSERLESS_TOKEN}"
                payload = {
                    "url": "about:blank",
                    "sessionId": session_id,
                    "gotoOptions": {"timeout": 5000}
                }
                
                response = requests.post(ping_url, json=payload, timeout=10)
                if response.status_code == 200:
                    stats['colab_pings'] += 1
                    logger.info(f"📡 Keep-alive ping #{stats['colab_pings']}")
                else:
                    logger.warning(f"⚠️ Ping failed: {response.status_code}")
                    
            except Exception as e:
                logger.warning(f"⚠️ Ping error: {e}")
                
            # Auto-click every 5 minutes
            if stats['colab_pings'] % 10 == 0:  # Every 10 pings = 5 minutes
                auto_click_reconnect(session_id)
                
    except Exception as e:
        logger.error(f"❌ Maintenance error: {e}")

def auto_click_reconnect(session_id=None):
    """Automatically click reconnect/run buttons in Colab"""
    global stats
    
    try:
        # JavaScript to auto-click buttons
        click_script = """
        function autoClickColab() {
            console.log('🤖 Auto-click script running...');
            
            // Click reconnect button
            const reconnect = document.querySelector('[aria-label="Reconnect"], [aria-label="Connect"]');
            if (reconnect) {
                reconnect.click();
                console.log('Clicked reconnect button');
                
                // Wait and click run
                setTimeout(() => {
                    const runBtn = document.querySelector('[aria-label="Run all"]');
                    if (runBtn) {
                        runBtn.click();
                        console.log('Clicked run button');
                        return 'reconnected_and_ran';
                    }
                }, 5000);
                return 'reconnected';
            }
            
            // Click run button
            const runBtn = document.querySelector('[aria-label="Run all"]');
            if (runBtn) {
                runBtn.click();
                console.log('Clicked run button');
                return 'ran';
            }
            
            console.log('No buttons found to click');
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
        
        if session_id:
            payload["sessionId"] = session_id
        
        response = requests.post(execute_url, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            stats['auto_clicks'] += 1
            stats['last_action'] = f"Auto-click at {datetime.now().strftime('%H:%M:%S')}"
            
            action = result.get('result', 'unknown')
            logger.info(f"✅ Auto-click executed: {action}")
            return {
                "success": True,
                "message": f"Auto-click performed: {action}"
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
        screenshot_url = f"{BROWSERLESS_API}/screenshot?token={BROWSERLESS_TOKEN}"
        payload = {
            "options": {
                "fullPage": False,
                "type": "png",
                "quality": 90
            }
        }
        
        response = requests.post(screenshot_url, json=payload, timeout=30)
        
        if response.status_code == 200:
            return response.content
        else:
            logger.error(f"❌ Screenshot failed: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Screenshot error: {e}")
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

@app.route('/restart_session')
def restart_session():
    """Restart browser session"""
    global stats
    stats['session_active'] = False
    time.sleep(2)
    result = start_virtual_browser()
    return jsonify(result)

@app.route('/screenshot')
def screenshot():
    """Get browser screenshot"""
    screenshot_data = take_browser_screenshot()
    if screenshot_data:
        return send_file(
            BytesIO(screenshot_data),
            mimetype='image/png',
            as_attachment=False,
            download_name='colab_screenshot.png'
        )
    else:
        # Return placeholder image
        from PIL import Image, ImageDraw
        img = Image.new('RGB', (800, 400), color='#2d3436')
        d = ImageDraw.Draw(img)
        d.text((400, 200), "No screenshot available\nBrowser may be loading", 
               fill='white', anchor='mm', align='center')
        
        img_io = BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        
        return send_file(img_io, mimetype='image/png')

@app.route('/ping')
def ping():
    """Keep-alive ping"""
    stats['colab_pings'] += 1
    return jsonify({
        "success": True,
        "message": f"Ping #{stats['colab_pings']} at {datetime.now().strftime('%H:%M:%S')}"
    })

@app.route('/status')
def status():
    uptime_seconds = time.time() - start_time
    return jsonify({
        'status': 'active' if stats['session_active'] else 'inactive',
        'uptime': int(uptime_seconds),
        'colab_url': COLAB_URL,
        'stats': stats,
        'start_time': session_start.isoformat(),
        'browserless_token': 'configured' if BROWSERLESS_TOKEN else 'missing',
        'current_session': browser_session
    })

@app.route('/keep_alive')
def keep_alive():
    """Simple endpoint to keep Render awake"""
    return jsonify({
        'alive': True,
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    logger.info("=" * 70)
    logger.info("🚀 COLAB 24/7 VIRTUAL BROWSER SERVICE")
    logger.info("=" * 70)
    logger.info(f"📌 Colab URL: {COLAB_URL}")
    logger.info(f"🔑 Browserless Token: {'✅ CONFIGURED' if BROWSERLESS_TOKEN else '❌ MISSING'}")
    logger.info("⚡ Service starting...")
    
    # Start browser session automatically
    if BROWSERLESS_TOKEN:
        logger.info("🔄 Starting virtual browser automatically in 5 seconds...")
        def auto_start():
            result = start_virtual_browser()
            if result.get('success'):
                logger.info(f"✅ Browser started: {result.get('session_id')}")
            else:
                logger.error(f"❌ Failed to start: {result.get('error')}")
        
        Timer(5, auto_start).start()
    else:
        logger.error("❌ Browserless token not configured! Get free token from browserless.io")
    
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
