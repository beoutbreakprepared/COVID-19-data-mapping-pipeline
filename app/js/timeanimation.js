
function updateTimeControl() {
  // There's no point in showing the time control if we only have data for one
  // date.
  if (dates.length < 2) {
    return;
  }
  document.getElementById('range-slider').style.display = 'flex';
  timeControl.min = 0;
  timeControl.max = dates.length - 1;
  // Keep the slider at max value.
  timeControl.value = dates.length - 1;
  setTimeControlLabel(dates.length - 1);
}

function toggleMapAnimation() {
  const shouldStart = !animationIntervalId;
  document.getElementById('playpause').setAttribute('src', 'img/' +
      (shouldStart ? 'pause' : 'play') + '.svg');
  if (shouldStart) {
    let i = 0;
    animationIntervalId = setInterval(function() {
      timeControl.value = i;
      showDataAtDate(dates[i]);
      setTimeControlLabel(i);
      i++;
      if (i === dates.length) {
        // We've reached the end.
        toggleMapAnimation();
      }
    }, ANIMATION_FRAME_DURATION_MS);
  } else {
    clearInterval(animationIntervalId);
    animationIntervalId = 0;
  }
}
