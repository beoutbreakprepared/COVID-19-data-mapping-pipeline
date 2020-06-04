var mapboxgl = {}

mapboxgl.accessToken = '';

/** @constructor */
mapboxgl.Map = function(options) {};

mapboxgl.Map.prototype.addControl = function(obj) {};
mapboxgl.Map.prototype.addLayer = function(obj) {};
mapboxgl.Map.prototype.addSource = function(s, obj) {};
mapboxgl.Map.prototype.getCanvas = function() {};
mapboxgl.Map.prototype.getSource = function(s, obj) {};
mapboxgl.Map.prototype.getZoom = function() {};
mapboxgl.Map.prototype.on = function(e, t, f) {};
mapboxgl.Map.prototype.flyTo = function(obj) {};

/** @constructor */
mapboxgl.NavigationControl = function() {};

/** @constructor */
mapboxgl.Popup = function(options) {};

mapboxgl.Popup.prototype.addTo = function(m) {};
mapboxgl.Popup.prototype.fitBounds = function(b) {};
mapboxgl.Popup.prototype.remove = function() {};
mapboxgl.Popup.prototype.setDOMContent = function(c) {};
mapboxgl.Popup.prototype.setLngLat = function(l) {};
