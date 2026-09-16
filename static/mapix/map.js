(() => {
  'use strict';

  const REGIONS = ['world', 'africa', 'europe', 'asia', 'north-america', 'south-america', 'oceania'];
  const MAP_WIDTH = 3600;
  const MAP_HEIGHT = 1800;
  const COUNTRY_SELECTOR = '[data-country], [data-target-country]';
  const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
  const countryId = node => node.getAttribute('data-country') || node.getAttribute('data-target-country');

  function numberAttribute(node, name) {
    const value = Number(node.getAttribute(name));
    if (!Number.isFinite(value) || value <= 0) throw new Error('Invalid map config');
    return value;
  }

  function readMapConfig(svg) {
    const views = {};
    for (const region of REGIONS) {
      const view = (svg.getAttribute(`data-view-${region}`) || '').split(/\s+/).map(Number);
      if (view.length !== 4 || view.some(value => !Number.isFinite(value)) ||
          view[2] <= 0 || view[3] <= 0) throw new Error('Invalid region view');
      views[region] = view;
    }
    return {
      views,
      wrapX: numberAttribute(svg, 'data-wrap-x'),
      wrapThreshold: numberAttribute(svg, 'data-wrap-threshold'),
    };
  }

  function startsNearDateline(node, threshold) {
    if (node.hasAttribute('cx')) return Number(node.getAttribute('cx')) < threshold;
    const coordinates = (node.getAttribute('d') || '').match(/-?\d+(?:\.\d+)?/g) || [];
    for (let index = 0; index < coordinates.length; index += 2) {
      if (Number(coordinates[index]) < threshold) return true;
    }
    return false;
  }

  function addDatelineCopies(svg, wrapX, threshold) {
    const group = document.createElementNS(svg.namespaceURI, 'g');
    group.id = 'mapix-wrap-copies';
    group.setAttribute('aria-hidden', 'true');
    for (const node of [...svg.querySelectorAll(COUNTRY_SELECTOR)]) {
      if (!startsNearDateline(node, threshold)) continue;
      const copy = node.cloneNode(true);
      copy.setAttribute('transform', `translate(${wrapX} 0)`);
      copy.setAttribute('data-mapix-wrap-copy', '');
      copy.setAttribute('aria-hidden', 'true');
      group.append(copy);
    }
    svg.append(group);
  }

  function parseMap(source) {
    const parsed = new DOMParser().parseFromString(source, 'image/svg+xml');
    const root = parsed.documentElement;
    const tags = new Set(['svg', 'g', 'path', 'circle']);
    const attributes = new Set([
      'xmlns', 'viewBox', 'role', 'aria-label', 'id', 'data-country',
      'data-target-country', 'data-wrap-x', 'data-wrap-threshold',
      ...REGIONS.map(region => `data-view-${region}`),
      'fill-rule', 'd', 'cx', 'cy', 'r', 'fill', 'pointer-events',
    ]);
    if (root.localName !== 'svg' || root.namespaceURI !== 'http://www.w3.org/2000/svg') {
      throw new Error('Invalid map');
    }
    // Le fichier local ne contient que des formes : refuser tout contenu actif,
    // lien, style ou titre au lieu de l'insérer dans le document.
    for (const node of [root, ...root.querySelectorAll('*')]) {
      if (!tags.has(node.localName) || node.namespaceURI !== root.namespaceURI ||
          [...node.attributes].some(attribute => !attributes.has(attribute.name)) ||
          (node.hasAttribute('fill') && node.getAttribute('fill') !== 'transparent')) {
        throw new Error('Unsafe map');
      }
    }
    if (!root.querySelector(COUNTRY_SELECTOR)) throw new Error('Empty map');
    return document.importNode(root, true);
  }

  function create(container, options = {}) {
    let svg = null;
    let destroyed = false;
    let configuredViews = null;
    let currentRegion = 'world';
    let initialView = [0, 0, MAP_WIDTH, MAP_HEIGHT];
    let view = [...initialView];
    let horizontalExtent = MAP_WIDTH;
    let interactive = true;
    let found = new Set();
    let imperfect = new Set();
    let drag = null;
    let suppressClick = false;
    const countries = new Map();
    const timers = new Map();
    const listeners = [];
    const controls = document.createElement('div');
    controls.className = 'map-controls';
    const zoomIn = document.createElement('button');
    const zoomOut = document.createElement('button');
    for (const [button, label, text] of [[zoomIn, 'Agrandir la carte', '+'], [zoomOut, 'Réduire la carte', '−']]) {
      button.type = 'button';
      button.setAttribute('aria-label', label);
      button.textContent = text;
      controls.append(button);
    }

    function listen(node, type, callback, settings) {
      node.addEventListener(type, callback, settings);
      listeners.push(() => node.removeEventListener(type, callback, settings));
    }

    function renderView() {
      if (!svg || destroyed) return;
      view[0] = clamp(view[0], 0, horizontalExtent - view[2]);
      view[1] = clamp(view[1], 0, MAP_HEIGHT - view[3]);
      svg.setAttribute('viewBox', view.join(' '));
      zoomIn.disabled = view[2] <= initialView[2] / 8 + 0.001;
      zoomOut.disabled = view[2] >= initialView[2] - 0.001;
    }

    function zoom(factor, point = {x: view[0] + view[2] / 2, y: view[1] + view[3] / 2}) {
      if (!svg || destroyed) return;
      const width = clamp(view[2] * factor, initialView[2] / 8, initialView[2]);
      const ratio = width / view[2];
      view = [point.x - (point.x - view[0]) * ratio,
        point.y - (point.y - view[1]) * ratio, width, view[3] * ratio];
      renderView();
    }

    function select(node) {
      if (!interactive) return;
      const target = node.closest?.(COUNTRY_SELECTOR);
      if (!destroyed && target && svg.contains(target)) options.onCountry?.(countryId(target));
    }

    function endDrag() {
      if (drag && svg.hasPointerCapture(drag.id)) svg.releasePointerCapture(drag.id);
      drag = null;
      svg.classList.remove('is-dragging');
    }

    function clearFeedback() {
      for (const timer of timers.values()) clearTimeout(timer);
      timers.clear();
      for (const nodes of countries.values()) {
        for (const node of nodes) node.classList.remove('is-wrong', 'is-correct', 'is-solution');
      }
    }

    function setRegion(region) {
      if (destroyed) return;
      currentRegion = REGIONS.includes(region) ? region : 'world';
      if (!configuredViews) return;
      initialView = [...configuredViews[currentRegion]];
      view = [...initialView];
      horizontalExtent = Math.max(MAP_WIDTH, initialView[0] + initialView[2]);
      if (svg) endDrag();
      suppressClick = false;
      clearFeedback();
      renderView();
    }

    function setInteractive(enabled) {
      interactive = Boolean(enabled);
      if (!svg || destroyed) return;
      svg.classList.toggle('is-selection-disabled', !interactive);
      for (const node of svg.querySelectorAll(COUNTRY_SELECTOR)) {
        if (node.hasAttribute('data-mapix-wrap-copy')) continue;
        if (interactive) {
          node.setAttribute('tabindex', '0');
          node.setAttribute('role', 'button');
          node.setAttribute('aria-label', 'Choisir ce territoire');
        } else {
          node.removeAttribute('tabindex');
          node.removeAttribute('role');
          node.removeAttribute('aria-label');
        }
      }
    }

    function setFound(countryIds, imperfectIds = []) {
      if (destroyed) return;
      found = new Set(countryIds);
      imperfect = new Set(imperfectIds);
      for (const [id, nodes] of countries) {
        for (const node of nodes) {
          node.classList.toggle('is-found', found.has(id));
          node.classList.toggle('is-imperfect', found.has(id) && imperfect.has(id));
          if (found.has(id)) node.classList.remove('is-correct');
        }
      }
    }

    function setRevealed(id) {
      if (destroyed) return;
      for (const [country, nodes] of countries) {
        for (const node of nodes) node.classList.toggle('is-solution', country === id);
      }
    }

    function flashWrong(id) {
      if (destroyed || !countries.has(id)) return;
      clearTimeout(timers.get(id));
      for (const node of countries.get(id)) node.classList.add('is-wrong');
      timers.set(id, setTimeout(() => {
        for (const node of countries.get(id)) node.classList.remove('is-wrong');
        timers.delete(id);
      }, 650));
    }

    function markCorrect(id, isImperfect = false) {
      if (destroyed || !countries.has(id)) return;
      clearTimeout(timers.get(id));
      timers.delete(id);
      for (const node of countries.get(id)) {
        node.classList.remove('is-wrong');
        node.classList.add('is-correct');
        node.classList.toggle('is-imperfect', isImperfect);
      }
    }

    function destroy() {
      if (destroyed) return;
      if (svg) endDrag();
      destroyed = true;
      clearFeedback();
      for (const remove of listeners) remove();
      countries.clear();
      svg?.remove();
      controls.remove();
    }

    const ready = (async () => {
      const response = await fetch('/static/mapix/world.svg');
      if (!response.ok) throw new Error('Map unavailable');
      const source = await response.text();
      if (destroyed) return;
      svg = parseMap(source);
      const config = readMapConfig(svg);
      configuredViews = config.views;
      addDatelineCopies(svg, config.wrapX, config.wrapThreshold);
      svg.classList.add('map-svg');
      // Un rôle img rendrait ses boutons descendants invisibles à l'accessibilité.
      svg.setAttribute('role', 'group');
      svg.setAttribute('aria-label', 'Carte interactive. Utilisez les boutons pour zoomer et les flèches pour déplacer la carte.');
      svg.setAttribute('tabindex', '0');
      for (const node of svg.querySelectorAll(COUNTRY_SELECTOR)) {
        const id = countryId(node);
        if (!countries.has(id)) countries.set(id, []);
        countries.get(id).push(node);
      }
      listen(svg, 'click', event => {
        if (suppressClick) { suppressClick = false; return; }
        select(event.target);
      });
      listen(svg, 'keydown', event => {
        if (interactive && (event.key === 'Enter' || event.key === ' ') && event.target.matches(COUNTRY_SELECTOR)) {
          event.preventDefault();
          if (!event.repeat) select(event.target);
        }
        const direction = {ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1]}[event.key];
        if (direction) {
          event.preventDefault();
          view[0] += direction[0] * view[2] * 0.1;
          view[1] += direction[1] * view[3] * 0.1;
          renderView();
        }
      });
      listen(svg, 'wheel', event => {
        event.preventDefault();
        const matrix = svg.getScreenCTM();
        if (!matrix) return;
        const point = svg.createSVGPoint();
        point.x = event.clientX;
        point.y = event.clientY;
        const units = event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? container.clientHeight : 1;
        zoom(Math.exp(clamp(event.deltaY * units, -300, 300) * 0.002), point.matrixTransform(matrix.inverse()));
      }, {passive: false});
      listen(svg, 'pointerdown', event => {
        if (event.button !== 0 || !event.isPrimary) return;
        const matrix = svg.getScreenCTM();
        if (!matrix) return;
        suppressClick = false;
        drag = {id: event.pointerId, x: event.clientX, y: event.clientY, view: [...view], scale: matrix.a};
      });
      listen(svg, 'pointermove', event => {
        if (!drag || event.pointerId !== drag.id) return;
        if (event.buttons === 0) { endDrag(); return; }
        const dx = event.clientX - drag.x;
        const dy = event.clientY - drag.y;
        if (!suppressClick && Math.hypot(dx, dy) <= 4) return;
        suppressClick = true;
        svg.setPointerCapture(drag.id);
        svg.classList.add('is-dragging');
        view[0] = drag.view[0] - dx / drag.scale;
        view[1] = drag.view[1] - dy / drag.scale;
        renderView();
      });
      for (const event of ['pointerup', 'pointercancel', 'lostpointercapture']) listen(svg, event, endDrag);
      listen(svg, 'pointerleave', () => {
        if (drag && !svg.hasPointerCapture(drag.id)) endDrag();
      });
      listen(zoomIn, 'click', () => zoom(1 / 1.5));
      listen(zoomOut, 'click', () => zoom(1.5));
      container.replaceChildren(svg, controls);
      setRegion(currentRegion);
      setInteractive(interactive);
      setFound(found);
    })();

    return {ready, setRegion, setInteractive, setFound, setRevealed, flashWrong, markCorrect, destroy};
  }

  window.MapixMap = {create};
})();
