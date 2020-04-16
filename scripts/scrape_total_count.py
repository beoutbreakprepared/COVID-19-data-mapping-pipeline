import json
import os
import urllib.request
import sys
from bs4 import BeautifulSoup
from datetime import datetime


def scrape_total_count(out_path):

    url = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vR30F8lYP3jG7YOq8es0PBpJIE5yvRVZffOyaqC0GgMBN6yt0Q-NI8pxS7hd1F9dYXnowSC6zpZmW9D/pubhtml/sheet?headers=false&gid=0&range=A1:I183'
    fp = urllib.request.urlopen(url)
    mybytes = fp.read()

    html = mybytes.decode("utf8")
    fp.close()

    soup = BeautifulSoup(html, 'html.parser')
    try:
      count = soup.select_one('tbody tr:nth-child(5) td:nth-child(2)').text
    except NotImplementedError:
      print("WARNING I wasn't able to scrape the number I wanted, using a dummy value")
      count = 2000000
    date  = datetime.now().strftime('%Y-%m-%d') 
    
    results = {'caseCount': count, 'date': date}


    with open(out_path, 'w') as F: 
        json.dump([results], F)

if __name__ == '__main__':
    self_dir = os.path.dirname(os.path.realpath(__file__))  
    out_path = os.path.join(self_dir, "latestCounts.json")
    print("Saving file as " + out_path + "...")
    scrape_total_count(out_path)
