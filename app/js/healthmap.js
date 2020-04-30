// Constants
var ANIMATION_FRAME_DURATION_MS = 300;
var CASE_GRAPH_WIDTH_PX = 220;
var CASE_GRAPH_HEIGHT_PX = 120;

var COLOR_MAP = [
  ['#67009e', '< 10', 10],
  ['#921694', '11–100', 100],
  ['#d34d60', '101–500', 500],
  ['#fb9533', '501–2000', 2000],
  ['#edf91c', '> 2000'],
  ['cornflowerblue', 'New'],
];
var MAPBOX_TOKEN = 'pk.eyJ1IjoiaGVhbHRobWFwIiwiYSI6ImNrOGl1NGNldTAyYXYzZnBqcnBmN3RjanAifQ.H377pe4LPPcymeZkUBiBtg';

// This is a single threshold for now, but is meant to become a multi-stage
// logic.
var ZOOM_THRESHOLD = 2;

// Runtime constants
var timestamp = (new Date()).getTime();

// Globals
var locationInfo = {};
// A map from 2-letter ISO country codes to full names
var countryNames = {};
// A map from country names to most recent data (case count, etc.).
var latestDataPerCountry = {};
var dates = [];
var map;
// The same popup object will be reused.
var popup;

var currentIsoDate;

// An object mapping dates to JSON objects with the corresponding data.
// for that day, grouped by country, province, or ungrouped (smallest
// granularity level).
var countryFeaturesByDay = {};
var provinceFeaturesByDay = {};
var atomicFeaturesByDay = {};

var timeControl = document.getElementById('slider');

function onMapZoomChanged() {
  showDataAtDate(currentIsoDate);
}

function showDataAtDate(isodate) {
  if (currentIsoDate != isodate) {
    currentIsoDate = isodate;
  }
  var zoom = map.getZoom();
  var featuresToShow = [];
  // Show per-country data for low zoom levels, but only for the most recent
  // date.
  if (zoom <= ZOOM_THRESHOLD && currentIsoDate == dates[dates.length - 1]) {
    for (var country in latestDataPerCountry) {
      var countryData = latestDataPerCountry[country];
      var feature = formatFeatureForMap({
        properties: {
          geoid: countryData[0] + '|' + countryData[1],
          total: countryData[2],
          new: 0
        }
      });
      featuresToShow.push(feature);
    }
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
  var i = 0;
  var stepMap = setInterval(function() {
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

  var parts = dateString.split('-');
  // Month is 0-based.
  var date = new Date(parts[0], parseInt(parts[1]) - 1, parts[2]);
  // Backtrack one day.
  date.setDate(date.getDate() - 1);
  return [date.getFullYear(),
          zfill(date.getMonth() + 1, 2),
          zfill(date.getDate(), 2)].join('-');
}

function processDailySlice(dateString, jsonData) {
  var currentDate = jsonData.date;
  var features = jsonData.features;

  // Cases grouped by country and province.
  var provinceFeatures = {};
  var countryFeatures = {};

  // "Re-hydrate" the features into objects ingestable by the map.
  for (var i = 0; i < features.length; i++) {
    var feature = formatFeatureForMap(features[i]);

    // If we don't know where this is, discard.
    if (!locationInfo[feature.properties.geoid]) {
      continue;
    }
    // City, province, country.
    var location = locationInfo[feature.properties.geoid].split(',');
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

  var url = 'dailies/' + dateString.replace(/-/g, '.') + '.json';
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

function onBasicDataFetched() {
  // We can now start getting daily data.
  fetchDailySlice();
}

function onAllDailySlicesFetched() {
  buildTimeControl();
  document.getElementById('spread').addEventListener('click', animateMap);
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
  // If the 'new' property is absent, assume 0.
  if (isNaN(feature.properties.new)) {
    feature.properties.new = 0;
  }
  var coords = feature.properties.geoid.split('|');
  // Flip latitude and longitude.
  feature.geometry = {'type': 'Point', 'coordinates': [coords[1], coords[0]]};
  return feature;
}

function fetchWhoData() {
  var params = {
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
  var token = '5T5nSi527N4F7luB';
  var paramArray = [];
  for (var p in params) {
    paramArray.push(p + '=' + params[p]);
  }
  var url = 'https://services.arcgis.com/' +
      token + '/' +
      'ArcGIS/rest/services/COVID_19_CasesByCountry(pl)_VIEW/' +
      'FeatureServer/0/query?' +
      paramArray.join('&');

  return fetch(url)
    .then(function(response) { return response.json(); })
    .then(function(jsonData) {
      var obj = jsonData.features;
      list = '';
      // Sort according to decreasing confirmed cases.
      obj.sort(function(a, b) {
        return b.attributes.cum_conf - a.attributes.cum_conf;
      });
      for (var i = 0; i < obj.length; ++i) {
        var location = obj[i];
        if (!location || !location.attributes || !location.centroid) {
          // We can't do much with this location.
          continue;
        }
        var name = location.attributes.ADM0_NAME || '';
        var lon = location.centroid.x || 0;
        var lat = location.centroid.y || 0;
        var geoid = '' + lat + '|' + lon;
        var cumConf = location.attributes.cum_conf || 0;
        var legendGroup = 'default';
        latestDataPerCountry[name] = [lat, lon, cumConf];
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

        list += '<li><button onClick="handleFlyTo(' + lon + ',' + lat +
            ',' + 4 + ')"><span class="label">' + name +
            '</span><span class="num legend-group-' + legendGroup + '">' +
            cumConf.toLocaleString() + '</span></span></button></li>';
      }
      document.getElementById('location-list').innerHTML = list;
    });
}

// Load the location data (geo names from latitude and longitude).
function fetchLocationData() {
  return fetch('location_info.data')
    .then(function(response) { return response.text(); })
    .then(function(responseText) {
      var lines = responseText.split('\n');
      for (var i = 0; i < lines.length; i++) {
        var parts = lines[i].split(':');
        locationInfo[parts[0]] = parts[1];
      }
    });
}

function fetchCountryNames() {
  return fetch('countries.data')
    .then(function(response) { return response.text(); })
    .then(function(responseText) {
      var countries = responseText.trim().split('|');
      for (var i = 0; i < countries.length; i++) {
        var parts = countries[i].split(':');
        countryNames[parts[1]] = parts[0];
      }
    });
}

// Load latest counts from scraper
function fetchLatestCounts() {
  return fetch('latestCounts.json?nocache=' + timestamp)
    .then(function(response) { return response.json(); })
    .then(function(jsonData) {
      document.getElementById('total-cases').innerText = jsonData[0].caseCount;
      document.getElementById('last-updated-date').innerText = jsonData[0].date;
    });
}

// Build list of locations with counts

// Filter list of locations
function filterList() {
  var filter = document.getElementById('location-filter').value.toUpperCase();
  ul = document.getElementById('location-list');
  var list_items = document.getElementById(
      'location-list').getElementsByTagName('li');
  var clearFilter = document.getElementById('clear-filter');
  // Loop through all list items, and hide those who don't match the search
  // query.
  for (var i = 0; i < list_items.length; ++i) {
    var label = list_items[i].getElementsByClassName('label')[0];
    var txtValue = label.textContent || label.innerText;
    // Show/hide the clear filter button.
    clearFilter.style.display = !!filter ? 'flex' : 'none';

    // Show/hide matching list items.
    var show = txtValue.toUpperCase().indexOf(filter) != -1;
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
  var modal = document.getElementById('modal');
  var modalWrapper = document.getElementById('modal-wrapper');
  // Switch elements to have 'display' value (block, flex) but keep hidden via
  // opacity
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
  var modal = document.getElementById('modal');
  var modalWrapper = document.getElementById('modal-wrapper');
  modalWrapper.classList.remove('is-visible');
  modal.classList.remove('is-visible');
  setTimeout(function () {
    // for transition
    modalWrapper.classList.remove('is-block');
    modal.classList.add('is-flex');
  }, 400);
}

function showLegend() {
  var list = document.getElementById('legend').getElementsByTagName('ul')[0];
  for (var i = 0; i < COLOR_MAP.length; i++) {
    var color = COLOR_MAP[i];
    var item = document.createElement('li');
    var circle = document.createElement('span');
    circle.className = 'circle';
    circle.style.backgroundColor = color[0];
    var label = document.createElement('span');
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

function sameLocation(geoid_a, geoid_b) {
  // Comparing the strings directly seems sufficient for now, but we might need
  // to round to fewer decimal places first.
  return geoid_a == geoid_b;
}

function makeCaseGraph(geoid) {
  var svg = d3.select(document.createElementNS(d3.namespaces.svg, 'svg'));
  svg.attr('width', CASE_GRAPH_WIDTH_PX).
      attr('height', CASE_GRAPH_HEIGHT_PX);

  var historicalFeaturesForHere = [];
  var dates = [];
  var cases = [];
  for (var date in atomicFeaturesByDay) {
    var features = atomicFeaturesByDay[date];
    for (var i = 0; i < features.length; i++) {
      var f = features[i];
      if (sameLocation(geoid, f.properties.geoid)) {
        f.properties.date = date;
        cases.push({
          date: d3.timeParse("%Y-%m-%d")(date),
          total: f.properties.total});
      }
    }
  }

  var xScale = d3.scaleTime()
      .domain(d3.extent(cases, function(c) { return c.date; }))
      .range([0, CASE_GRAPH_WIDTH_PX]);

  svg.append('g')
      .attr('transform', 'translate(0,' + CASE_GRAPH_HEIGHT_PX + ')')
      .call(d3.axisBottom(xScale));

  var yScale = d3.scaleLinear()
      .domain([0, d3.max(cases, function(c) { return c.total; })])
      .range([CASE_GRAPH_HEIGHT_PX, 0]);

  svg.append("g").call(d3.axisLeft(yScale));

  var casesLine = d3.line()
    .x(function(c) { return xScale(c.date);}) // apply the x scale to the x data
    .y(function(c) { return yScale(c.total);}) // apply the y scale to the y data

  svg.append("path")
      .attr('d', casesLine(cases))
      .attr('fill', 'none')
      .attr('stroke', 'steelblue')
      .attr('stroke-width', 1.5);

  return svg.node();
}

function showPopupForEvent(e) {
  if (!e.features.length) {
    // We can't do much without a feature.
    return;
  }

  var f = e.features[0];
  var props = f.properties;
  var geo_id = props.geoid;
  var coordinatesString = geo_id.split('|');
  var lat = parseFloat(coordinatesString[0]);
  var lng = parseFloat(coordinatesString[1]);
  // Country, province, city
  var location = locationInfo[geo_id].split(',');
  // Replace country code with name if necessary
  if (location[2].length == 2) {
    location[2] = countryNames[location[2]];
  }
  // Remove empty strings
  location = location.filter(function (el) { return el != ''; });

  var content = document.createElement('div');
  content.innerHTML = '<h3 class="popup-header">' + location.join(', ') +
      '</h3>' + '<div>' + '<strong>Number of Cases: </strong>' +
      props.total.toLocaleString() + '</div>';

  // Only show case graphs for atomic locations.
  if (map.getZoom() > ZOOM_THRESHOLD) {
    content.appendChild(makeCaseGraph(geo_id));
  }

  // Ensure that if the map is zoomed out such that multiple
  // copies of the feature are visible, the popup appears
  // over the copy being pointed to.
  while (Math.abs(e.lngLat.lng - lng) > 180) {
    lng += e.lngLat.lng > lng ? 360 : -360;
  }
  popup
    .setLngLat([lng, lat])
    .setDOMContent(content)
    .addTo(map);
}


function handleFlyTo(lat, lon, zoom, item) {
  map.flyTo({ center: [lat, lon], zoom: zoom })
  window.scrollTo({
    top: 0,
    left: 0,
    behavior: 'smooth'
  });
};


function initMap() {
  mapboxgl.accessToken = MAPBOX_TOKEN;
  map = new mapboxgl.Map({
    'container': 'map',
    'style': 'mapbox://styles/healthmap/ck7o47dgs1tmb1ilh5b1ro1vn',
    'center': [10, 0],
    'zoom': 1,
  }).addControl(new mapboxgl.NavigationControl());
  popup = new mapboxgl.Popup({
    'closeButton': false,
    'closeOnClick': false
  });

  timeControl.addEventListener('input', function() {
    setTimeControlLabel(timeControl.value);
    showDataAtDate(dates[timeControl.value]);
  });

  map.on('load', function () {
    map.addSource('counts', {
      'type': 'geojson',
      'data': formatFeatureSetForMap([])
    });
    var circleColorForTotals = ['step', ['get', 'total']];
    // Don't use the last color here (for new cases).
    for (var i = 0; i < COLOR_MAP.length - 1; i++) {
      var color = COLOR_MAP[i];
      circleColorForTotals.push(color[0]);
      if (color.length > 2) {
        circleColorForTotals.push(color[2]);
      }
    }

    addMapLayer(map, 'totals', 'total', circleColorForTotals);
    addMapLayer(map, 'daily', 'new', 'cornflowerblue');

    map.on('mouseenter', 'totals', function (e) {
      // Change the cursor style as a UI indicator.
      map.getCanvas().style.cursor = 'pointer';

      showPopupForEvent(e);
    });

    map.on('zoom', onMapZoomChanged);

    map.on('mouseleave', 'totals', function () {
      map.getCanvas().style.cursor = '';
      popup.remove();
    });

    // Get the basic data about locations before we can start getting daily
    // slices.
    Promise.all([
      fetchLatestCounts(),
      fetchCountryNames(),
      fetchLocationData(),
      fetchWhoData()
    ]).then(onBasicDataFetched);

    showLegend();
  });
}

// Exports
window['initMap'] = initMap;
window['handleFlyTo'] = handleFlyTo;
