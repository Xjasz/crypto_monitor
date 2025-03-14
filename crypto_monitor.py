import logging
import os
import re
import time
import pygame
from selenium import webdriver
from selenium.common import StaleElementReferenceException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

EMAIL_ENABLED = True

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='crypto_monitor_log.txt'
)

logger = logging.getLogger()
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
logger.addHandler(console_handler)

pygame.mixer.init()

CRYPTO_KEYWORDS = [
    "cryptocurrency", "bitcoin", "btc", "ltc", "ethereum", "eth", "litecoin","dogecoin", "shiba inu", "floki", "pepe", "dogwifhat", "cardano",
    "altcoin", "bnb", "xrp", "ripple", "sol", "trx", "tron", "xlm", "stellar", 'sell', 'sold', 'buy', 'bought',"ada","vechain", "algorand",
    "trumpcoin","freedom coin"
]

TWITTER_ACCOUNTS = [
    "elonmusk",
    "cz_binance",
    "WhiteHouse",
    "POTUS",
    "realDonaldTrump",
    "Pentosh1"
]

TRUTH_SOCIAL_ACCOUNTS = [
    "realDonaldTrump",
    "TuckerCarlson",
    "DonaldJTrumpJr"
]

GECKO_EXE_LOC = os.getenv('GECKO_EXE_LOC', '')
BROWSER_EXE_LOC = os.getenv('BROWSER_EXE_LOC', '')
BROWSER_PROFILE_DIR = os.getenv('BROWSER_PROFILE_DIR', '')
EMAIL_SENDER = os.getenv('EMAIL_SENDER', '')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', '')
EMAIL_SERVER = os.getenv('EMAIL_SERVER', '')
EMAIL_RECEIVER =  os.getenv('EMAIL_RECEIVER', '')

ALERT_SOUND = "notice.mp3"
FOUND_POSTS_FILE = "found_posts.txt"
BROWSER_TYPE = 'FIREFOX'
found_posts = set()

def setup_browser():
    if os.name == "nt":
        log_path = "NUL"
    else:
        log_path = "/dev/null"

    service = FirefoxService(GECKO_EXE_LOC, log_output=open(log_path, "w"))
    options = webdriver.FirefoxOptions()
    options.binary_location = BROWSER_EXE_LOC
    options.add_argument("--log-level=3")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.set_preference("browser.console.logLevel", "fatal")
    options.set_preference("webdriver.log.file", "NUL" if os.name == "nt" else "/dev/null")
    options.profile = BROWSER_PROFILE_DIR
    # Comment to view
    options.add_argument('--headless')
    options.add_argument("--window-size=0,0")
    # options.add_argument("--window-size=1920,1080")
    driver = webdriver.Firefox(service=service, options=options)
    logger.info(driver.capabilities.get("moz:profile"))
    return driver

def play_alert_sound():
    try:
        pygame.mixer.music.load(ALERT_SOUND)
        pygame.mixer.music.play()
        logger.info("Alert sound played")
    except Exception as e:
        logger.error(f"Error playing alert sound: {e}")

def check_for_keywords(text):
    text = text.lower()
    found_keywords = []
    for keyword in CRYPTO_KEYWORDS:
        if keyword.lower() == "eth":
            if re.search(r'\beth\b', text, re.IGNORECASE):
                found_keywords.append(keyword)
        elif keyword.lower() == "tron":
            if re.search(r'\btron\b', text, re.IGNORECASE):
                found_keywords.append(keyword)
        elif keyword.lower() == "ada":
            if re.search(r'\bada\b', text, re.IGNORECASE):
                found_keywords.append(keyword)
        else:
            if keyword.lower() in text:
                found_keywords.append(keyword)
    return found_keywords

def check_twitter_account(driver, account):
    logger.info(f"Checking Twitter account: {account}")
    url_link = f"https://twitter.com/{account}"
    try:
        driver.get(url_link)
        WebDriverWait(driver, 8).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='tweetText']")))
        time.sleep(2)
        scroll_down(driver, scrolls=1, scroll_height=500)
        tweets = driver.find_elements(By.CSS_SELECTOR, "[data-testid='tweetText']")
        if tweets:
            logger.info(f"Account: {account} has {len(tweets)} posts found.")
        else:
            logger.warning(f"No posts found on the {account} page!")
        for tweet in tweets[:10]:
            try:
                tweet_text = tweet.text
                tweet_text = re.sub(r'CZ\s+BNB', '', tweet_text, flags=re.IGNORECASE).strip()
                found_keywords = check_for_keywords(tweet_text)
                if found_keywords:
                    alert_event(account, found_keywords, tweet_text, url_link)
            except Exception as e:
                logger.error(f"Error processing tweet: {e}")
    except Exception as e:
        logger.error(f"Error checking Twitter account {account}: {e}")


def check_truth_social_account(driver, account):
    logger.info(f"Checking Truth Social account: {account}")
    url_link = f"https://truthsocial.com/@{account}"
    try:
        driver.get(url_link)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "timeline")))
        time.sleep(2)
        scroll_down(driver, scrolls=1, scroll_height=500)
        posts = driver.find_elements(By.CSS_SELECTOR, "div.status__content-wrapper")
        if posts:
            logger.info(f"Account: {account} has {len(posts)} posts found.")
        else:
            logger.warning(f"No posts found on the {account} page!")
        for index, post in enumerate(posts[:10]):
            retry_attempts = 3
            while retry_attempts > 0:
                try:
                    post = driver.find_elements(By.CSS_SELECTOR, "div.status__content-wrapper")[index]
                    post_text_elements = post.find_elements(By.CSS_SELECTOR, "p")
                    post_text_elements_clean = post_text_elements
                    if not post_text_elements:
                        logger.warning(f"No text found in post {index + 1}: {post.get_attribute('outerHTML')}")
                        break
                    if len(post_text_elements) > 3:
                        post_text_elements_clean = post_text_elements[:-3]
                    post_text = " ".join([p.text.strip() for p in post_text_elements_clean if p.text.strip()])
                    found_keywords = check_for_keywords(post_text)
                    if found_keywords:
                        alert_event(account,found_keywords,post_text, url_link)
                    break
                except (StaleElementReferenceException, NoSuchElementException):
                    logger.warning(f"StaleElementReferenceException: Retrying post {index + 1}")
                    retry_attempts -= 1
                    time.sleep(1)
                except Exception as e:
                    logger.error(f"Error processing post {index + 1}: {e}")
                    break
    except Exception as e:
        logger.error(f"Error checking Truth Social account {account}: {e}")

def alert_event(account, found_keywords, post_text, url_link):
    global found_posts
    trimmed_post = normalize_text(post_text)
    if trimmed_post in found_posts:
        logger.info("Duplicate post detected. Skipping alert.")
        return
    logger.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    logger.info(f"Found crypto keywords in post by {account}: {found_keywords}")
    logger.info(f"Post text: {post_text}")
    logger.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    play_alert_sound()
    if EMAIL_ENABLED:
        subject = f"Crypto Alert: {', '.join(found_keywords)} Found!"
        body = f"LINK: {url_link}\nNew post from {account}:\n\n{post_text}"
        send_email(subject, body)
    save_found_post(post_text)

def scroll_down(driver, scrolls=5, scroll_height=500, wait_time=1):
    for _ in range(scrolls):
        driver.execute_script("window.scrollBy(0, arguments[0]);", scroll_height)
        time.sleep(wait_time)

def send_email(subject, body):
    logger.info("send_email...")
    msg = MIMEMultipart()
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    with smtplib.SMTP_SSL(EMAIL_SERVER, 465) as server:
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
    logger.info(f"Email sent: {subject}")

def load_found_posts():
    logger.info("load_found_posts...")
    if not os.path.exists(FOUND_POSTS_FILE):
        return set()
    with open(FOUND_POSTS_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f)

def save_found_post(post_text):
    logger.info("save_found_post...")
    trimmed_post = normalize_text(post_text)
    with open(FOUND_POSTS_FILE, "a", encoding="utf-8") as f:
        f.write(trimmed_post + "\n")

def normalize_text(text):
    text = text.replace('\n', ' ').strip()
    return text[:-30] if len(text) > 30 else text

def main():
    global found_posts
    logger.info("Starting crypto monitoring...")
    found_posts = load_found_posts()
    driver = None
    service = None
    try:
        driver = setup_browser()
        service = driver.service
        for account in TRUTH_SOCIAL_ACCOUNTS:
            check_truth_social_account(driver, account)
            time.sleep(2)
        for account in TWITTER_ACCOUNTS:
            check_twitter_account(driver, account)
            time.sleep(2)
    except KeyboardInterrupt:
        logger.info("Monitoring stopped by user")
    except Exception as e:
        logger.error(f"Error in main monitoring loop: {e}")
    finally:
        if driver:
            try:
                driver.quit()
                logger.info("Browser session closed successfully.")
            except Exception as e:
                logger.error(f"Error while quitting driver: {e}")
        if service:
            try:
                service.stop()
                logger.info("Selenium service stopped successfully.")
            except Exception as e:
                logger.error(f"Error while stopping Selenium service: {e}")
    log_path = os.path.join(os.getcwd(), "geckodriver.log")
    if os.path.exists(log_path):
        try:
            os.remove(log_path)
            logger.info("Deleted geckodriver.log")
        except Exception as e:
            logger.error(f"Failed to delete geckodriver.log: {e}")
    logger.info("Completed crypto monitoring...")

if __name__ == "__main__":
    main() 