from newspaper import Article
import requests
url = "https://www.the961.com/"
html = requests.get(url).text
print(len(html))
print(html[:1000])