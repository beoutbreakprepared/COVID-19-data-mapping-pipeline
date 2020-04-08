'''
Pipeline to fetch covid-19 data from Open Line List and reformat for map on : 
    healthmap.org/covid-19

Author : Thomas Brewer
email  : thomas.brewer@childrens.harvard.edu
'''



testing = True

import configparser
import pandas as pd
from shutil import copyfile
from functions import *
import requests
import sys
import re

configfile = './.CONF'
config = configparser.ConfigParser()
config.read(configfile)
logfile = config['FILES'].get('LOG')


jhu_file = config['FILES']['JHU']
jhu_url = 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_US.csv'

COLNAMES = ['ID', 'latitude', 'longitude', 'city', 'province', 'country',
            'age', 'sex', 'symptoms', 'source', 'date_confirmation', 'geo_resolution'] # desired columns from sheets
# A1 notation ranges from sheets
def main():
    try :
        # Line list data
        latest_data_path = config['FILES'].get('SHEETDATA', './latestdata.csv')
        req = requests.get('https://raw.githubusercontent.com/beoutbreakprepared/nCoV2019/master/latest_data/latestdata.csv')
        if req.status_code == 200:
            with open(latest_data_path, 'w') as f:
                f.write(req.text)
        else :
            sys.exit(1)

        df = pd.read_csv(latest_data_path, dtype=str)
        filter_ = ~df.country.isin(['United States', 'Virgin Islands, U.S.'])
        df = df[filter_]
        full_data = clean_data(df, COLNAMES)
    

        # JHU data
        req = requests.get(jhu_url)
        if req.status_code == 200:
            with open(jhu_file, 'w') as F:
                F.write(req.text)
        
        us_data = pd.read_csv(jhu_file, dtype=str)
      
        # rename date columns to match sheet format (%d.%m.%d)
        rx = '\d{1,2}/\d{1,2}/\d'
        date_columns = []
        for c in us_data.columns:
            if re.match(rx, c):
                month, day, year = c.split('/')
                month = str(month).zfill(2)
                day   = str(day).zfill(2)
                year = '20' + str(year)
                date = '{}.{}.{}'.format(day, month, year)
                date_columns.append(date)
                us_data.rename({c : date}, axis=1, inplace=True)
        date_columns = sorted(date_columns, key=lambda x: pd.to_datetime(x, format='%d.%m.%Y'))
        
        # reformat JHU to have same structure as sheet
        # This may seem silly because we unpack and then reduce to Unique again, 
        # we do it because the "full_data" file is sent to FM-Global

        # only defining columns where values will change for now.
        # Loop is done in this order so that IDs persist. 
        print(len(us_data[us_data.Lat.astype(float) == 0]))
        us_reformed = pd.DataFrame(columns=['latitude', 'longitude', 'city', 'province', 'date_confirmation'])
        for i, date in enumerate(date_columns):
            print(date)
            for j, row in us_data.iterrows():
                if float(row['Lat']) == 0 or float(row['Long_']) == 0:
                    continue

                if pd.isnull(row['Lat']) or pd.isnull(row['Long_']): 
                    continue

                if i == 0:
                    N = int(row[date])
                else:
                    N = int(row[date]) - int(row[date_columns[i-1]])
                entry = {
                        'latitude': row['Lat'],
                        'longitude': row['Long_'],
                        'city': row['Admin2'],
                        'province': row['Province_State'],
                        'date_confirmation': date
                }
                us_reformed = us_reformed.append([entry]*N, ignore_index=True)

        print(len(us_reformed[us_reformed['latitude'].astype(float) == 0]))
        us_reformed.insert(0, 'ID', range(1, len(us_reformed) + 1))
        us_reformed['ID'] = us_reformed['ID'].apply(lambda x : 'JHU' + str(x))
        us_reformed.insert(5, 'country', 'United States')
        us_reformed.insert(6, 'age', '')
        us_reformed.insert(7, 'sex', '')
        us_reformed.insert(8, 'symptoms', '')
        us_reformed.insert(9, 'source', 'JHU')
        us_reformed.insert(11, 'geo_resolution', 'admin2')

        full_data = full_data.append(us_reformed, ignore_index = True)
        unique_data = reduceToUnique(full_data) 
        full_data = {'data': full_data.to_dict(orient='records')}
        fullpath  = config['FILES'].get('FULL')
        savedata(full_data, fullpath)
        
        # animation data
        geo_anipath    = config['FILES'].get('GEO_ANIME')
        animation_formating_geo(fullpath, geo_anipath)
        

        if not testing:
            # Copy files to HTML directoryi
            htmlpath1 = config['HTML'].get('TOTALS')
            htmlpath2 = config['HTML'].get('ANIMATION')
            copyfile(uniquepath, htmlpath1) 
            copyfile(anipath, htmlpath2)

            htmlpath1 = config['HTML'].get('GEO_TOTALS')
            htmlpath2 = config['HTML'].get('GEO_ANIME')
            copyfile(geo_uniquepath, htmlpath1)
            copyfile(geo_anipath, htmlpath2)

    except Exception as Err:
        message = f'Update Error, {Err}'
        log_message(message, config)
        raise Err


if __name__ == '__main__':
    main()


