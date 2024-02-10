from keep_alive import keep_alive
import pytz
import requests
from apscheduler.schedulers.blocking import BlockingScheduler
from bs4 import BeautifulSoup
from pymongo import MongoClient
import os

connection_string = os.environ.get("connection_string")
client = MongoClient(connection_string)

db = client['chelsea_news']
collection = db['chelsea_news_co']

HEADER = {
    "User-Agent":
        "Mozilla/5.0 (X11; CrOS x86_64 8172.45.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.64 Safari/537.36"
}

BOT_TOKEN = os.environ.get("bot_token")
CHAT_ID = os.environ.get("chat_id")
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/"

keep_alive()

nigerian_tz = pytz.timezone("Africa/Lagos")


def scrape_chelsea_news():
    url = "https://www.chelsea-news.co/category/news/"
    response = requests.get(url, headers=HEADER, timeout=(10, 27))
    response.raise_for_status()

    soup = BeautifulSoup(response.content, "html.parser")

    news_cards = soup.find_all("div", class_="home-content-article")
    news_list = []

    for news_card in news_cards[:5]:
        crd_title = news_card.find("div", class_="article-title").h1.text
        crd_img = news_card.find("div", class_="article-img-box").div.get('lazy-background', '')
        crd_author = news_card.find("div", class_="article-byline").a.text
        crd_link = news_card.a.get('href', '')

        if not crd_title or not crd_img or not crd_link or not crd_author:
            continue

        resp = requests.get(crd_link,
                            headers=HEADER,
                            timeout=(10, 27))
        resp.raise_for_status()  # Check for HTTP status code errors
        soup = BeautifulSoup(resp.content, "html.parser")

        article_container = soup.find("div", {"id": "article-body"})
        crd_contents = article_container.find_all("p")
        crd_desc = "".join([content.get_text() + '\n\n' for content in crd_contents[:2]])
        news_list.append({
            "title": crd_title,
            "image": crd_img,
            "contents": crd_desc,
            "author": crd_author
        })

    return news_list


# Function to send news to Telegram
def send_news_to_telegram(article_items):
    for item in article_items:
        title_ = item.get("title", "")
        story_ = item.get("contents", "")
        img_ = item.get("image", "")
        author_ = item.get("author", "")

        # Check if any of the required data is missing
        if not title_ or not story_:
            continue

        message = f"🚨 *{title_}*\n\n{story_}\n" \
                  f"🔗 *{author_} - Chelsea News*\n\n" \
                  f"📲 @JustCFC"

        saved_titles = collection.find_one({"text": title_})
        if not saved_titles:
            response = requests.post(BASE_URL + "sendPhoto",
                                     json={
                                         "chat_id": CHAT_ID,
                                         "disable_web_page_preview": False,
                                         "parse_mode": "Markdown",
                                         "caption": message,
                                         "photo": img_
                                     })

            if response.status_code == 200:
                print("Message sent successfully.")

                # Insert the text into the collection
                collection.insert_one({"text": title_})

            else:
                print(
                    f"Message sending failed. Status code: {response.status_code}"
                )


def main():
    news_items = scrape_chelsea_news()
    send_news_to_telegram(news_items)


scheduler = BlockingScheduler(timezone=nigerian_tz)
scheduler.add_job(main, "interval", minutes=30)
scheduler.start()
# main()
