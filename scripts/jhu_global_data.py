#!/usr/bin/env python3

import requests
import pandas as pd
from datetime import datetime, timedelta 
import sys
from io import StringIO
import json

def legend_group(count):
    if count <= 10:
        return '10'
    elif 10 < count <= 100:
        return '100'
    elif 100 < count <= 500:
        return  '500'
    elif 500 < count <= 2000:
        return '2000'
    else:
        return 'default'

def main(outfile):
    url_base = 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_daily_reports/{}.csv'
    date = (datetime.now() - timedelta(days=1)).strftime('%m-%d-%Y')
    url = url_base.format(date)


    req = requests.get(url)
    if req.status_code != 200:
        print('Couldn\'t get Global JHU data, aborting')
        sys.exit(1)

    df = pd.read_csv(StringIO(req.text), usecols=['Lat', 'Long_',
        'Country_Region', 'Confirmed'])
    df = df[~(df.Lat.isna() | df.Long_.isna())] 

    central_us_lat  = '39.8283'
    central_us_long = '98.5795'

    counts = df[['Country_Region', 'Confirmed']].groupby('Country_Region', as_index=False).sum()
   
    df = df.drop('Confirmed', axis=1)
    df = df.drop_duplicates(subset='Country_Region')

    counts = counts.merge(df, on='Country_Region', how='left')
    counts['legendGroup'] = counts.Confirmed.map(legend_group)
    counts['Confirmed'] = counts.Confirmed.map('{:,}'.format)
    counts[counts.Country_Region == 'US'][['Lat', 'Long_']] = [central_us_lat, central_us_long]
    counts[counts.Country_Region == 'US']['Country_Region'] = 'United States of America'
    counts['Lat'] = counts.Lat.round(4)
    counts['Long_'] = counts.Long_.round(4)
    counts.Country_Region = counts.Country_Region.apply(lambda x: 'United States of America' if x == 'US' else x)
    features = []
    for i, row in counts.iterrows():
        print(row.dtype)
        entry = {
            'attributes': {
                'cum_conf': row['Confirmed'],
                'ADM0_NAME': row['Country_Region'],
                'legendGroup': row['legendGroup']
            },
            'centroid': {
                  "x" : row['Long_'], 
                  "y" : row['Lat']
                }
              }
        features.append(entry)

    features = sorted(features, 
            key=lambda x: int(x['attributes']['cum_conf'].replace(',','')), 
            reverse=True)
    data = {'features': features}

    with open(outfile, 'w') as f:
        json.dump(data, f) 


if __name__ == '__main__':
    main(sys.argv[1])

