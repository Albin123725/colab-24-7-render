import os
import time
import json
import logging
import traceback
import random
from datetime import datetime
from threading import Thread, Lock
from flask import Flask, render_template_string, jsonify, request, send_file

# Try to import undetected_chromedriver, fallback to regular selenium
try:
    import undetected_chromedriver as uc
    USE_UNDETECTED = True
except ImportError as e:
    print(f"Warning: undetected_chromedriver not available: {e}")
    print("Falling back to regular selenium...")
    USE_UNDETECTED = False
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# ============================================================================
# CONFIGURATION
# ============================================================================

# Your Colab URL - CHANGE THIS
COLAB_URL = os.environ.get('COLAB_URL', 'https://colab.research.google.com/drive/1jckV8xUJSmLhhol6wZwVJzpybsimiRw1')

# Flask App
app = Flask(__name__)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('colab_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Global variables
driver = None
monitoring = False
lock = Lock()
start_time = time.time()
session_start = datetime.now()
stats = {
    'reconnect_count': 0,
    'run_count': 0,
    'errors': 0,
    'last_action': None,
    'last_success': None
}

# ============================================================================
# HTML INTERFACE
# ============================================================================

HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>🎮 Colab 24/7 Auto-Restart</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            color: #333;
        }
        .container {
            max-width: 1200px;
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
            font-size: 2.8em;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 15px;
        }
        .header p {
            color: #636e72;
            font-size: 1.2em;
        }
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .status-card {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            transition: transform 0.3s, box-shadow 0.3s;
        }
        .status-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 25px rgba(0,0,0,0.15);
        }
        .status-card.running { border-left: 5px solid #00b894; }
        .status-card.stopped { border-left: 5px solid #d63031; }
        .status-card.warning { border-left: 5px solid #fdcb6e; }
        .status-label { color: #636e72; font-size: 0.9em; margin-bottom: 5px; }
        .status-value {
            font-size: 1.8em;
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
            min-width: 200px;
            justify-content: center;
        }
        .btn-start { background: #00b894; color: white; }
        .btn-stop { background: #d63031; color: white; }
        .btn-restart { background: #0984e3; color: white; }
        .btn-refresh { background: #6c5ce7; color: white; }
        .btn-login { background: #fdcb6e; color: #2d3436; }
        .btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 7px 20px rgba(0,0,0,0.2);
        }
        .btn:active { transform: translateY(-1px); }
        .logs-container {
            background: #2d3436;
            color: #dfe6e9;
            padding: 20px;
            border-radius: 15px;
            margin-top: 30px;
            max-height: 400px;
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
        .screenshot-container {
            text-align: center;
            margin: 30px 0;
            padding: 20px;
            background: white;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        .screenshot {
            max-width: 100%;
            border-radius: 10px;
            border: 3px solid #dfe6e9;
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        .info-box {
            background: #ffeaa7;
            border: 2px solid #fdcb6e;
            border-radius: 12px;
            padding: 20px;
            margin: 20px 0;
            display: flex;
            align-items: center;
            gap: 15px;
        }
        .info-icon { font-size: 24px; }
        .info-text { flex: 1; }
        .action-history {
            background: white;
            padding: 20px;
            border-radius: 15px;
            margin-top: 20px;
        }
        .action-item {
            padding: 10px;
            border-left: 4px solid #74b9ff;
            margin: 10px 0;
            background: #f9f9f9;
        }
        .last-update {
            text-align: center;
            margin-top: 20px;
            color: #636e72;
            font-size: 0.9em;
        }
        @media (max-width: 768px) {
            .container { padding: 15px; }
            .btn { min-width: 100%; }
            .status-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎮 Colab 24/7 Auto-Restart</h1>
            <p>Keep your Minecraft Colab running continuously with auto-reconnect</p>
        </div>
        
        <div class="info-box">
            <div class="info-icon">⚠️</div>
            <div class="info-text">
                <strong>First-time setup:</strong> Click "Login Setup" to authenticate with Google. 
                After login, return here and click "Start Monitoring".
            </div>
        </div>
        
        <div class="status-grid">
            <div class="status-card" id="statusCard">
                <div class="status-label">MONITOR STATUS</div>
                <div class="status-value" id="statusText">STOPPED</div>
                <div class="status-label" id="statusDetail">Not monitoring</div>
            </div>
            
            <div class="status-card">
                <div class="status-label">UPTIME</div>
                <div class="status-value" id="uptime">00:00:00</div>
                <div class="status-label">Since <span id="startTime">--:--:--</span></div>
            </div>
            
            <div class="status-card">
                <div class="status-label">RECONNECTS</div>
                <div class="status-value" id="reconnectCount">0</div>
                <div class="status-label">Auto-reconnect attempts</div>
            </div>
            
            <div class="status-card">
                <div class="status-label">LAST ACTION</div>
                <div class="status-value" id="lastAction">None</div>
                <div class="status-label" id="lastActionTime">Never</div>
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
            <button class="btn btn-login" onclick="window.open('/setup_login', '_blank')">
                <span>🔐</span> Login Setup
            </button>
            <button class="btn btn-refresh" onclick="location.reload()">
                <span>↻</span> Refresh
            </button>
        </div>
        
        <div class="screenshot-container">
            <h3>Live Screenshot</h3>
            <img id="screenshot" src="/screenshot" class="screenshot" 
                 alt="Screenshot loading..." 
                 onerror="this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iODAwIiBoZWlnaHQ9IjQwMCI+PHJlY3Qgd2lkdGg9IjgwMCIgaGVpZ2h0PSI0MDAiIGZpbGw9IiNmMGYwZjAiLz48dGV4dCB4PSI0MDAiIHk9IjIwMCIgZm9udC1mYW1pbHk9IkFyaWFsIiBmb250LXNpemU9IjI0IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmaWxsPSIjNjM2ZTIyIj5TY3JlZW5zaG90IHdpbGwgYXBwZWFyIGhlcmU8L3RleHQ+PC9zdmc+'">
            <p><small>Updates every 30 seconds. Shows current Colab page.</small></p>
        </div>
        
        <div class="action-history">
            <h3>Recent Actions</h3>
            <div id="actionHistory">
                <div class="action-item">No actions yet</div>
            </div>
        </div>
        
        <div class="logs-container">
            <h3>Live Logs</h3>
            <div id="logs">
                <div class="log-entry"><span class="log-time">[--:--:--]</span> <span class="log-info">Logs will appear here...</span></div>
            </div>
        </div>
        
        <div class="last-update" id="lastUpdate">
            Last updated: <span id="updateTime">--:--:--</span>
        </div>
    </div>
    
    <script>
        let actionHistory = [];
        
        function control(action) {
            fetch('/' + action)
                .then(r => r.text())
                .then(msg => {
                    showNotification(msg);
                    updateStatus();
                })
                .catch(err => showNotification('Error: ' + err, 'error'));
        }
        
        function showNotification(message, type = 'info') {
            alert(message);
            addAction(message);
        }
        
        function addAction(action) {
            const time = new Date().toLocaleTimeString();
            actionHistory.unshift({time, action});
            if (actionHistory.length > 10) actionHistory.pop();
            
            const historyDiv = document.getElementById('actionHistory');
            historyDiv.innerHTML = actionHistory.map(item => 
                `<div class="action-item"><strong>[${item.time}]</strong> ${item.action}</div>`
            ).join('');
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
                        statusCard.className = 'status-card running';
                    } else {
                        statusText.className = 'status-value stopped';
                        statusCard.className = 'status-card stopped';
                    }
                    
                    // Update uptime
                    document.getElementById('uptime').textContent = formatTime(data.uptime);
                    document.getElementById('startTime').textContent = new Date(data.start_time * 1000).toLocaleTimeString();
                    
                    // Update stats
                    document.getElementById('reconnectCount').textContent = data.stats.reconnect_count;
                    document.getElementById('lastAction').textContent = data.stats.last_action || 'None';
                    document.getElementById('lastActionTime').textContent = data.stats.last_action_time || 'Never';
                    
                    // Update screenshot with cache busting
                    const screenshot = document.getElementById('screenshot');
                    screenshot.src = '/screenshot?_=' + Date.now();
                    
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
        
        // Keep page alive
        setInterval(() => {
            if (document.hidden) return;
            // Simulate user activity
            document.dispatchEvent(new MouseEvent('mousemove', {
                view: window,
                bubbles: true,
                clientX: Math.random() * 100,
                clientY: Math.random() * 100
            }));
        }, 30000);
    </script>
</body>
</html>
'''

# ============================================================================
# BROWSER FUNCTIONS
# ============================================================================

def init_browser(headless=True):
    """Initialize Chrome browser with stealth settings"""
    try:
        logger.info("Initializing browser...")
        
        options = uc.ChromeOptions()
        
        # Essential for Render
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-software-rasterizer')
        
        # Window size
        options.add_argument('--window-size=1920,1080')
        
        # Stealth settings
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-features=VizDisplayCompositor')
        options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # User agents
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        
        options.add_argument(f'--user-agent={random.choice(user_agents)}')
        
        # Headless mode
        if headless:
            options.add_argument('--headless=new')
        
        # Additional arguments
        options.add_argument('--disable-web-security')
        options.add_argument('--allow-running-insecure-content')
        options.add_argument('--disable-notifications')
        options.add_argument('--disable-popup-blocking')
        options.add_argument('--disable-background-networking')
        options.add_argument('--disable-sync')
        
        # Create driver
        driver = uc.Chrome(
            options=options,
            version_main=120  # Use Chrome 120
        )
        
        # Stealth scripts
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": options.arguments[-1].split('=')[1] 
            if 'user-agent' in options.arguments[-1] 
            else user_agents[0]
        })
        
        driver.execute_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };
        """)
        
        logger.info("✅ Browser initialized successfully")
        return driver
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize browser: {e}")
        return None

def save_screenshot(driver, filename='/tmp/screenshot.png'):
    """Save screenshot of current page"""
    try:
        driver.save_screenshot(filename)
        return True
    except Exception as e:
        logger.error(f"Screenshot failed: {e}")
        return False

def check_colab_status(driver):
    """Check if Colab needs restart and perform actions"""
    try:
        # Get page source
        page_source = driver.page_source.lower()
        
        # Check for various status indicators
        status_indicators = {
            'disconnected': ['runtime disconnected', 'not connected', 'disconnected', 'session ended'],
            'reconnect': ['reconnect', 'connect to runtime', 'connect'],
            'stopped': ['stop', 'stopped', 'interrupt'],
            'running': ['running', 'connected', 'executing']
        }
        
        current_status = 'unknown'
        needs_action = False
        action = None
        
        # Determine current status
        for status, indicators in status_indicators.items():
            for indicator in indicators:
                if indicator in page_source:
                    current_status = status
                    break
        
        # Check for specific elements
        try:
            # Look for reconnect button
            reconnect_selectors = [
                '//button[contains(text(), "Reconnect")]',
                '//button[contains(text(), "Connect")]',
                '//div[contains(@aria-label, "Reconnect")]',
                '//div[contains(@aria-label, "Connect")]'
            ]
            
            for selector in reconnect_selectors:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    if elements and elements[0].is_displayed():
                        current_status = 'disconnected'
                        needs_action = True
                        action = 'reconnect'
                        break
                except:
                    continue
        except:
            pass
        
        # Check for run button
        if current_status == 'disconnected' or 'stopped' in current_status:
            try:
                run_selectors = [
                    '//colab-run-button[@label="Run all"]',
                    '//button[@aria-label="Run all"]',
                    '//button[contains(text(), "Run")]'
                ]
                
                for selector in run_selectors:
                    try:
                        elements = driver.find_elements(By.XPATH, selector)
                        if elements and elements[0].is_displayed():
                            needs_action = True
                            action = 'run'
                            break
                    except:
                        continue
            except:
                pass
        
        # Check for runtime indicator
        try:
            runtime_elements = driver.find_elements(By.XPATH, '//div[contains(text(), "Runtime")]')
            for element in runtime_elements:
                text = element.text.lower()
                if 'disconnect' in text or 'not connected' in text:
                    current_status = 'disconnected'
                    needs_action = True
        except:
            pass
        
        return {
            'status': current_status,
            'needs_action': needs_action,
            'action': action,
            'page_source': page_source[:500]  # First 500 chars for logging
        }
        
    except Exception as e:
        logger.error(f"Status check error: {e}")
        return {'status': 'error', 'needs_action': False, 'action': None}

def perform_action(driver, action):
    """Perform the required action on Colab"""
    try:
        if action == 'reconnect':
            # Try to find and click reconnect button
            reconnect_selectors = [
                (By.XPATH, '//button[contains(text(), "Reconnect")]'),
                (By.XPATH, '//button[contains(text(), "Connect")]'),
                (By.XPATH, '//div[contains(@aria-label, "Reconnect")]'),
                (By.XPATH, '//div[contains(@aria-label, "Connect")]')
            ]
            
            for by, selector in reconnect_selectors:
                try:
                    elements = driver.find_elements(by, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            logger.info("🔄 Clicking reconnect button")
                            element.click()
                            stats['reconnect_count'] += 1
                            stats['last_action'] = 'reconnect'
                            stats['last_action_time'] = datetime.now().isoformat()
                            return True
                except:
                    continue
        
        if action == 'run' or action == 'reconnect':
            # Try to find and click run button
            run_selectors = [
                (By.XPATH, '//colab-run-button[@label="Run all"]'),
                (By.XPATH, '//button[@aria-label="Run all"]'),
                (By.XPATH, '//button[contains(text(), "Run all")]'),
                (By.XPATH, '//button[contains(text(), "Run")]')
            ]
            
            for by, selector in run_selectors:
                try:
                    elements = driver.find_elements(by, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            logger.info("▶️ Clicking run button")
                            element.click()
                            stats['run_count'] += 1
                            stats['last_action'] = 'run'
                            stats['last_action_time'] = datetime.now().isoformat()
                            return True
                except:
                    continue
        
        return False
        
    except Exception as e:
        logger.error(f"Action error: {e}")
        return False

def colab_monitor():
    """Main monitoring function"""
    global driver, monitoring, stats
    
    logger.info("🚀 Starting Colab monitor...")
    
    while monitoring:
        try:
            # Initialize browser if needed
            if driver is None:
                driver = init_browser(headless=True)
                if driver is None:
                    logger.error("Failed to initialize browser")
                    time.sleep(30)
                    continue
            
            # Navigate to Colab
            logger.info(f"🌐 Navigating to: {COLAB_URL}")
            driver.get(COLAB_URL)
            
            # Wait for page load
            time.sleep(10)
            
            # Check for Google login
            if "accounts.google.com" in driver.current_url:
                logger.warning("🔐 Google login required")
                stats['last_action'] = 'login_required'
                stats['last_action_time'] = datetime.now().isoformat()
                
                # Try to handle login (simplified)
                time.sleep(5)
                save_screenshot(driver)
            
            # Main monitoring loop
            while monitoring and driver:
                try:
                    # Check Colab status
                    status_info = check_colab_status(driver)
                    
                    logger.info(f"📊 Status: {status_info['status']}")
                    
                    # Take screenshot periodically
                    if int(time.time()) % 30 == 0:
                        save_screenshot(driver)
                    
                    # Perform action if needed
                    if status_info['needs_action'] and status_info['action']:
                        success = perform_action(driver, status_info['action'])
                        if success:
                            logger.info(f"✅ Action performed: {status_info['action']}")
                            # Wait after action
                            time.sleep(10)
                    
                    # Refresh page periodically (every 30 minutes)
                    if int(time.time()) % 1800 == 0:
                        logger.info("🔄 Periodic refresh")
                        driver.refresh()
                        time.sleep(10)
                    
                    # Small delay between checks
                    time.sleep(15)
                    
                except Exception as e:
                    logger.error(f"Monitoring error: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"Main loop error: {e}")
            stats['errors'] += 1
            
            # Cleanup and retry
            try:
                if driver:
                    driver.quit()
            except:
                pass
            driver = None
            
            logger.info("🔄 Restarting browser in 30 seconds...")
            time.sleep(30)
    
    # Cleanup
    logger.info("🛑 Stopping monitor...")
    try:
        if driver:
            driver.quit()
    except:
        pass
    driver = None

# ============================================================================
# FLASK ROUTES
# ============================================================================

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/start')
def start():
    global monitoring
    with lock:
        if not monitoring:
            monitoring = True
            Thread(target=colab_monitor, daemon=True).start()
            return "✅ Colab monitor started! It will now keep your Minecraft server running 24/7."
        return "⚠️ Monitor is already running."

@app.route('/stop')
def stop():
    global monitoring
    with lock:
        monitoring = False
        return "⏹️ Colab monitor stopped."

@app.route('/restart')
def restart():
    global monitoring, driver
    with lock:
        monitoring = False
        time.sleep(2)
        
        # Cleanup driver
        try:
            if driver:
                driver.quit()
        except:
            pass
        driver = None
        
        # Restart
        monitoring = True
        Thread(target=colab_monitor, daemon=True).start()
        return "🔄 Colab monitor restarted!"

@app.route('/setup_login')
def setup_login():
    """Special endpoint for manual login setup"""
    try:
        # Create a simple login page
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Colab Login Setup</title>
            <style>
                body { font-family: Arial, sans-serif; padding: 40px; text-align: center; }
                .container { max-width: 600px; margin: 0 auto; }
                .steps { text-align: left; margin: 30px 0; }
                .step { margin: 15px 0; padding: 10px; background: #f0f0f0; border-radius: 5px; }
                .step-number { background: #4285f4; color: white; width: 30px; height: 30px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; margin-right: 10px; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔐 Colab Login Setup</h1>
                <p>Follow these steps to login to your Colab notebook:</p>
                
                <div class="steps">
                    <div class="step">
                        <span class="step-number">1</span>
                        Click the button below to open Colab
                    </div>
                    <div class="step">
                        <span class="step-number">2</span>
                        Login with your Google account when prompted
                    </div>
                    <div class="step">
                        <span class="step-number">3</span>
                        Wait for the page to load completely
                    </div>
                    <div class="step">
                        <span class="step-number">4</span>
                        Return to the main page and click "Start Monitoring"
                    </div>
                </div>
                
                <a href="''' + COLAB_URL + '''" target="_blank">
                    <button style="padding: 15px 30px; font-size: 18px; background: #4285f4; color: white; border: none; border-radius: 5px; cursor: pointer;">
                        🔓 Open Colab for Login
                    </button>
                </a>
                
                <p style="margin-top: 30px;">
                    <a href="/" style="color: #666; text-decoration: none;">← Return to main page</a>
                </p>
            </div>
        </body>
        </html>
        '''
    except Exception as e:
        return f"Error: {e}"

@app.route('/screenshot')
def screenshot():
    try:
        if os.path.exists('/tmp/screenshot.png'):
            return send_file('/tmp/screenshot.png', mimetype='image/png')
    except:
        pass
    # Return empty response
    return '', 204

@app.route('/status')
def status():
    uptime_seconds = time.time() - start_time
    status_text = 'running' if monitoring else 'stopped'
    detail = 'Monitoring Colab' if monitoring else 'Not monitoring'
    
    if driver is None and monitoring:
        detail = 'Initializing browser...'
    
    return jsonify({
        'status': status_text,
        'detail': detail,
        'uptime': int(uptime_seconds),
        'start_time': start_time,
        'colab_url': COLAB_URL,
        'stats': stats,
        'driver_active': driver is not None,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/get_logs')
def get_logs():
    try:
        with open('colab_monitor.log', 'r') as f:
            logs = f.read().split('\n')[-50:]  # Last 50 lines
        return '<br>'.join(logs)
    except:
        return "No logs available"

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'monitoring': monitoring
    })

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    # Start monitoring automatically
    monitoring = True
    monitor_thread = Thread(target=colab_monitor, daemon=True)
    monitor_thread.start()
    
    logger.info(f"🚀 Application started at {datetime.now()}")
    logger.info(f"📌 Monitoring Colab: {COLAB_URL}")
    
    # Run Flask
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
