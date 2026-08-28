(() => {
  'use strict';

  const SVG_NAMESPACE = 'http://www.w3.org/2000/svg';
  const WIDTH = 680;
  const HEIGHT = 160;
  const PADDING = 8;
  const MINIMUM_SCALE_MS = 4000;
  const OPERATION_COLORS = {
    '+': '#72d6a6',
    '−': '#7db7ff',
    '×': '#e8b36a',
    '÷': '#d99af7',
  };

  function element(name, attributes = {}) {
    const node = document.createElementNS(SVG_NAMESPACE, name);
    Object.entries(attributes).forEach(([attribute, value]) => {
      node.setAttribute(attribute, String(value));
    });
    return node;
  }

  function clear(svg) {
    svg.replaceChildren();
  }

  function median(values) {
    const ordered = [...values].sort((left, right) => left - right);
    const middle = Math.floor(ordered.length / 2);
    if (ordered.length % 2 === 1) return ordered[middle];
    return (ordered[middle - 1] + ordered[middle]) / 2;
  }

  function render(svg, samples, {limit} = {}) {
    clear(svg);
    const visibleSamples = Number.isInteger(limit) && limit > 0
      ? samples.slice(-limit)
      : samples.slice();
    if (visibleSamples.length === 0) return;

    const drawing = element('svg', {
      viewBox: `0 0 ${WIDTH} ${HEIGHT}`,
      width: '100%',
      height: HEIGHT,
      preserveAspectRatio: 'none',
      focusable: 'false',
      'aria-hidden': 'true',
    });
    const elapsedTimes = visibleSamples.map((sample) => sample.elapsed_ms);
    const scaleMaximum = Math.max(MINIMUM_SCALE_MS, ...elapsedTimes);
    const chartWidth = WIDTH - PADDING * 2;
    const chartHeight = HEIGHT - PADDING * 2;
    const x = (index) => PADDING + (
      visibleSamples.length === 1 ? chartWidth / 2 : index * chartWidth / (visibleSamples.length - 1)
    );
    const y = (elapsedMs) => PADDING + chartHeight * (1 - elapsedMs / scaleMaximum);

    for (const fraction of [0.25, 0.5, 0.75, 1]) {
      drawing.append(element('line', {
        x1: PADDING,
        x2: WIDTH - PADDING,
        y1: y(scaleMaximum * fraction),
        y2: y(scaleMaximum * fraction),
        stroke: '#303641',
        'stroke-width': 1,
        'vector-effect': 'non-scaling-stroke',
      }));
    }

    const medianY = y(median(elapsedTimes));
    drawing.append(element('line', {
      x1: PADDING,
      x2: WIDTH - PADDING,
      y1: medianY,
      y2: medianY,
      stroke: '#89919d',
      'stroke-width': 1,
      'stroke-dasharray': '5 5',
      'vector-effect': 'non-scaling-stroke',
    }));

    drawing.append(element('polyline', {
      points: visibleSamples.map((sample, index) => `${x(index)},${y(sample.elapsed_ms)}`).join(' '),
      fill: 'none',
      stroke: '#89919d',
      'stroke-opacity': 0.55,
      'stroke-width': 1.5,
      'vector-effect': 'non-scaling-stroke',
    }));

    visibleSamples.forEach((sample, index) => {
      drawing.append(element('circle', {
        cx: x(index),
        cy: y(sample.elapsed_ms),
        r: 3.5,
        fill: OPERATION_COLORS[sample.operator] || '#f4f6f8',
        stroke: '#101216',
        'stroke-width': 1,
        'vector-effect': 'non-scaling-stroke',
      }));
    });

    svg.append(drawing);
  }

  window.CalculatorXChart = {clear, render};
})();
