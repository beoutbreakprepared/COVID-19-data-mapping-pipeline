// Constants
const ANIMATION_FRAME_DURATION_MS = 300;
const CASE_GRAPH_WIDTH_PX = 200;
const CASE_GRAPH_HEIGHT_PX = 120;

const COLOR_MAP = [
  ['#67009e', '< 10', 10],
  ['#921694', '11–100', 100],
  ['#d34d60', '101–500', 500],
  ['#fb9533', '501–2000', 2000],
  ['#edf91c', '> 2000'],
  ['cornflowerblue', 'New'],
];
const MAPBOX_TOKEN = 'pk.eyJ1IjoiaGVhbHRobWFwIiwiYSI6ImNrOGl1NGNldTAyYXYzZnBqcnBmN3RjanAifQ.H377pe4LPPcymeZkUBiBtg';

// This is a single threshold for now, but is meant to become a multi-stage
// logic.
const ZOOM_THRESHOLD = 2;

// Runtime constants
const timestamp = (new Date()).getTime();

// Globals
let dataProvider;
let locationInfo = {};
// A map from 2-letter ISO country codes to country objects.
let countries = {};
let dates = [];
let map;
// The same popup object will be reused.
let popup;

let currentIsoDate;
let animationIntervalId = 0;

// An object mapping dates to JSON objects with the corresponding data.
// for that day, grouped by country, province, or ungrouped (smallest
// granularity level).
let countryFeaturesByDay = {};
let provinceFeaturesByDay = {};
let atomicFeaturesByDay = {};

let timeControl;

function onMapZoomChanged() {
  showDataAtDate(currentIsoDate);
}

function showDataAtDate(isodate) {
  if (currentIsoDate != isodate) {
    currentIsoDate = isodate;
  }
  const zoom = map.getZoom();
  let featuresToShow = [];
  // Show per-country data for low zoom levels, but only for the most recent
  // date.
  if (zoom <= ZOOM_THRESHOLD && currentIsoDate == dates[dates.length - 1]) {
    const data = dataProvider.getLatestDataPerCountry();
    for (let centroid_geoid in data) {
      let countryData = data[centroid_geoid];
      let country = countryData[0];
      let feature = formatFeatureForMap({
        'properties': {
          'geoid': centroid_geoid,
          'total': countryData[1],
          'new': 0
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

/** Fills with leading zeros to the desired width. */
function zfill(n, width) {
  n = n + '';
  return n.length >= width ? n : new Array(width - n.length + 1).join('0') + n;
}

function onAllDailySlicesFetched() {
}

// Takes an array of features, and bundles them in a way that the map API
// can ingest.
function formatFeatureSetForMap(features) {
  return {'type': 'FeatureCollection', 'features': features};
}

// Tweaks the given object to make it ingestable as a feature by the map API.
function formatFeatureForMap(feature) {
  feature.type = 'Feature';
  if (!feature['properties']) {
    // This feature is missing key data, add a placeholder.
    feature['properties'] = {'geoid': '0|0'};
  }
  // If the 'new' property is absent, assume 0.
  if (isNaN(feature['properties']['new'])) {
    feature['properties']['new'] = 0;
  }
  let coords = feature['properties']['geoid'].split('|');
  // Flip latitude and longitude.
  feature['geometry'] = {'type': 'Point', 'coordinates': [coords[1], coords[0]]};
  return feature;
}

// Build list of locations with counts

// Filter list of locations
function filterList() {
  let filter = document.getElementById('location-filter').value.toUpperCase();
  let ul = document.getElementById('location-list');
  let list_items = document.getElementById(
      'location-list').getElementsByTagName('li');
  let clearFilter = document.getElementById('clear-filter');
  // Loop through all list items, and hide those who don't match the search
  // query.
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
  // Attach an event to the close button once this is finished rendering.
  setTimeout(function() {
    document.getElementById('modal-cancel').onclick = handleHideModal;
  }, 0);
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

function sameLocation(geoid_a, geoid_b) {
  // Comparing the strings directly seems sufficient for now, but we might need
  // to round to fewer decimal places first.
  return geoid_a == geoid_b;
}

function makeCaseGraph(geoid) {
  let svg = d3.select(document.createElementNS(d3.namespaces.svg, 'svg'));
  svg.attr('width', CASE_GRAPH_WIDTH_PX).
      attr('height', CASE_GRAPH_HEIGHT_PX);

  let historicalFeaturesForHere = [];
  let cases = [];
  for (let i = 0; i < dates.length; i++) {
    const date = dates[i];
    let features = atomicFeaturesByDay[date];
    for (let i = 0; i < features.length; i++) {
      let f = features[i];
      if (sameLocation(geoid, f['properties']['geoid'])) {
        f['properties']['date'] = date;
        cases.push({
          'date': d3.timeParse("%Y-%m-%d")(date),
          'total': f['properties']['total']});
      }
    }
  }

  let xScale = d3.scaleTime()
      .domain(d3.extent(cases, function(c) { return c['date']; }))
      .range([0, CASE_GRAPH_WIDTH_PX]);

  svg.append('g')
      .attr('transform', 'translate(0,' + CASE_GRAPH_HEIGHT_PX + ')')
      .call(d3.axisBottom(xScale).tickValues([]));

  let yScale = d3.scaleLinear()
      .domain([0, d3.max(cases, function(c) { return c['total']; })])
      .range([CASE_GRAPH_HEIGHT_PX, 0]);

  svg.append("g")
      .call(d3.axisLeft(yScale).tickValues([]));

  let casesLine = d3.line()
    .x(function(c) { return xScale(c['date']);}) // apply the x scale to the x data
    .y(function(c) { return yScale(c['total']);}) // apply the y scale to the y data

  svg.append("path")
      .attr('d', casesLine(cases))
      .attr('fill', 'none')
      .attr('stroke', 'steelblue')
      .attr('stroke-width', 1.5);

  return svg.node();
}

function showPopupForEvent(e) {
  if (!e['features'].length) {
    // We can't do much without a feature.
    return;
  }

  let f = e['features'][0];
  let props = f['properties'];
  let geo_id = props['geoid'];
  let coordinatesString = geo_id.split('|');
  let lat = parseFloat(coordinatesString[0]);
  let lng = parseFloat(coordinatesString[1]);

  let locationString = '';
  let totalCaseCount = 0;
  if (map.getZoom() > ZOOM_THRESHOLD) {
    // Country, province, city
    let location = locationInfo[geo_id].split(',');
    // Replace country code with name if necessary
    if (location[2].length == 2) {
      location[2] = countries[location[2]].getName();
    }
    // Remove empty strings
    location = location.filter(function (el) { return el != ''; });
    locationString = location.join(', ');
    totalCaseCount = props['total'];
  } else {
    const data = dataProvider.getLatestDataPerCountry();
    if (!data[geo_id]) {
      return;
    }
    const countryData = data[geo_id];
    locationString = countryData[0];
    totalCaseCount = countryData[1];
  }

  let content = document.createElement('div');
  content.innerHTML = '<h3 class="popup-header">' + locationString +
      '</h3>' + '<div>' + '<strong>Number of Cases: </strong>' +
      totalCaseCount.toLocaleString() + '</div>';

  // Only show case graphs for atomic locations.
  if (map.getZoom() > ZOOM_THRESHOLD) {
    content.appendChild(makeCaseGraph(geo_id));
  }

  // Ensure that if the map is zoomed out such that multiple
  // copies of the feature are visible, the popup appears
  // over the copy being pointed to.
  while (Math.abs(e['lngLat']['lng'] - lng) > 180) {
    lng += e['lngLat']['lng'] > lng ? 360 : -360;
  }
  popup
    .setLngLat([lng, lat])
    .setDOMContent(content)
    .addTo(map);
}


function flyToCountry(event) {
  let target = event.target;
  while (!target.getAttribute('country')) {
    target = target.parentNode;
  }
  const country = countries[target.getAttribute('country')];
  const dest = country.getMainBoundingBox();
  map.fitBounds([[dest[0], dest[1]], [dest[2], dest[3]]]);
};


function init() {
  dataProvider = new DataProvider(
      'https://raw.githubusercontent.com/ghdsi/covid-19/master/');

  const hash = window.location.href.split('#')[1] || '';
  if (hash == 'autodrive') {
    document.body.classList.add('autodrive');
  }

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

  timeControl = document.getElementById('slider');
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

    dataProvider.fetchInitialData(function() {
      // Once the initial data is here, fetch the daily slices.
      dataProvider.fetchDailySlices(function() {
        dates = dates.sort();
      });
    });
    // Get the basic data about locations before we can start getting daily
    // slices.

    showLegend();
  });
  document.getElementById('spread').
      addEventListener('click', toggleMapAnimation);
  document.getElementById('playpause').setAttribute('src', 'img/play.svg');
}

function countryInit() {
  dataProvider = new DataProvider(
      'https://raw.githubusercontent.com/ghdsi/covid-19/master/');
  dataProvider.loadCountryData(showCountryPage);
}

function showCountryPage(data) {
  console.log(data);
}

// Exports
if (typeof(globalThis) === 'undefined' && typeof(global) !== "undefined") {
    globalThis = global;
}
globalThis['clearFilter'] = clearFilter;
globalThis['fetchAboutPage'] = fetchAboutPage;
globalThis['filterList'] = filterList;
globalThis['init'] = init;
globalThis['countryInit'] = countryInit;
