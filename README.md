# 🎮 Colab Minecraft 24/7 Auto-Restart

Keeps your Google Colab Minecraft server running 24/7 with auto-reconnect.

## Features
- ✅ Auto-detects when Colab runtime disconnects
- ✅ Auto-clicks "Reconnect" and "Run" buttons
- ✅ Beautiful web interface for monitoring
- ✅ Live screenshots of Colab page
- ✅ Works 24/7 on Render.com free tier

## Quick Deployment

1. **Create GitHub repository** with these files
2. **Go to [render.com](https://render.com)**
3. **Click "New +" → "Web Service"**
4. **Connect your GitHub repository**
5. **Configure:**
   - Name: `colab-minecraft-24-7`
   - Environment: `Python`
   - Build Command: (from render.yaml)
   - Start Command: `python app.py`
   - Plan: `Free`
6. **Click "Create Web Service"**

## First-Time Setup

1. After deployment, visit your Render URL
2. Click **"Login Setup"** button
3. Open Colab and login with Google
4. Return to main page
5. Click **"Start Monitoring"**

## Keep It Awake (IMPORTANT!)

Render free tier sleeps after 15 minutes of no traffic.
Set up **UptimeRobot** (free):

1. Go to [uptimerobot.com](https://uptimerobot.com)
2. Add monitor for your Render URL
3. Set to ping every 5 minutes
4. This prevents Render from sleeping

## Monitor Your Minecraft Server

Visit your Render URL to see:
- ✅ Live status of monitor
- 📊 Reconnect statistics
- 🖼️ Live screenshot of Colab
- 📜 Real-time logs

## Troubleshooting

**Q: Monitor shows "Login required"**
A: Click "Login Setup" and login manually

**Q: Screenshot not showing**
A: Wait 30 seconds for first screenshot

**Q: Colab still disconnects**
A: Make sure UptimeRobot is pinging your Render URL

## Support
For issues, check the logs at `/get_logs` endpoint
