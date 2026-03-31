import os
import time
from datetime import datetime
import feedparser
from bs4 import BeautifulSoup
import requests
from google import genai
from dotenv import load_dotenv

# 환경변수 로드 (.env 파일이 있으면 읽어옴. GitHub Actions에서는 Secrets에서 주입)
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

RSS_URL = "https://platum.kr/feed"

def get_todays_articles():
    """RSS 피드를 파싱하여 오늘(또는 최근 24시간) 발행된 기사만 필터링합니다."""
    print("Fetching RSS feed...")
    feed = feedparser.parse(RSS_URL)
    
    todays_articles = []
    today_date = datetime.now().date()
    
    for entry in feed.entries:
        # RSS Published Date Format Parsing
        try:
            pub_date = datetime(*entry.published_parsed[:6]).date()
        except Exception as e:
            print(f"Date parsing error: {e}")
            continue
            
        # 오늘 날짜에 해당하는 기사만 수집 (GitHub Actions이 하루 한 번 도는 기준)
        if pub_date == today_date:
            todays_articles.append({
                "title": entry.title,
                "link": entry.link,
                "content": entry.description # 요약 또는 본문 일부 (RSS 형태소)
            })
            
    return todays_articles

def summarize_article(content, client):
    """Gemini API를 사용하여 기사를 3줄 요약합니다."""
    # HTML 태그 제거
    soup = BeautifulSoup(content, "html.parser")
    clean_text = soup.get_text(separator=" ", strip=True)
    
    prompt = f"""
다음은 스타트업 관련 뉴스 기사의 내용입니다.
이 기사의 핵심 내용(어떤 회사가, 무엇을 했고, 규모/의의가 무엇인지)을 파악하여 **불릿 포인트(-) 3줄**로 간결하게 요약해주세요.

[기사 내용]
{clean_text[:3000]}
"""
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        print(f"Gemini API error: {e}")
        return "요약에 실패했습니다."

def send_telegram_message(text):
    """Telegram API를 사용하여 메시지를 전송합니다."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram configuration missing. Skipping message.")
        return
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print("Telegram message sent successfully.")
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")

def main():
    if not GEMINI_API_KEY:
        print("GEMINI_API_KEY is not set.")
        return
        
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    articles = get_todays_articles()
    print(f"Found {len(articles)} articles for today.")
    
    if not articles:
        send_telegram_message("📢 오늘 플래텀에 새롭게 올라온 기사가 없습니다.")
        return

    # 메시지 조합
    today_str = datetime.now().strftime("%Y년 %m월 %d일")
    full_message = f"🚀 **{today_str} 플래텀 스타트업 뉴스 요약**

"
    
    for i, article in enumerate(articles, 1):
        print(f"Summarizing article {i}/{len(articles)}: {article['title']}")
        summary = summarize_article(article['content'], client)
        
        full_message += f"📰 **[{article['title']}]({article['link']})**
"
        full_message += f"{summary}

"
        
        time.sleep(2)
        
        if len(full_message) > 3500:
            send_telegram_message(full_message)
            full_message = ""

    print("All summaries completed. Sending to Telegram...")
    if full_message.strip():
        send_telegram_message(full_message)

if __name__ == "__main__":
    main()

