// Constants
const ANIMATION_FRAME_DURATION_MS = 300;
const COLOR_MAP = [
  ['#67009e', '< 10', 10],
  ['#921694', '11–100', 100],
  ['#d34d60', '101–500', 500],
  ['#fb9533', '501–2000', 2000],
  ['#edf91c', '> 2000'],
  ['cornflowerblue', 'New'],
];
const MAPBOX_TOKEN = 'pk.eyJ1IjoiaGVhbHRobWFwIiwiYSI6ImNrOGl1NGNldTAyYXYzZnBqcnBmN3RjanAifQ.H377pe4LPPcymeZkUBiBtg';

// Runtime constants
const timestamp = (new Date()).getTime();

// Globals
let location_info = {};
let dates = [];
let map;

// An object mapping dates to JSON objects with the corresponding data.
// for that day, grouped by country, province, or ungrouped (smallest
// granularity level).
let countryFeaturesByDay = {};
let provinceFeaturesByDay = {};
let atomicFeaturesByDay = {};

let timeControl = document.getElementById('slider');

function showDataAtDate(isodate) {

  const zoom = map.getZoom();
  let featuresToShow;
  if (zoom <= 1) {
    let countryFeaturesAsArray = [];
    for (let country in countryFeaturesByDay[isodate]) {
      countryFeaturesAsArray.push(formatFeatureForMap(countryFeaturesByDay[isodate][country]));
    }
    featuresToShow = countryFeaturesAsArray;
  } else {
    featuresToShow = atomicFeaturesByDay[isodate];
  }
  map.getSource('counts').setData(formatFeatureSetForMap(featuresToShow));
}

function setTimeControlLabel(date) {
  document.getElementById('date').innerText = dates[date];
}

function buildTimeControl() {
  document.getElementById('range-slider').style.display = 'flex';
  timeControl.setAttribute('max', dates.length - 1)
  timeControl.setAttribute('value', dates.length - 1);
  setTimeControlLabel(dates.length - 1);
}

function animateMap() {
  let i = 0;
  let stepMap = setInterval(function() {
    timeControl.value = i;
    showDataAtDate(dates[i]);
    setTimeControlLabel(i);
    i++;
    if (i === dates.length) {
      clearInterval(stepMap);
    }
  }, ANIMATION_FRAME_DURATION_MS);
}

/** Fills with leading zeros to the desired width. */
function zfill(n, width) {
  n = n + '';
  return n.length >= width ? n : new Array(width - n.length + 1).join('0') + n;
}

/**
 * Returns a date string corresponding to the day before the passed in
 * date.
 */
function oneDayBefore(dateString) {

  let parts = dateString.split('-');
   // Month is 0-based.
  let date = new Date(parts[0], parseInt(parts[1]) - 1, parts[2]);
  // Backtrack one day.
  date.setDate(date.getDate() - 1);
  return [date.getFullYear(),
          zfill(date.getMonth() + 1, 2),
          zfill(date.getDate(), 2)].join('-');
}

function processDailySlice(dateString, jsonData) {
  let currentDate = jsonData.date;
  let features = jsonData.features;

  // Cases grouped by country and province.
  let provinceFeatures = {};
  let countryFeatures = {};

  // "Re-hydrate" the features into objects ingestable by the map.
  for (let i = 0; i < features.length; i++) {
    let feature = formatFeatureForMap(features[i]);

    // City, province, country.
    let location = location_info[feature.properties.geoid].split(',');
    if (!provinceFeatures[location[1]]) {
      provinceFeatures[location[1]] = {total: 0, new: 0};
    }
    provinceFeatures[location[1]].total += feature.properties.total;
    provinceFeatures[location[1]].new += feature.properties.new;
    if (!countryFeatures[location[2]]) {
      countryFeatures[location[2]] = {total: 0, new: 0};
    }
    countryFeatures[location[2]].total += feature.properties.total;
    countryFeatures[location[2]].new += feature.properties.new;
  }

  dates.unshift(currentDate);

  countryFeaturesByDay[currentDate] = countryFeatures;
  provinceFeaturesByDay[currentDate] = provinceFeatures;
  atomicFeaturesByDay[currentDate] = features;

  // Only use the latest data for the map until we're done downloading
  // everything.
  if (dateString == 'latest') {
    showDataAtDate(currentDate);
  }
}

/**
 * Fetches the next daily slice of data we need. If no argument is provided,
 * fetches the latest slice first.
 */
function fetchDailySlice(dateString) {
  dateString = dateString || 'latest';

  let url = 'dailies/' + dateString.replace(/-/g, '.') + '.json';
  if (dateString == 'latest') {
    url += '?nocache=' + timestamp;
  }
  fetch(url)
      .then(function(response) {
        if (response.status == 200) {
          return response.json();
        } else {
          // We're done downloading data.
          onAllDailySlicesFetched();
        }
      })
      .then(function(jsonData) {
        if (!jsonData) {
          return;
        }
        processDailySlice(dateString, jsonData);

        // Now fetch the next (older) slice of data.
        fetchDailySlice(oneDayBefore(jsonData.date));
  });
}

function onAllDailySlicesFetched() {
  buildTimeControl();
  document.getElementById('spread').addEventListener('click', animateMap);
  let latestDate = dates[dates.length - 1];
}

// Takes an array of features, and bundles them in a way that the map API
// can ingest.
function formatFeatureSetForMap(features) {
  return {type: 'FeatureCollection', features: features};
}

// Tweaks the given object to make it ingestable as a feature by the map API.
function formatFeatureForMap(feature) {
  feature.type = 'Feature';
  if (!feature.properties) {
    // This feature is missing key data, add a placeholder.
    feature.properties = {geoid: '0|0'};
  }
  let coords = feature.properties.geoid.split('|');
  // Flip latitude and longitude.
  feature.geometry = {'type': 'Point', 'coordinates': [coords[1], coords[0]]};
  return feature;
}

function fetchWhoData() {
  const params = {
    'where': '1=1',
    'geometryType': 'esriGeometryEnvelope',
    'spatialRel': 'esriSpatialRelIntersects',
    'units': 'esriSRUnit_Meter',
    'returnGeodetic': 'true',
    'outFields': 'cum_conf%2C+ADM0_NAME',
    'returnGeometry': 'false',
    'returnCentroid': 'true',
    'featureEncoding': 'esriDefault',
    'multipatchOption': 'xyFootprint',
    'applyVCSProjection': 'false',
    'returnIdsOnly': 'false',
    'returnUniqueIdsOnly': 'false',
    'returnCountOnly': 'false',
    'returnExtentOnly': 'false',
    'returnQueryGeometry': 'false',
    'returnDistinctValues': 'false',
    'cacheHint': 'false',
    'returnZ': 'false',
    'returnM': 'false',
    'returnExceededLimitFeatures': 'true',
    'f': 'pjson'
  }
  const token = '5T5nSi527N4F7luB';
  let paramArray = [];
  for (let p in params) {
    paramArray.push(p + '=' + params[p]);
  }
  const url = 'https://services.arcgis.com/' +
      token + '/' +
      'ArcGIS/rest/services/COVID_19_CasesByCountry(pl)_VIEW/FeatureServer/0/query?' +
      paramArray.join('&');

  fetch(url)
    .then(function(response) { return response.json(); })
    .then(function(jsonData) {
      let obj = jsonData.features;
      list = '';
      // Sort according to decreasing confirmed cases.
      obj.sort(function(a, b) {
        return b.attributes.cum_conf - a.attributes.cum_conf;
      });
      for (let i = 0; i < obj.length; ++i) {
        let location = obj[i];
        if (!location || !location.attributes || !location.centroid) {
          // We can't do much with this location.
          continue;
        }
        let name = location.attributes.ADM0_NAME || '';
        let lat = location.centroid.x || 0;
        let lon = location.centroid.y || 0;
        let cumConf = location.attributes.cum_conf || 0;
        let legendGroup = 'default';
        if (cumConf <= 10) {
          legendGroup = '10';
        } else if (cumConf <= 100) {
          legendGroup = '100';
        } else if (cumConf <= 500) {
          legendGroup = '500';
        } else if (cumConf <= 2000) {
          legendGroup = '2000';
        }

        list += '<li><button onClick="handleFlyTo(' + lat + ',' + lon + ',' + 4 + ')"><span class="label">' + name + '</span><span class="num legend-group-' + legendGroup + '">' + cumConf.toLocaleString() + '</span></span></button></li>';
      }
      document.getElementById('location-list').innerHTML = list;
    });
}

// Load the location data (geo names from latitude and longitude).
fetch('location_info.data')
  .then(function(response) { return response.text(); })
  .then(function(responseText) {
    let lines = responseText.split('\n');
    for (let i = 0; i < lines.length; i++) {
      let parts = lines[i].split(':');
      location_info[parts[0]] = parts[1];
    }
  });

// Load latest counts from scraper
fetch('latestCounts.json?nocache=' + timestamp)
  .then(function(response) { return response.json(); })
  .then(function(jsonData) {
    document.getElementById('total-cases').innerText = jsonData[0].caseCount;
    document.getElementById('last-updated-date').innerText = jsonData[0].date;
  });

// Build list of locations with counts

// Filter list of locations
function filterList() {
  let filter = document.getElementById('location-filter').value.toUpperCase();
  ul = document.getElementById('location-list');
  let list_items = document.getElementById('location-list').getElementsByTagName('li');
  let clearFilter = document.getElementById('clear-filter');
  // Loop through all list items, and hide those who don't match the search query
  for (let i = 0; i < list_items.length; ++i) {
    let label = list_items[i].getElementsByClassName('label')[0];
    let txtValue = label.textContent || label.innerText;
    // Show/hide the clear filter button.
    clearFilter.style.display = !!filter ? 'flex' : 'none';

    // Show/hide matching list items.
    const show = txtValue.toUpperCase().indexOf(filter) != -1;
    list_items[i].style.display = show ? 'list-item' : 'none';
  }
}

function clearFilter() {
  document.getElementById('location-filter').value = '';
  filterList();
}

function fetchAboutPage() {
  fetch('about.html')
    .then(function(response) { return response.text(); })
    .then(function(html) { handleShowModal(html); });
}

function handleShowModal(html) {
  let modal = document.getElementById('modal');
  let modalWrapper = document.getElementById('modal-wrapper');
  // switch elements to have 'display' value (block, flex) but keep hidden via opacity
  modalWrapper.classList.add('is-block');
  modal.classList.add('is-flex');
  setTimeout(function () {
    // for transition
    modalWrapper.classList.add('is-visible');
    modal.classList.add('is-visible');
  }, 40);
  modal.innerHTML = html;
}

function handleHideModal() {
  let modal = document.getElementById('modal');
  let modalWrapper = document.getElementById('modal-wrapper');
  modalWrapper.classList.remove('is-visible');
  modal.classList.remove('is-visible');
  setTimeout(function () {
    // for transition
    modalWrapper.classList.remove('is-block');
    modal.classList.add('is-flex');
  }, 400);
}

function showLegend() {
  let list = document.getElementById('legend').getElementsByTagName('ul')[0];
  for (let i = 0; i < COLOR_MAP.length; i++) {
    let color = COLOR_MAP[i];
    let item = document.createElement('li');
    let circle = document.createElement('span');
    circle.className = 'circle';
    circle.style.backgroundColor = color[0];
    let label = document.createElement('span');
    label.className = 'label';
    label.textContent = color[1];
    item.appendChild(circle);
    item.appendChild(label);
    list.appendChild(item);
  }
}

function addMapLayer(map, id, featureProperty, circleColor) {
  map.addLayer({
    'id': id,
    'type': 'circle',
    'source': 'counts',
    'paint': {
      'circle-radius': [
        'case', [
          '<',
          0, [
            'number', [
              'get',
              featureProperty
            ]
          ]
        ], [
          '*', [
            'log10', [
              'sqrt', [
                'get',
                featureProperty
              ]
            ]
          ],
          10
        ],
        0
      ],
      'circle-color': circleColor,
      'circle-opacity': 0.6,
    }
  });
}

function initMap() {
  mapboxgl.accessToken = MAPBOX_TOKEN;
  map = new mapboxgl.Map({
    container: 'map',
    style: 'mapbox://styles/healthmap/ck7o47dgs1tmb1ilh5b1ro1vn',
    center: [10, 0],
    zoom: 1,
  }).addControl(new mapboxgl.NavigationControl());

  window.handleFlyTo = function(lat, lon, zoom, item) {
    map.flyTo({ center: [lat, lon], zoom: zoom })
    window.scrollTo({
      top: 0,
      left: 0,
      behavior: 'smooth'
    });
  }

  timeControl.addEventListener('input', function() {
    setTimeControlLabel(timeControl.value);
    showDataAtDate(dates[timeControl.value]);
  });

  map.on('load', function () {
    map.addSource('counts', {
      'type': 'geojson',
      'data': formatFeatureSetForMap([])
    });
    let circleColorForTotals = ['step', ['get', 'total']];
    // Don't use the last color here (for new cases).
    for (let i = 0; i < COLOR_MAP.length - 1; i++) {
      let color = COLOR_MAP[i];
      circleColorForTotals.push(color[0]);
      if (color.length > 2) {
        circleColorForTotals.push(color[2]);
      }
    }

    addMapLayer(map, 'totals', 'total', circleColorForTotals);
    addMapLayer(map, 'daily', 'new', 'cornflowerblue');

    // Create a popup, but don't add it to the map yet.
    let popup = new mapboxgl.Popup({
      closeButton: false,
      closeOnClick: false
    });

    map.on('mouseenter', 'totals', function (e) {
      // Change the cursor style as a UI indicator.
      map.getCanvas().style.cursor = 'pointer';

      let props = e.features[0].properties;
      let geo_id = props.geoid;
      let coordinatesString = geo_id.split('|');
      let lat = parseFloat(coordinatesString[0]);
      let lng = parseFloat(coordinatesString[1]);
      // Country, province, city
      let location = location_info[geo_id].split(',');
      // Remove empty strings
      location = location.filter(function (el) { return el != ''; });
      let description =
        '<h3 class="popup-header">' + location.join(', ') + '</h3>' +
        '<div>' + '<strong>Number of Cases: </strong>' + props.total + '</div>';

      // Ensure that if the map is zoomed out such that multiple
      // copies of the feature are visible, the popup appears
      // over the copy being pointed to.
      while (Math.abs(e.lngLat.lng - lng) > 180) {
        lng += e.lngLat.lng > lng ? 360 : -360;
      }

      // Populate the popup and set its coordinates
      // based on the feature found.
      popup
        .setLngLat([lng, lat])
        .setHTML(description)
        .addTo(map);
    });

    map.on('mouseleave', 'totals', function () {
      map.getCanvas().style.cursor = '';
      popup.remove();
    });

    fetchDailySlice();
    fetchWhoData();
    showLegend();
  });
}
