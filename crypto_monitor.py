import logging
import os
import re
import time
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
DEBUG_ENABLED = False

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='crypto_monitor_log.txt'
)

logger = logging.getLogger()
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
logger.addHandler(console_handler)

CRYPTO_KEYWORDS = [
    "cryptocurrency", "bitcoin", "btc", "ltc", "ethereum", "eth", "litecoin","dogecoin", "shiba inu", "floki", "pepe", "dogwifhat",
    "altcoin", "bnb", "xrp", "ripple", "sol", "trx", "tron", "xlm", "stellar", 'sell', 'sold', 'buy', 'bought',"ada","vechain", "algorand",
    "trumpcoin","freedom coin"
]

TWITTER_ACCOUNTS = [
    ["elonmusk",True],
    ["WhiteHouse",True],
    ["POTUS",True],
    ["realDonaldTrump",True],
    ["Pentosh1",True]
]

TRUTH_SOCIAL_ACCOUNTS = [
    ["realDonaldTrump",True],
    ["TuckerCarlson",True],
    ["DonaldJTrumpJr",True]
]

GECKO_EXE_LOC = os.getenv('GECKO_EXE_LOC', '')
BROWSER_EXE_LOC = os.getenv('BROWSER_EXE_LOC', '')
BROWSER_PROFILE_DIR = os.getenv('BROWSER_PROFILE_DIR', '')
EMAIL_SENDER = os.getenv('EMAIL_SENDER', '')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', '')
EMAIL_SERVER = os.getenv('EMAIL_SERVER', '')
EMAIL_RECEIVER =  os.getenv('EMAIL_RECEIVER', '')

FOUND_POSTS_FILE = "found_posts.txt"
BROWSER_TYPE = 'FIREFOX'
LOADED_POSTS = set()

def setup_browser():
    service = FirefoxService(GECKO_EXE_LOC)
    options = webdriver.FirefoxOptions()
    options.binary_location = BROWSER_EXE_LOC
    options.add_argument("--log-level=3")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.set_preference("browser.console.logLevel", "fatal")
    options.set_preference("webdriver.log.file", "NUL" if os.name == "nt" else "/dev/null")
    options.set_preference("profile", BROWSER_PROFILE_DIR)
    # Comment to view
    # options.add_argument('--headless')
    # options.add_argument("--window-size=0,0")
    # options.add_argument("--window-size=1920,1080")
    driver = webdriver.Firefox(service=service, options=options)
    logger.info(driver.capabilities.get("moz:profile"))
    return driver

def check_for_keywords(text):
    global LOADED_POSTS, CRYPTO_KEYWORDS, DEBUG_ENABLED
    found_keywords = []
    if text in LOADED_POSTS:
        if DEBUG_ENABLED:
            logger.info(f"~~~~~ FOUND IN LOADED_POSTS ~~~~~")
        return found_keywords
    for keyword in CRYPTO_KEYWORDS:
        if re.search(rf'(?<!\w){re.escape(keyword)}(?!\w)', text, re.IGNORECASE):
            found_keywords.append(keyword)
    return found_keywords

def check_twitter_account(driver, item):
    global DEBUG_ENABLED
    logger.info(f"Checking Twitter account: {item[0]}")
    url_link = f"https://twitter.com/{item[0]}"
    try:
        driver.get(url_link)
        WebDriverWait(driver, 8).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='tweetText']")))
        time.sleep(2)
        scroll_down(driver, scrolls=1, scroll_height=500)
        tweets = driver.find_elements(By.CSS_SELECTOR, "[data-testid='tweetText']")
        if tweets:
            logger.info(f"Account: {item[0]} has {len(tweets)} posts found.")
        else:
            logger.warning(f"No posts found on the {item[0]} page!")
        for tweet in tweets[:10]:
            try:
                post_text = tweet.text
                post_text = normalize_text(post_text)
                found_keywords = check_for_keywords(post_text)
                if found_keywords:
                    alert_event(item, found_keywords, post_text, url_link)
                elif DEBUG_ENABLED:
                    logger.info(f"NO MATCH FOUND IN ---->  {post_text}")
            except Exception as e:
                logger.error(f"Error processing tweet: {e}")
    except Exception as e:
        logger.error(f"Error checking Twitter account {item[0]}: {e}")


def check_truth_social_account(driver, item):
    global DEBUG_ENABLED
    logger.info(f"Checking Truth Social account: {item[0]}")
    url_link = f"https://truthsocial.com/@{item[0]}"
    try:
        driver.get(url_link)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "timeline")))
        time.sleep(2)
        scroll_down(driver, scrolls=1, scroll_height=500)
        posts = driver.find_elements(By.CSS_SELECTOR, "div.status__content-wrapper")
        if posts:
            logger.info(f"Account: {item[0]} has {len(posts)} posts found.")
        else:
            logger.warning(f"No posts found on the {item[0]} page!")
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
                    post_text = normalize_text(post_text)
                    found_keywords = check_for_keywords(post_text)
                    if found_keywords:
                        alert_event(item, found_keywords, post_text, url_link)
                    elif DEBUG_ENABLED:
                        logger.info(f"NO MATCH FOUND IN ---->  {post_text}")
                    break
                except (StaleElementReferenceException, NoSuchElementException):
                    logger.warning(f"StaleElementReferenceException: Retrying post {index + 1}")
                    retry_attempts -= 1
                    time.sleep(1)
                except Exception as e:
                    logger.error(f"Error processing post {index + 1}: {e}")
                    break
    except Exception as e:
        logger.error(f"Error checking Truth Social account {item[0]}: {e}")

def alert_event(item, found_keywords, post_text, url_link):
    logger.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    logger.info(f"Found crypto keywords in post by {item[0]}: {found_keywords}")
    logger.info(f"Post text: {post_text}")
    logger.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    if EMAIL_ENABLED and item[1]:
        subject = f"Crypto Account: {item[0]} found ({', '.join(found_keywords)})"
        body = f"LINK: {url_link}\nNew post from {item[0]}:\n\n{post_text}"
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
    global FOUND_POSTS_FILE, LOADED_POSTS
    logger.info("load_found_posts...")
    LOADED_POSTS = set()
    if os.path.exists(FOUND_POSTS_FILE):
        with open(FOUND_POSTS_FILE, "r", encoding="utf-8") as f:
            LOADED_POSTS = set(line.strip() for line in f)
        f.close()
    return LOADED_POSTS

def save_found_post(post_text):
    global FOUND_POSTS_FILE
    logger.info("save_found_post...")
    with open(FOUND_POSTS_FILE, "a", encoding="utf-8") as f:
        f.write(post_text + "\n")
    f.close()

def normalize_text(text):
    text = text.replace('\n', ' ').strip()
    return text

def main():
    global LOADED_POSTS, TRUTH_SOCIAL_ACCOUNTS, TWITTER_ACCOUNTS
    logger.info("Starting crypto monitoring...")
    LOADED_POSTS = load_found_posts()
    driver = None
    service = None
    try:
        driver = setup_browser()
        service = driver.service
        for item in TRUTH_SOCIAL_ACCOUNTS:
            check_truth_social_account(driver, item)
            time.sleep(2)
        for item in TWITTER_ACCOUNTS:
            check_twitter_account(driver, item)
            time.sleep(2)
    except KeyboardInterrupt:
        logger.info("Monitoring stopped by user")
        if driver:
            driver.quit()
            logger.info("Browser session closed on user interrupt.")
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