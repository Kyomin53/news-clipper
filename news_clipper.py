import os
import time
from datetime import datetime
import feedparser
from bs4 import BeautifulSoup
import requests
from google import genai
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

RSS_URL = "https://platum.kr/feed"

def get_todays_articles():
    print("Fetching RSS feed...")
    feed = feedparser.parse(RSS_URL)
    todays_articles = []
    
    for entry in feed.entries:
        todays_articles.append({
            "title": entry.title,
            "link": entry.link,
            "content": entry.description
        })
        if len(todays_articles) >= 3:
            break
            
    return todays_articles

def summarize_article(content, client):
    soup = BeautifulSoup(content, "html.parser")
    clean_text = soup.get_text(separator=" ", strip=True)
    prompt = f"Please summarize the following Korean startup news article. Identify the company, what they did, and the significance. Format as 3 concise bullet points (-). Output the summary ENTIRELY IN KOREAN. CRITICAL: DO NOT use ANY markdown characters like asterisks (*) or underscores (_), use strictly plain text!\n\n[Article Content]\n{clean_text[:2500]}"
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        print(f"Gemini API error: {e}")
        return "Failed to summarize."

def send_telegram_message(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print("Telegram sent successfully")
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")

def escape_html(text):
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def main():
    if not GEMINI_API_KEY:
        return
    client = genai.Client(api_key=GEMINI_API_KEY)
    articles = get_todays_articles()
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    full_message = f"<b>{today_str} Platum Startup News Summary (Test Run)</b>\n\n"
    
    for i, article in enumerate(articles, 1):
        summary = summarize_article(article["content"], client)
        
        safe_title = escape_html(article['title'])
        safe_summary = escape_html(summary)
        
        full_message += f"<b><a href='{article['link']}'>{safe_title}</a></b>\n{safe_summary}\n\n"
        time.sleep(2)
        if len(full_message) > 3500:
            send_telegram_message(full_message)
            full_message = ""

    if full_message.strip():
        send_telegram_message(full_message)

if __name__ == "__main__":
    main()
