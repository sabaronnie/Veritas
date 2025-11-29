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

    # Remove emojis and pictographs
    text = re.sub(r"[\U00010000-\U0010FFFF]", "", text)

    # Remove invisible Unicode control characters
    text = re.sub(r"[\u200B-\u200F\u202A-\u202E]", "", text)

    # Normalize dashes to simple hyphen
    text = text.replace("–", "-")   # en dash U+2013
    text = text.replace("—", "-")   # em dash U+2014
    text = text.replace("−", "-")   # minus sign U+2212

    #Remove arabic
    pattern = r'[\u0600-\u06FF\u0750-\u077F]+'
    text = re.sub(pattern, '', text)
    
    # Fix weird spaces
    text = text.replace("\xa0", " ")
    text = re.sub(r"[\x00-\x1F\x7F]", " ", text)

    # Smart quote normalization
    replacements = {
        "’": "'", "‘": "'", "‚": "'",
        "“": '"', "”": '"', "„": '"'
    }
    for k, v in replacements.items():
        text = text.replace(k, v)

    # Collapse spaces & blank lines
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