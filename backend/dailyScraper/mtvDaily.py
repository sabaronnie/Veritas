import os
import sys
import time
import json
import hashlib
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from pymongo import MongoClient
from dotenv import load_dotenv

# ---------------------------------------
# ENV
# ---------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(BASE_DIR + "/../secrets.env")

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
articles_col = db["articles"]

from specific_scrapers import scrape_mtv

# ---------------------------------------
# IMPORT HELPERS
# ---------------------------------------
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(parent_dir)

from cleaning import clean_text
from mtvDaily import scrape_mtv
from loadToDb import insert_one_article
# ---------------------------------------
# CONFIG
# ---------------------------------------
HEADERS = {"User-Agent": "Mozilla/5.0"}
MTV_API = "https://www.mtv.com.lb/en/api/articles?start={}&end={}&type="

PAGE_SIZE = 50       # MTV returns blocks of N items
MAX_AGE_HOURS = 24   # stop scraping once older articles detected



articles = scrape_mtv(MAX_AGE_HOURS, MTV_API, PAGE_SIZE)
#print(articles)
for article in articles:
    insert_one_article(article)