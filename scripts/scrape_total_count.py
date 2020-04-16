import json
import urllib.request
from bs4 import BeautifulSoup
from datetime import datetime


def scrape_total_count():

    url = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vR30F8lYP3jG7YOq8es0PBpJIE5yvRVZffOyaqC0GgMBN6yt0Q-NI8pxS7hd1F9dYXnowSC6zpZmW9D/pubhtml/sheet?headers=false&gid=0&range=A1:I183'
    fp = urllib.request.urlopen(url)
    mybytes = fp.read()

    html = mybytes.decode("utf8")
    fp.close()

    soup = BeautifulSoup(html, 'html.parser')
    count = soup.select_one('tbody tr:nth-child(5) td:nth-child(2)').text
    date  = datetime.now().strftime('%Y-%m-%d') 
    
    results = {'caseCount': count, 'date': date}


    with open('/path/to/index/latestCounts.json', 'w') as F: 
        json.dump([results], F)


if __name__ == '__main__':
    scrape_total_count()
