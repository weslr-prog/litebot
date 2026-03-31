# Notification & Alert System Options

**Question:** "Is there a way to set triggers for the bot so that it sends a message to the chat to investigate and fix it?"

---

## Short Answer

**VSCode Chat Limitations:** GitHub Copilot Chat cannot receive automated alerts from your bot. The chat is session-based and only responds when you actively message it.

**Solution:** Use external notification systems (email, SMS, messaging apps) that can send alerts to your phone/email while you're at work.

---

## Recommended Options (Ordered by Simplicity)

### Option 1: Email Alerts (EASIEST)
Send email to yourself when critical events occur.

**Pros:**
- ✅ Free and simple
- ✅ Works on any phone/device
- ✅ Can set up Gmail filters to mark as urgent
- ✅ No additional services needed

**Cons:**
- ⚠️ Might go to spam (can be fixed)
- ⚠️ Requires SMTP credentials in code

**Setup:**
```python
# bot_v2/utils/alerts.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email_alert(subject, message):
    """Send email alert for critical events"""
    sender_email = "your_email@gmail.com"
    sender_password = "your_app_password"  # Use Gmail app password
    receiver_email = "your_phone_number@txt.att.net"  # SMS via email gateway
    
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = f"🤖 Bot Alert: {subject}"
    msg.attach(MIMEText(message, 'plain'))
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Alert failed: {e}")
        return False

# Usage in bot:
send_email_alert("No Trades Today", "Bot has not made any trades for 2+ hours")
send_email_alert("Critical Error", "Bot crashed with exception: {error}")
send_email_alert("Positions Stuck", "12 positions failed to exit at 10 AM")
```

**Email-to-SMS Gateways:**
- AT&T: `phonenumber@txt.att.net`
- Verizon: `phonenumber@vtext.com`
- T-Mobile: `phonenumber@tmomail.net`
- Sprint: `phonenumber@messaging.sprintpcs.com`

---

### Option 2: Telegram Bot (RECOMMENDED)
Free messaging app with bot API - get instant notifications on your phone.

**Pros:**
- ✅ Free and reliable
- ✅ Instant push notifications
- ✅ Can send from anywhere in the world
- ✅ Easy API, no SMTP setup
- ✅ Can include formatted messages and logs

**Cons:**
- ⚠️ Requires creating Telegram account + bot
- ⚠️ 5-minute setup time

**Setup:**
1. Install Telegram on your phone
2. Message [@BotFather](https://t.me/botfather) to create a bot
3. Get your bot token (looks like: `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)
4. Get your chat ID (message [@userinfobot](https://t.me/userinfobot))

```python
# bot_v2/utils/alerts.py
import requests

TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN"
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID"

def send_telegram_alert(message):
    """Send Telegram alert"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload)
        return response.status_code == 200
    except Exception as e:
        print(f"Telegram alert failed: {e}")
        return False

# Usage:
send_telegram_alert("🤖 *Bot Alert*\n\n12 positions exited successfully\n$483 buying power freed")
send_telegram_alert("⚠️ *Critical Error*\nBot crashed at 10:15 AM\nError: NoneType...")
```

---

### Option 3: Discord Webhook (DEVELOPER FRIENDLY)
Free, no phone number needed, works great for technical alerts.

**Pros:**
- ✅ Free
- ✅ No phone number required
- ✅ Rich formatting (embeds, colors)
- ✅ Extremely simple setup (just a URL)

**Cons:**
- ⚠️ Requires Discord account
- ⚠️ Need to check Discord app (not SMS)

**Setup:**
1. Create Discord server (or use existing)
2. Create a channel (e.g., "bot-alerts")
3. Edit channel → Integrations → Webhooks → New Webhook
4. Copy webhook URL

```python
# bot_v2/utils/alerts.py
import requests

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_TOKEN"

def send_discord_alert(title, message, color="red"):
    """Send Discord alert with embed"""
    colors = {"red": 16711680, "green": 65280, "yellow": 16776960}
    
    payload = {
        "embeds": [{
            "title": f"🤖 {title}",
            "description": message,
            "color": colors.get(color, 16711680),
            "timestamp": datetime.datetime.utcnow().isoformat()
        }]
    }
    
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        return response.status_code == 204
    except Exception as e:
        print(f"Discord alert failed: {e}")
        return False

# Usage:
send_discord_alert("Positions Exited", "12 positions sold successfully", color="green")
send_discord_alert("Critical Error", "Bot crashed with exception", color="red")
```

---

### Option 4: Twilio SMS (PROFESSIONAL)
Real SMS to your phone, very reliable but costs money.

**Pros:**
- ✅ Real SMS (works without internet)
- ✅ Most reliable
- ✅ Professional service

**Cons:**
- ❌ Costs money (~$1/month + $0.0075 per SMS)
- ⚠️ Requires Twilio account + credit card

**Setup:**
```python
# pip install twilio
from twilio.rest import Client

def send_sms_alert(message):
    account_sid = "YOUR_ACCOUNT_SID"
    auth_token = "YOUR_AUTH_TOKEN"
    client = Client(account_sid, auth_token)
    
    message = client.messages.create(
        body=message,
        from_='+1234567890',  # Your Twilio number
        to='+1987654321'       # Your phone number
    )
    return message.sid
```

---

## Alert Integration - Where to Add Alerts

Add alerts to these critical points in `bot_v2/launcher.py`:

### 1. Bot Startup
```python
def __init__(self):
    # ... existing code ...
    self.logger.info("✅ All modules initialized successfully")
    send_alert("Bot Started", f"Bot initialized at {datetime.now()}")
```

### 2. Critical Errors
```python
except Exception as e:
    self.logger.error(f"Critical error in main loop: {e}", exc_info=True)
    send_alert("Critical Error", f"Bot crashed: {str(e)}")
    time.sleep(60)
```

### 3. No Activity Watchdog
```python
def _monitor_exits(self):
    # Track last activity
    if not hasattr(self, '_last_trade_time'):
        self._last_trade_time = datetime.now()
    
    # Alert if no activity for 2 hours during market hours
    if self._is_market_hours() and (datetime.now() - self._last_trade_time).seconds > 7200:
        send_alert("No Activity Warning", "Bot has not traded for 2+ hours")
        self._last_trade_time = datetime.now()  # Reset to avoid spam
```

### 4. Position Exit Success/Failure
```python
def _monitor_exits(self):
    # ... existing code ...
    for position in active_positions:
        should_exit, reason = self.exit_manager.should_exit(position)
        if should_exit:
            success = self.order_manager.execute_sell_order(position, reason)
            if success:
                send_alert("Position Exited", f"✅ {position.symbol} sold: {reason}")
            else:
                send_alert("Exit Failed", f"⚠️ {position.symbol} failed to exit: {reason}")
```

### 5. Daily Summary (End of Day)
```python
def _postmarket_summary(self):
    summary = f"""
📊 Daily Trading Summary - {datetime.now().date()}

Positions Entered: {self.stats.entries_today}
Positions Exited: {self.stats.exits_today}
Win Rate: {self.stats.win_rate:.1%}
P&L Today: ${self.stats.pnl_today:.2f}

Active Positions: {len(self.position_tracker.get_active_positions())}
Portfolio Value: ${self.config.portfolio_value:.2f}
"""
    send_alert("Daily Summary", summary)
```

---

## Simple Implementation Plan

If you want me to implement this, here's the easiest approach:

### Step 1: Choose Your Method
- **For work:** Telegram or Email (instant notifications)
- **For technical logs:** Discord
- **For critical only:** SMS via email gateway (free)

### Step 2: Create Alert Module
I'll create `bot_v2/utils/alert_system.py` with your chosen method(s)

### Step 3: Add Alert Points
Add 4-5 critical alert points:
1. Bot startup confirmation
2. Critical errors (crashes)
3. Position exit failures (stuck positions)
4. No activity for 2+ hours
5. End-of-day summary

### Step 4: Test
Send a test alert to verify it works

---

## My Recommendation

**For tomorrow (Dec 17):** Use **Email-to-SMS** gateway for immediate setup:
- ✅ No accounts to create
- ✅ Free
- ✅ Can set up in 2 minutes
- ✅ You'll get texts about critical events

**For long-term:** Switch to **Telegram** for better reliability:
- ✅ Cleaner interface
- ✅ More reliable than email
- ✅ Can send formatted logs
- ✅ Can query bot status by messaging the bot

---

## Quick Setup (Email-to-SMS)

Want me to implement email alerts right now? I just need:
1. Your email address (e.g., `your_email@gmail.com`)
2. Your carrier and phone number for SMS gateway
3. Create a Gmail "App Password" (not your regular password)

I can have this working in 5 minutes with alerts for:
- ✅ Bot started successfully
- ✅ Positions exited (or failed to exit)
- ✅ Critical errors/crashes
- ✅ End of day summary

---

## Can't Use VSCode Chat for Alerts

Unfortunately, there's no way to have the bot send messages directly to this chat because:
- GitHub Copilot Chat is **read-only** from external programs
- No API to send messages to an active chat session
- Chat sessions are temporary and don't persist

The bot would need an **outbound** communication channel (email, SMS, messaging app) rather than trying to communicate through the IDE.

---

## Want Me to Implement This?

Let me know:
1. Which method you prefer (Telegram recommended, Email-SMS easiest)
2. I'll add the alert system with 4-5 critical alert points
3. Test it before tomorrow morning

This way you'll get notifications at work if anything goes wrong or to confirm the 12 positions exited successfully.
