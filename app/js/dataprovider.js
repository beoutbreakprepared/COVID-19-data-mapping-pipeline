
/** @constructor */
let DataProvider = function(baseUrl) {
  /**
   * @const
   * @private
   */
  this.baseUrl_ = baseUrl;

  /** @private */
  this.countryFeaturesByDay_ = [];

  /** @private */
  this.provinceFeaturesByDay_ = [];

  /** @private */
  this.cityFeaturesByDay_ = [];

  /**
   * A map from country names to most recent data (case count, etc.).
   * @private
   */
  this.latestDataPerCountry_ = {};

  /** @private */
  this.dataSliceFileNames_ = [];
}

DataProvider.prototype.getLatestDataPerCountry = function() {
  return this.latestDataPerCountry_;
};

DataProvider.prototype.fetchInitialData = function(callback) {
  const self = this;
  Promise.all([
    this.fetchLatestCounts(),
    this.fetchCountryNames(),
    this.fetchDataIndex(),
    this.fetchLocationData()
  ]).then(function() { self.fetchJhuData(); }).then(callback);
};


DataProvider.prototype.fetchDailySlices = function(callback) {
  let dailyFetches = [];
  for (let i = 0; i < this.dataSliceFileNames_.length; i++) {
    dailyFetches.push(this.fetchDailySlice(
        this.dataSliceFileNames_[i], i == 0));
  }
  Promise.all(dailyFetches).then(callback);
};

/** Loads the location data (geo names from latitude and longitude). */
DataProvider.prototype.fetchLocationData = function() {
  return fetch(this.baseUrl_ + 'location_info.data')
    .then(function(response) { return response.text(); })
    .then(function(responseText) {
      let lines = responseText.split('\n');
      for (let i = 0; i < lines.length; i++) {
        let parts = lines[i].split(':');
        locationInfo[parts[0]] = parts[1];
      }
    });
};


DataProvider.prototype.fetchDataIndex = function() {
  let self = this;
  return fetch(this.baseUrl_ + '/d/index.txt')
    .then(function(response) { return response.text(); })
    .then(function(responseText) {
      let lines = responseText.split('\n');
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        if (!!line) {
          self.dataSliceFileNames_.push(line);
        }
      }
    });
};


DataProvider.prototype.fetchCountryNames = function() {
  return fetch('https://raw.githubusercontent.com/ghdsi/common/master/countries.data')
    .then(function(response) { return response.text(); })
    .then(function(responseText) {
      let countryLines = responseText.trim().split('\n');
      for (let i = 0; i < countryLines.length; i++) {
        let parts = countryLines[i].split(':');
        const code = parts[0];
        const name = parts[1];
        let bboxParts = parts[2].split('|');
        let bboxes = [];
        for (let j = 0; j < bboxParts.length; j++) {
            let bbox = bboxParts[j].split(',');
            bboxes.push(bbox);
        }
        let c = new Country(code, name, bboxes);
        countries[code] = c;
      }
    });
};


/** Loads the latest case counts from the scraper. */
DataProvider.prototype.fetchLatestCounts = function() {
  return fetch(this.baseUrl_ + 'latestCounts.json?nocache=' + timestamp)
    .then(function(response) { return response.json(); })
    .then(function(jsonData) {
      document.getElementById('total-cases').innerText = jsonData[0]['caseCount'];
      document.getElementById('last-updated-date').innerText = jsonData[0]['date'];
    });
};


/** Loads the appropriate country-specific data. */
DataProvider.prototype.loadCountryData = function(callback) {
  const code = document.getElementById('dash').getAttribute('c');
  fetch(this.baseUrl_ + 'c/' + code + '.json')
      .then(function(response) { return response.json(); })
      .then(callback);
};


/**
 * Fetches the next daily slice of data we need. If no argument is provided,
 * fetches the latest slice first.
 */
DataProvider.prototype.fetchDailySlice = function(sliceFileName, isNewest) {
  let self = this;
  let url = this.baseUrl_ + 'd/' + sliceFileName;
  // Don't cache the most recent daily slice. Cache all others.
  if (isNewest) {
    url += '?nocache=' + timestamp;
  }
  return fetch(url)
      .then(function(response) {
          return response.status == 200 ? response.json() : undefined;
      })
      .then(function(jsonData) {
        if (!jsonData) {
          return;
        }
        self.processDailySlice(jsonData, isNewest);
  });
};


DataProvider.prototype.processDailySlice = function(jsonData, isNewest) {
  let currentDate = jsonData['date'];
  let features = jsonData['features'];

  // Cases grouped by country and province.
  let provinceFeatures = {};
  let countryFeatures = {};

  // "Re-hydrate" the features into objects ingestable by the map.
  for (let i = 0; i < features.length; i++) {
    let feature = formatFeatureForMap(features[i]);

    // If we don't know where this is, discard.
    if (!locationInfo[feature['properties']['geoid']]) {
      continue;
    }
    // City, province, country.
    let location = locationInfo[feature['properties']['geoid']].split(',');
    if (!provinceFeatures[location[1]]) {
      provinceFeatures[location[1]] = {'total': 0, 'new': 0};
    }
    provinceFeatures[location[1]]['total'] += feature['properties']['total'];
    provinceFeatures[location[1]]['new'] += feature['properties']['new'];
    if (!countryFeatures[location[2]]) {
      countryFeatures[location[2]] = {'total': 0, 'new': 0};
    }
    countryFeatures[location[2]]['total'] += feature['properties']['total'];
    countryFeatures[location[2]]['new'] += feature['properties']['new'];
  }

  dates.unshift(currentDate);

  countryFeaturesByDay[currentDate] = countryFeatures;
  provinceFeaturesByDay[currentDate] = provinceFeatures;
  atomicFeaturesByDay[currentDate] = features;

  // Only use the latest data for the map until we're done downloading
  // everything.
  if (isNewest) {
    showDataAtDate(currentDate);
  }

  updateTimeControl();
};


DataProvider.prototype.fetchJhuData = function() {
  let self = this;
  return fetch(this.baseUrl_ + 'jhu.json?nocache=' + timestamp)
    .then(function(response) { return response.json(); })
    .then(function(jsonData) {
      let obj = jsonData['features'];
      // Sort according to decreasing confirmed cases.
      obj.sort(function(a, b) {
        return b['attributes']['cum_conf'] - a['attributes']['cum_conf'];
      });
      let countryList = document.getElementById('location-list');
      for (let i = 0; i < obj.length; ++i) {
        let location = obj[i];
        if (!location || !location['attributes'] || !location['centroid']) {
          // We can't do much with this location.
          continue;
        }
        const code = location['attributes']['code'];
        const country = countries[code];
        if (!country) {
          continue;
        }
        const name = country.getName();
        let lon = location['centroid']['x'] || 0;
        let lat = location['centroid']['y'] || 0;
        const geoid = '' + lat + '|' + lon;
        // The total count comes down as a formatted string.
        let cumConf = parseInt(
            location['attributes']['cum_conf'].replace(/,/g, ''),
            10) || 0;
        let legendGroup = 'default';
        self.latestDataPerCountry_[geoid] = [name, cumConf];
        // No city or province, just the country name.
        locationInfo[geoid] = ',,' + name;
        if (cumConf <= 10) {
          legendGroup = '10';
        } else if (cumConf <= 100) {
          legendGroup = '100';
        } else if (cumConf <= 500) {
          legendGroup = '500';
        } else if (cumConf <= 2000) {
          legendGroup = '2000';
        }

        let item = document.createElement('li');
        let button = document.createElement('button');
        button.setAttribute('country', code);
        button.onclick = flyToCountry;
        button.innerHTML = '<span class="label">' + name + '</span>' +
            '<span class="num legend-group-' + legendGroup + '">' +
            cumConf.toLocaleString() + '</span></span>';
        item.appendChild(button);
        countryList.appendChild(item);
      }
    });
}
