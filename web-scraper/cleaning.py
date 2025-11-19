# -----------------------------
# CLEANING HELPERS
# -----------------------------
import re 
from bs4 import BeautifulSoup

def clean_text(text):
    if not text:
        return ""

    # Parse HTML and extract visible text
    soup = BeautifulSoup(text, "html.parser")
    text = soup.get_text(separator=" ")

    text = re.sub(r"[\u200B-\u200F\u202A-\u202E]", "", text)
    text = text.replace("\xa0", " ")
    text = re.sub(r"[\x00-\x1F\x7F]", " ", text)

    replacements = {
        "’": "'", "‘": "'", "‚": "'",
        "“": '"', "”": '"', "„": '"'
    }
    for k, v in replacements.items():
        text = text.replace(k, v)

    text = re.sub(r" +", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)

    return text.strip()


def clean_url(url):
    if not url:
        return None
    url = url.strip()
    url = re.sub(r"[\u200B-\u200F\u202A-\u202E]", "", url)
    url = url.replace("\xa0", "")
    return url