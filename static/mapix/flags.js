(() => {
  'use strict';

  function createImage(country) {
    const image = document.createElement('img');
    image.className = 'flag-image';
    image.src = `/static/mapix/flags/${country.id.toLowerCase()}.svg`;
    image.alt = '';
    image.draggable = false;
    image.loading = 'lazy';
    image.decoding = 'async';
    image.setAttribute('aria-hidden', 'true');
    return image;
  }

  window.MapixFlags = {createImage};
})();
