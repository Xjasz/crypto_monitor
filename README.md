# 🔍 Crypto Social Media Monitor

Monitors posts on **Twitter (X)** and **Truth Social** in real-time for crypto-related keywords from a list of specified accounts. Sends out **instant alerts via email and SMS/MMS** when matches are detected.

---

## ⚙️ What It Does

- Scrapes recent posts from specified **Twitter/X** and **Truth Social** accounts.
- Searches each post for a list of predefined **crypto keywords** (e.g., BTC, ETH, XRP, DOGE, etc.).
- Prevents duplicate alerts by maintaining a history of already-flagged content in `found_posts.txt`.
- Sends **email** and/or **SMS** alerts if any crypto-related term is detected.
- Logs all activity and matches in `crypto_monitor_log.txt`.
- Can optionally check your phone's **SMS/MMS carrier gateway** to determine where alerts can be delivered.

---

## 🛠️ Features

- ✅ Monitors Twitter and Truth Social accounts
- ✅ Customizable crypto keyword detection
- ✅ Email and MMS alerting (via SMTP)
- ✅ Automatic post deduplication
- ✅ Adjustable headless browser config (via Firefox + Selenium)
- ✅ Simple carrier testing mode (for verifying delivery)
- ✅ Lightweight and extensible

---

## 🔧 Requirements

Install dependencies with:

```bash
pip install -r requirements.txt
```

**Required:**
- Python 3.9+
- Firefox Browser 
- GeckoDriver (for Selenium) https://github.com/mozilla/geckodriver/releases

Optional but recommended:
- Email SMTP credentials for notifications
- A verified MMS gateway (e.g. your_phone_number@carrier.com)

---

## 🚀 Usage

### 1. Environment Variables

Set the following environment variables before running the script:

```bash
export GECKO_EXE_LOC="/path/to/geckodriver"
export BROWSER_EXE_LOC="/path/to/firefox"
export BROWSER_PROFILE_DIR="/your/firefox/profile"
export EMAIL_SENDER="your_email@example.com"
export EMAIL_PASSWORD="your_email_password"
export EMAIL_SERVER="smtp.yourprovider.com"
```

For Windows:

```bat
set GECKO_EXE_LOC=C:\path\to\geckodriver.exe
set BROWSER_EXE_LOC=C:\Program Files\Mozilla Firefox\firefox.exe
set BROWSER_PROFILE_DIR=C:\Users\YourUser\AppData\Roaming\Mozilla\Firefox\Profiles\xyz.default-release
set EMAIL_SENDER=your_email@example.com
set EMAIL_PASSWORD=your_email_password
set EMAIL_SERVER=smtp.yourprovider.com
```

---

### 2. Configuration

You can customize:
- `CRYPTO_KEYWORDS` → Keywords to scan for
- `TWITTER_ACCOUNTS` & `TRUTH_SOCIAL_ACCOUNTS` → Target handles
- `EMAIL_RECIPIENTS` → Email alert destinations
- `PHONE_NUMBERS` → SMS/MMS alert destinations

Edit these directly in `crypto_monitor.py`.

---

### 3. Run the Monitor

```bash
python crypto_monitor.py
```

The script will log activity, trigger alerts on matches, and rotate through the accounts you’ve specified.

---

## 🧪 Optional: SMS Carrier Check

If you're unsure of the correct email-to-text gateway for your number, enable this flag in the script:

```python
CHECK_CARRIER = True
```

Then run the script once. It will attempt to send messages to all known U.S. carrier gateways. You'll receive a test message from the one that works.

---

## 📁 Output

- ✅ **`crypto_monitor_log.txt`** – Full execution log
- ✅ **`found_posts.txt`** – Prevents redundant alerts
- ✅ **Email/SMS** – Instant keyword detection alerts

