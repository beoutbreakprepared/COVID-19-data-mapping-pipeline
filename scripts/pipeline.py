##########
# Author/Editor Thomas Brewer, thomas.brewer@childrens.harvard.edu
# Last edit : 2020-03-18
#########

testing = True
import configparser
import pandas as pd
from shutil import copyfile
from functions import *

if testing:
    configfile = '.GITCONF'
else:
    configfile = '.CONF'
config = configparser.ConfigParser()
config.read(configfile)
logfile = config['FILES'].get('LOG')


COLNAMES = ['ID', 'latitude', 'longitude', 'city', 'province', 'country',
            'age', 'sex', 'symptoms', 'source', 'date_confirmation', 'geo_resolution'] # desired columns from sheets
# A1 notation ranges from sheets
RANGE1='outside_Hubei!A:V'
RANGE2='Hubei!A:V'

def main():
    try :
        # Outside Hubei
        outside_hubei_full   = clean_data(load_sheet(RANGE1, config), COLNAMES)
        outside_hubei_unique = reduceToUnique(outside_hubei_full)

        # Hubei
        hubei_full   = clean_data(load_sheet(RANGE2, config), COLNAMES)
        hubei_unique = reduceToUnique(hubei_full)

        # Combine Inside/Outside data
        full_data   = {
                'outside_Hubei': outside_hubei_full.to_dict(orient='records'), 
                'Hubei': hubei_full.to_dict(orient='records')
                }
        unique_data = {'outside_Hubei': outside_hubei_unique, 
                'Hubei': hubei_unique
                }
        

        # save all results
        fullpath   = config['FILES'].get('FULL')
        backuppath = config['FILES'].get('JSONB')
        savedata(full_data, fullpath)
    
        uniquepath = config['FILES'].get('TOTAL')
        backuppath = config['FILES'].get('TOTALB')
        savedata(unique_data, uniquepath)


        # Animation
        anipath = config['FILES'].get('ANIMATION', './')
        animation_formating(fullpath, anipath)
        
        if not testing:
            # Copy files to HTML directoryi
            htmlpath1 = config['HTML'].get('TOTAL')
            htmlpath2 = config['HTML'].get('ANIMATION')
            copyfile(uniquepath, htmlpath1) 
            copyfile(anipath, htmlpath2)

    except Exception as Err:
        message = f'Update Error, {Err}'
        log_message(message, config)
        raise Err


if __name__ == '__main__':
    main()


