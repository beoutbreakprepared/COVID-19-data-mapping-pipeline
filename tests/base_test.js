function assert(condition, explanation) {
  if (!condition) {
    throw explanation;
  }
}

function assertEquals(expected, actual, explanation) {
    assert(expected == actual, explanation);
}
