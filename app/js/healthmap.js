// Constants
const ANIMATION_FRAME_DURATION_MS = 300;
const COLOR_MAP = [
  ['#67009e', '< 10', 10],
  ['#921694', '11–100', 100],
  ['#d34d60', '101–500', 500],
  ['#fb9533', '501–2000', 2000],
  ['#edf91c', '> 2000'],
  ['cornflowerblue', 'New'],
]

// Runtime constants
const timestamp = (new Date()).getTime();

// Globals
let location_info = {};
let dates = [];
let map;

// An object mapping dates to JSON objects with the corresponding data.
// for that day.
let featuresByDay = {};
let timeControl = document.getElementById('slider');

function showDataAtDate(isodate) {
  map.getSource('counts').setData(featuresByDay[isodate]);
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
        let currentDate = jsonData.date;
        // "Re-hydrate" the features into objects ingestable by the map.
        jsonData.type = 'FeatureCollection';
        for (let i = 0; i < jsonData.features.length; i++) {
          let feature = jsonData.features[i];
          feature.type = 'Feature';
          let coords = feature.properties.geoid.split('|');
          // Flip latitude and longitude.
          feature.geometry = {'type': 'Point', 'coordinates': [coords[1], coords[0]]};
        }

        dates.unshift(currentDate);
        featuresByDay[currentDate] = jsonData;

        // Only use the latest data for the map until we're done downloading
        // everything.
        if (dateString == 'latest') {
          map.getSource('counts').setData(jsonData);
        }
        // Now fetch the next (older) slice of data.
        fetchDailySlice(oneDayBefore(currentDate));
  });
}

function onAllDailySlicesFetched() {
  buildTimeControl();
  document.getElementById('spread').addEventListener('click', animateMap);
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
fetch('who.json?nocache=' + timestamp)
  .then(function(response) { return response.json(); })
  .then(function(jsonData) {
    let obj = jsonData.features;
    list = '';
    for (let i = 0; i < obj.length; ++i) {
      let location = obj[i];
      let name, lat, lon, cumConf, legendGroup;
      name = location.attributes.ADM0_NAME ? location.attributes.ADM0_NAME : '';
      lat = location.centroid.x ? location.centroid.x : 0;
      lon = location.centroid.y ? location.centroid.y : 0;
      cumConf = location.attributes.cum_conf ? location.attributes.cum_conf : 0;
      legendGroup = location.attributes.legendGroup ? location.attributes.legendGroup : '';
      list += '<li><button onClick="handleFlyTo(' + lat + ',' + lon + ',' + 4 + ')"><span class="label">' + name + '</span><span class="num legend-group-' + legendGroup + '">' + cumConf + '</span></span></button></li>';
    }
    document.getElementById('location-list').innerHTML = list;
  });

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

function initMap() {
  mapboxgl.accessToken = 'pk.eyJ1IjoiaGVhbHRobWFwIiwiYSI6ImNrOGl1NGNldTAyYXYzZnBqcnBmN3RjanAifQ.H377pe4LPPcymeZkUBiBtg';
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
      'data': {
        'type': 'FeatureCollection',
        'features': []
      }
    });
    let circleColor = ['step', ['get', 'total']];
    // Don't use the last color here (for new cases).
    for (let i = 0; i < COLOR_MAP.length - 1; i++) {
      let color = COLOR_MAP[i];
      circleColor.push(color[0]);
      if (color.length > 2) {
        circleColor.push(color[2]);
      }
    }
    map.addLayer({
      'id': 'totals',
      'type': 'circle',
      'source': 'counts',
      'paint': {
        'circle-radius': [ 'case', ['<', 0, ['number', ['get', 'total']]], ['*', ['log10', ['sqrt', ['get', 'total']]], 10], 0 ],
        'circle-color': circleColor,
        'circle-opacity': .6,
    }});
    map.addLayer({
      'id': 'daily',
      'type': 'circle',
      'source': 'counts',
      'paint': {
        'circle-radius': [ 'case', ['<', 0, ['number', ['get', 'new']]], ['*', ['log10', ['sqrt', ['get', 'new']]], 10], 0 ],
        'circle-color': 'cornflowerblue',
        'circle-opacity': 0.6,
      }
    });

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
    showLegend();
  });
}
