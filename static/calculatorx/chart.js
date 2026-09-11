(() => {
  'use strict';

  const SVG_NAMESPACE = 'http://www.w3.org/2000/svg';
  const WIDTH = 680;
  const HEIGHT = 160;
  const PADDING = 8;
  const MINIMUM_SCALE_MS = 4000;
  const OPERATION_COLORS = {
    '+': 'var(--add)',
    '−': 'var(--subtract)',
    '×': 'var(--multiply)',
    '÷': 'var(--divide)',
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

  function mean(values) {
    return values.reduce((total, value) => total + value, 0) / values.length;
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
        stroke: 'var(--chart-grid)',
        'stroke-width': 1,
        'vector-effect': 'non-scaling-stroke',
      }));
    }

    const meanY = y(mean(elapsedTimes));
    drawing.append(element('line', {
      x1: PADDING,
      x2: WIDTH - PADDING,
      y1: meanY,
      y2: meanY,
      stroke: 'var(--chart-line)',
      'stroke-width': 1,
      'stroke-dasharray': '5 5',
      'vector-effect': 'non-scaling-stroke',
    }));

    drawing.append(element('polyline', {
      points: visibleSamples.map((sample, index) => `${x(index)},${y(sample.elapsed_ms)}`).join(' '),
      fill: 'none',
      stroke: 'var(--chart-line)',
      'stroke-opacity': 0.55,
      'stroke-width': 1.5,
      'vector-effect': 'non-scaling-stroke',
    }));

    visibleSamples.forEach((sample, index) => {
      drawing.append(element('circle', {
        cx: x(index),
        cy: y(sample.elapsed_ms),
        r: 3.5,
        fill: OPERATION_COLORS[sample.operator] || 'var(--text)',
        stroke: 'var(--chart-point-stroke)',
        'stroke-width': 1,
        'vector-effect': 'non-scaling-stroke',
      }));
    });

    svg.append(drawing);
  }

  window.CalculatorXChart = {clear, render};
})();
