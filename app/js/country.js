/** @constructor */
let Country = function(code, name, boundingBoxes) {

  /**
   * This country's two-letter iso code.
   * @const
   * @private
   */
  this.code_ = code;

  /**
   * This country's official name, as used in common language.
   * @const
   * @private
   */
  this.name_ = name;

  /**
   * A list of bounding boxes encapsulating this country's geographical regions.
   * @const
   * @private
   */
  this.boundingBoxes_ = boundingBoxes;
};


Country.prototype.getName = function() {
  return this.name_;
}

Country.prototype.getMainBoundingBox = function() {
  // Assume the 'main' geographical region is listed first.
  return this.boundingBoxes_[0];
}
