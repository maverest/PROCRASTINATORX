(() => {
  'use strict';

  const OPERATIONS = ['+', '−', '×', '÷'];
  const PANELS = ['mode', 'settings', 'game', 'result', 'scores'];
  const STORAGE_KEYS = {
    mode: 'calculatorx:last-mode',
    customConfig: 'calculatorx:custom-config',
  };

  const ui = {
    mode: document.getElementById('modePanel'),
    settings: document.getElementById('settingsPanel'),
    game: document.getElementById('gamePanel'),
    result: document.getElementById('resultPanel'),
    scores: document.getElementById('scoresPanel'),
    classicButton: document.getElementById('classicButton'),
    customButton: document.getElementById('customButton'),
    constanceButton: document.getElementById('constanceButton'),
    scoresButton: document.getElementById('scoresButton'),
    customForm: document.getElementById('customForm'),
    customDuration: document.getElementById('customDuration'),
    operationInputs: Array.from(document.querySelectorAll('input[name="operations"]')),
    additionLeftMinimum: document.getElementById('additionLeftMinimum'),
    additionLeftMaximum: document.getElementById('additionLeftMaximum'),
    additionRightMinimum: document.getElementById('additionRightMinimum'),
    additionRightMaximum: document.getElementById('additionRightMaximum'),
    multiplicationLeftMinimum: document.getElementById('multiplicationLeftMinimum'),
    multiplicationLeftMaximum: document.getElementById('multiplicationLeftMaximum'),
    multiplicationRightMinimum: document.getElementById('multiplicationRightMinimum'),
    multiplicationRightMaximum: document.getElementById('multiplicationRightMaximum'),
    resetClassicButton: document.getElementById('resetClassicButton'),
    startCustomButton: document.getElementById('startCustomButton'),
    retry: document.getElementById('retryButton'),
    stopButton: document.getElementById('stopButton'),
    input: document.getElementById('answerInput'),
    problem: document.getElementById('problemText'),
    timer: document.getElementById('timerValue'),
    score: document.getElementById('scoreValue'),
    projectedScore: document.getElementById('projectedScore'),
    finalScore: document.getElementById('finalScore'),
    responseChart: document.getElementById('responseChart'),
    resultChart: document.getElementById('resultChart'),
    operationSummaries: document.getElementById('operationSummaries'),
    error: document.getElementById('errorMessage'),
    resultError: document.getElementById('resultError'),
  };

  const state = {
    roundToken: 0,
    preparing: false,
    finishing: false,
    problems: [],
    problemIndex: 0,
    score: 0,
    durationSeconds: 120,
    deadline: 0,
    roundStartedAt: 0,
    problemStartedAt: 0,
    frameId: 0,
    playing: false,
    mode: 'classic',
    config: {mode: 'classic'},
    samples: [],
    endedReason: null,
    lastResult: null,
  };

  function classicCustomConfig() {
    return {
      mode: 'custom',
      duration_seconds: 120,
      operations: [...OPERATIONS],
      addition: {
        left: {minimum: 2, maximum: 100},
        right: {minimum: 2, maximum: 100},
      },
      multiplication: {
        left: {minimum: 2, maximum: 12},
        right: {minimum: 2, maximum: 100},
      },
    };
  }

  function readStoredJson(key) {
    try {
      const rawValue = window.localStorage.getItem(key);
      return rawValue === null ? null : JSON.parse(rawValue);
    } catch (_error) {
      return null;
    }
  }

  function writeStoredJson(key, value) {
    try {
      window.localStorage.setItem(key, JSON.stringify(value));
    } catch (_error) {
      // A disabled local store must never prevent a game from starting.
    }
  }

  function isIntegerInRange(value, minimum, maximum) {
    return Number.isInteger(value) && value >= minimum && value <= maximum;
  }

  function isRange(value) {
    return value
      && isIntegerInRange(value.minimum, 0, 9999)
      && isIntegerInRange(value.maximum, 0, 9999)
      && value.minimum <= value.maximum;
  }

  function isCustomConfig(config) {
    return config
      && config.mode === 'custom'
      && isIntegerInRange(config.duration_seconds, 1, 3600)
      && Array.isArray(config.operations)
      && config.operations.length > 0
      && config.operations.every((operator) => OPERATIONS.includes(operator))
      && new Set(config.operations).size === config.operations.length
      && config.addition
      && isRange(config.addition.left)
      && isRange(config.addition.right)
      && config.multiplication
      && isRange(config.multiplication.left)
      && isRange(config.multiplication.right)
      && (!config.operations.includes('÷') || config.multiplication.left.maximum > 0);
  }

  function loadPreferences() {
    const storedMode = readStoredJson(STORAGE_KEYS.mode);
    const storedConfig = readStoredJson(STORAGE_KEYS.customConfig);
    state.mode = ['classic', 'custom', 'constance'].includes(storedMode) ? storedMode : 'classic';
    if (state.mode === 'custom' && isCustomConfig(storedConfig)) {
      state.config = storedConfig;
    } else if (state.mode === 'constance') {
      state.config = {mode: 'constance'};
    } else {
      state.mode = 'classic';
      state.config = {mode: 'classic'};
    }
    applyConfigToForm(isCustomConfig(storedConfig) ? storedConfig : classicCustomConfig());
  }

  function showPanel(panel) {
    PANELS.forEach((name) => {
      ui[name].hidden = ui[name] !== panel;
    });
  }

  function setPreparing(preparing) {
    state.preparing = preparing;
    [ui.classicButton, ui.constanceButton, ui.startCustomButton, ui.retry].forEach((button) => {
      button.disabled = preparing;
    });
  }

  function cancelPreparation() {
    if (!state.preparing) return;
    ++state.roundToken;
    setPreparing(false);
  }

  function navigateToPanel(panel) {
    cancelPreparation();
    showPanel(panel);
  }

  function clearError() {
    [ui.error, ui.resultError].forEach((error) => {
      error.hidden = true;
      error.textContent = '';
    });
  }

  function showError(message) {
    ui.error.textContent = message;
    ui.error.hidden = false;
  }

  function showResultError(message) {
    ui.resultError.textContent = message;
    ui.resultError.hidden = false;
  }

  function numberFrom(input) {
    return input.value.trim() === '' ? Number.NaN : Number(input.value);
  }

  function configFromForm() {
    const config = {
      mode: 'custom',
      duration_seconds: numberFrom(ui.customDuration),
      operations: ui.operationInputs.filter((input) => input.checked).map((input) => input.value),
      addition: {
        left: {
          minimum: numberFrom(ui.additionLeftMinimum),
          maximum: numberFrom(ui.additionLeftMaximum),
        },
        right: {
          minimum: numberFrom(ui.additionRightMinimum),
          maximum: numberFrom(ui.additionRightMaximum),
        },
      },
      multiplication: {
        left: {
          minimum: numberFrom(ui.multiplicationLeftMinimum),
          maximum: numberFrom(ui.multiplicationLeftMaximum),
        },
        right: {
          minimum: numberFrom(ui.multiplicationRightMinimum),
          maximum: numberFrom(ui.multiplicationRightMaximum),
        },
      },
    };
    if (!isCustomConfig(config)) throw new Error('Réglages invalides.');
    return config;
  }

  function applyConfigToForm(config) {
    ui.customDuration.value = String(config.duration_seconds);
    ui.operationInputs.forEach((input) => {
      input.checked = config.operations.includes(input.value);
    });
    ui.additionLeftMinimum.value = String(config.addition.left.minimum);
    ui.additionLeftMaximum.value = String(config.addition.left.maximum);
    ui.additionRightMinimum.value = String(config.addition.right.minimum);
    ui.additionRightMaximum.value = String(config.addition.right.maximum);
    ui.multiplicationLeftMinimum.value = String(config.multiplication.left.minimum);
    ui.multiplicationLeftMaximum.value = String(config.multiplication.left.maximum);
    ui.multiplicationRightMinimum.value = String(config.multiplication.right.minimum);
    ui.multiplicationRightMaximum.value = String(config.multiplication.right.maximum);
  }

  function isProblem(problem) {
    return Number.isInteger(problem.left)
      && OPERATIONS.includes(problem.operator)
      && Number.isInteger(problem.right)
      && Number.isInteger(problem.answer);
  }

  function isSession(payload) {
    return payload
      && payload.mode === state.mode
      && isIntegerInRange(payload.duration_seconds, 1, 3600)
      && Array.isArray(payload.problems)
      && payload.problems.length > 0
      && payload.problems.every(isProblem);
  }

  function renderProblem() {
    const problem = state.problems[state.problemIndex];
    ui.problem.textContent = `${problem.left} ${problem.operator} ${problem.right} =`;
    ui.input.value = '';
    state.problemStartedAt = performance.now();
    ui.input.focus();
  }

  function renderLiveChart() {
    window.CalculatorXChart.render(ui.responseChart, state.samples, {limit: 30});
  }

  function updateProjection(now) {
    if (state.score < 3) {
      ui.projectedScore.hidden = true;
      return;
    }
    const elapsed = now - state.roundStartedAt;
    if (elapsed <= 0) return;
    const projection = Math.round(state.score * state.durationSeconds * 1000 / elapsed);
    ui.projectedScore.textContent = `≈${projection}`;
    ui.projectedScore.hidden = false;
  }

  function formatMilliseconds(milliseconds) {
    const seconds = milliseconds / 1000;
    return seconds < 10 ? `${seconds.toFixed(2)}s` : `${seconds.toFixed(1)}s`;
  }

  function renderSummaries(statistics) {
    ui.operationSummaries.replaceChildren();
    OPERATIONS.forEach((operator) => {
      const summary = statistics && statistics[operator];
      if (!summary) return;
      const group = document.createElement('div');
      const term = document.createElement('dt');
      const details = document.createElement('dd');
      term.textContent = operator;
      details.textContent = `${summary.count} · ${formatMilliseconds(summary.median_ms)} · ${formatMilliseconds(summary.fastest_ms)}–${formatMilliseconds(summary.slowest_ms)}`;
      details.setAttribute('aria-label', `${summary.count} réponses, médiane ${formatMilliseconds(summary.median_ms)}, meilleur temps ${formatMilliseconds(summary.fastest_ms)}, temps le plus lent ${formatMilliseconds(summary.slowest_ms)}`);
      group.append(term, details);
      ui.operationSummaries.append(group);
    });
  }

  async function finishRound(token, reason) {
    if (token !== state.roundToken || !state.playing) return;
    state.playing = false;
    state.finishing = true;
    state.endedReason = reason;
    cancelAnimationFrame(state.frameId);
    ui.input.disabled = true;
    ui.projectedScore.hidden = true;
    if (reason === 'timeout') ui.timer.textContent = '0';
    ui.finalScore.textContent = String(state.score);
    ui.retry.disabled = true;
    ui.resultError.hidden = true;
    ui.resultError.textContent = '';
    window.CalculatorXChart.render(ui.resultChart, state.samples, {});
    renderSummaries({});
    showPanel(ui.result);

    const resultPayload = {
      mode: state.mode,
      duration_seconds: state.durationSeconds,
      score: state.score,
      ended_reason: reason,
      samples: state.samples.map((sample) => ({...sample})),
    };
    state.lastResult = {request: resultPayload, response: null};

    try {
      const response = await fetch('/games/calculatorx/result', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(resultPayload),
      });
      if (!response.ok) throw new Error('result unavailable');
      const payload = await response.json();
      if (token !== state.roundToken) return;
      state.lastResult.response = payload;
      renderSummaries(payload.statistics);
    } catch (_error) {
      if (token === state.roundToken) showResultError('Score non enregistré.');
    } finally {
      if (token === state.roundToken) {
        state.finishing = false;
        ui.retry.disabled = false;
        if (!ui.result.hidden) ui.retry.focus();
      }
    }
  }

  function updateClock(token) {
    if (token !== state.roundToken || !state.playing) return;
    const remaining = Math.max(0, state.deadline - performance.now());
    ui.timer.textContent = String(Math.ceil(remaining / 1000));
    if (remaining <= 0) {
      finishRound(token, 'timeout');
      return;
    }
    state.frameId = requestAnimationFrame(() => updateClock(token));
  }

  function beginRound(payload, token) {
    if (token !== state.roundToken) return;
    const now = performance.now();
    state.problems = payload.problems;
    state.problemIndex = 0;
    state.score = 0;
    state.samples = [];
    state.durationSeconds = payload.duration_seconds;
    state.roundStartedAt = now;
    state.deadline = now + payload.duration_seconds * 1000;
    state.endedReason = null;
    state.lastResult = null;
    state.playing = true;
    state.finishing = false;
    ui.score.textContent = '0';
    ui.timer.textContent = String(payload.duration_seconds);
    ui.projectedScore.hidden = true;
    ui.input.disabled = false;
    window.CalculatorXChart.clear(ui.responseChart);
    window.CalculatorXChart.clear(ui.resultChart);
    renderSummaries({});
    setPreparing(false);
    clearError();
    writeStoredJson(STORAGE_KEYS.mode, state.mode);
    if (state.mode === 'custom') writeStoredJson(STORAGE_KEYS.customConfig, state.config);
    showPanel(ui.game);
    renderProblem();
    updateClock(token);
  }

  function showPreparationError(token, message = 'Impossible de préparer la partie.') {
    if (token !== state.roundToken) return;
    setPreparing(false);
    showPanel(ui.mode);
    showError(message);
    ui.classicButton.focus();
  }

  function prepareRound() {
    if (state.preparing || state.playing) return;
    const token = ++state.roundToken;
    state.finishing = false;
    cancelAnimationFrame(state.frameId);
    clearError();
    setPreparing(true);
    fetch('/games/calculatorx/session', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(state.config),
    })
      .then((response) => {
        if (!response.ok) throw new Error('session unavailable');
        return response.json();
      })
      .then((payload) => {
        if (!isSession(payload)) throw new Error('invalid session');
        beginRound(payload, token);
      })
      .catch(() => showPreparationError(token));
  }

  function selectMode(mode) {
    state.mode = mode;
    state.config = {mode};
    prepareRound();
  }

  function handleAnswer() {
    if (!state.playing) return;
    const token = state.roundToken;
    const now = performance.now();
    if (now >= state.deadline) {
      finishRound(token, 'timeout');
      return;
    }
    if (!/^\d+$/.test(ui.input.value)) return;
    const current = state.problems[state.problemIndex];
    if (Number(ui.input.value) !== current.answer) return;

    state.samples.push({
      operator: current.operator,
      elapsed_ms: Math.max(0, Math.round(now - state.problemStartedAt)),
    });
    state.score += 1;
    state.problemIndex += 1;
    ui.score.textContent = String(state.score);
    updateProjection(now);
    renderLiveChart();
    if (state.problemIndex >= state.problems.length) {
      finishRound(token, 'exhausted');
      return;
    }
    renderProblem();
  }

  ui.classicButton.addEventListener('click', () => selectMode('classic'));
  ui.constanceButton.addEventListener('click', () => selectMode('constance'));
  ui.customButton.addEventListener('click', () => {
    clearError();
    navigateToPanel(ui.settings);
    ui.customDuration.focus();
  });
  ui.scoresButton.addEventListener('click', () => navigateToPanel(ui.scores));
  ui.resetClassicButton.addEventListener('click', () => applyConfigToForm(classicCustomConfig()));
  ui.customForm.addEventListener('submit', (event) => {
    event.preventDefault();
    try {
      const config = configFromForm();
      state.mode = 'custom';
      state.config = config;
      prepareRound();
    } catch (error) {
      showPreparationError(state.roundToken, error.message);
    }
  });
  ui.retry.addEventListener('click', prepareRound);
  ui.stopButton.addEventListener('click', () => finishRound(state.roundToken, 'stopped'));
  ui.input.addEventListener('input', handleAnswer);
  document.querySelectorAll('[data-panel]').forEach((button) => {
    button.addEventListener('click', () => {
      if (button.dataset.panel === 'settings') {
        const config = state.mode === 'custom' && isCustomConfig(state.config)
          ? state.config
          : classicCustomConfig();
        applyConfigToForm(config);
        navigateToPanel(ui.settings);
        ui.customDuration.focus();
        return;
      }
      navigateToPanel(ui.mode);
      ui.classicButton.focus();
    });
  });
  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Enter' || state.playing || state.preparing || state.finishing) return;
    if (event.target.closest('a, button, input, select, textarea, [role="button"]')) return;
    if (ui.mode.hidden && ui.result.hidden) return;
    event.preventDefault();
    prepareRound();
  });

  loadPreferences();
  showPanel(ui.mode);
})();
