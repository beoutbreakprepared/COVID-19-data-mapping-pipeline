'''
Get WHO data for Global counts side bar on map. 

Query copied after using interface at : 
    https://services.arcgis.com/5T5nSi527N4F7luB/ArcGIS/rest/services/COVID_19_CasesByCountry(pl)_VIEW/FeatureServer/0/query
'''

import requests
import json
from datetime import datetime
import os

def get_WHO(out_path):
    query = 'https://services.arcgis.com/5T5nSi527N4F7luB/ArcGIS/rest/services/COVID_19_CasesByCountry(pl)_VIEW/FeatureServer/0/query?where=1%3D1&objectIds=&time=&geometry=&geometryType=esriGeometryEnvelope&inSR=&spatialRel=esriSpatialRelIntersects&resultType=none&distance=0.0&units=esriSRUnit_Meter&returnGeodetic=true&outFields=cum_conf%2C+ADM0_NAME&returnGeometry=false&returnCentroid=true&featureEncoding=esriDefault&multipatchOption=xyFootprint&maxAllowableOffset=&geometryPrecision=&outSR=&datumTransformation=&applyVCSProjection=false&returnIdsOnly=false&returnUniqueIdsOnly=false&returnCountOnly=false&returnExtentOnly=false&returnQueryGeometry=false&returnDistinctValues=false&cacheHint=false&orderByFields=&groupByFieldsForStatistics=&outStatistics=&having=&resultOffset=&resultRecordCount=&returnZ=false&returnM=false&returnExceededLimitFeatures=true&quantizationParameters=&sqlFormat=none&f=pjson&token='
    
    req = requests.get(query)
    
    if req.status_code == 200:
        data = json.loads(req.text)
        features = {
                'features': sorted(data['features'], 
                    key=lambda x: int(x['attributes']['cum_conf']), 
                    reverse=True)
                }
    
        drop = None
        new    = 'legendGroup'
        values = [10, 100, 500, 2000] 
        for ind,f in enumerate(features['features']):
            attributes = f['attributes']
            if attributes['ADM0_NAME'] == 'International conveyance (Diamond Princess)':
                drop = ind
    
            count = int(attributes['cum_conf'])
            if count <= 10:
                attributes[new] = '10'
            elif 10 < count <= 100:
                attributes[new] = '100'
            elif 100 < count <= 500:
                attributes[new] = '500'
            elif 500 < count <= 2000:
                attributes[new] = '2000'
            else:
                attributes[new] = 'default'
            attributes['cum_conf'] = '{:,}'.format(count)
    
        if drop is not None:
            del(features['features'][drop])
    
        with open(out_path, 'w') as F:
            json.dump(features, F)
    
    
    

if __name__ == '__main__':
    self_dir = os.path.dirname(os.path.realpath(__file__))
    out_path = os.path.join(self_dir, "who.json")
    print("Saving file as " + out_path + "...")
    get_WHO(out_path)
