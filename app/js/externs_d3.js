var d3 = {};

d3.namespaces = {};
d3.namespaces.svg = {};

/** @constructor */
d3.Axis = function() {};

/** @return {d3.Axis} */
d3.Axis.prototype.tickValues = function(a) {};

/** @constructor */
d3.Line = function() {};

/** @return {d3.Line} */
d3.Line.prototype.x = function(f) {};

/** @return {d3.Line} */
d3.Line.prototype.y = function(f) {};


/** @constructor */
d3.Scale = function() {};

/** @return {d3.Scale} */
d3.Scale.prototype.domain = function(e) {};

/** @return {d3.Scale} */
d3.Scale.prototype.range = function(e) {};


/** @constructor */
d3.Selection = function() {};

/** @return {d3.Selection} */
d3.Selection.prototype.attr = function(k, v) {};

/** @return {d3.Selection} */
d3.Selection.prototype.append = function(e) {};

/** @return {d3.Selection} */
d3.Selection.prototype.call = function(e) {};

/** @return {d3.Selection} */
d3.Selection.prototype.node = function() {};

/** @return {d3.Axis} */
d3.axisBottom = function(a) {};

/** @return {d3.Axis} */
d3.axisLeft = function(a) {};

d3.extent = function(a, b) {};

/** @return {d3.Line} */
d3.line();

d3.max = function(c, f) {};

/** @return {d3.Scale} */
d3.scaleLinear = function() {};

/** @return {d3.Scale} */
d3.scaleTime = function() {};

/** @return {d3.Selection} */
d3.select = function(s) {};
d3.timeParse = function(t) {};
