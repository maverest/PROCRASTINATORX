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
    activeMode: document.getElementById('activeMode'),
    projectedScore: document.getElementById('projectedScore'),
    finalScore: document.getElementById('finalScore'),
    responseChart: document.getElementById('responseChart'),
    resultChart: document.getElementById('resultChart'),
    operationSummaries: document.getElementById('operationSummaries'),
    error: document.getElementById('errorMessage'),
    settingsError: document.getElementById('settingsError'),
    resultError: document.getElementById('resultError'),
    historyList: document.getElementById('historyList'),
    historyError: document.getElementById('historyError'),
    clearHistoryButton: document.getElementById('clearHistoryButton'),
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
    historyToken: 0,
    historyGeneration: 0,
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
    ++state.historyToken;
    showPanel(panel);
    if (panel === ui.scores) loadHistory();
  }

  function clearError() {
    [ui.error, ui.settingsError, ui.resultError].forEach((error) => {
      error.hidden = true;
      error.textContent = '';
    });
  }

  function showError(message) {
    ui.error.textContent = message;
    ui.error.hidden = false;
  }

  function clearSettingsError() {
    ui.settingsError.hidden = true;
    ui.settingsError.textContent = '';
  }

  function showSettingsError(message, field) {
    ui.settingsError.textContent = message;
    ui.settingsError.hidden = false;
    focusSettingsField(field);
  }

  function focusSettingsField(field) {
    const controls = {
      duration_seconds: ui.customDuration,
      operations: ui.operationInputs[0],
      addition: ui.additionLeftMinimum,
      'addition.left': ui.additionLeftMinimum,
      'addition.left.minimum': ui.additionLeftMinimum,
      'addition.left.maximum': ui.additionLeftMaximum,
      'addition.right': ui.additionRightMinimum,
      'addition.right.minimum': ui.additionRightMinimum,
      'addition.right.maximum': ui.additionRightMaximum,
      multiplication: ui.multiplicationLeftMinimum,
      'multiplication.left': ui.multiplicationLeftMinimum,
      'multiplication.left.minimum': ui.multiplicationLeftMinimum,
      'multiplication.left.maximum': ui.multiplicationLeftMaximum,
      'multiplication.right': ui.multiplicationRightMinimum,
      'multiplication.right.minimum': ui.multiplicationRightMinimum,
      'multiplication.right.maximum': ui.multiplicationRightMaximum,
    };
    const control = controls[field];
    if (control) control.focus();
  }

  function showResultError(message) {
    ui.resultError.textContent = message;
    ui.resultError.hidden = false;
  }

  function clearHistoryError() {
    ui.historyError.hidden = true;
    ui.historyError.textContent = '';
  }

  function showHistoryError(message) {
    ui.historyError.textContent = message;
    ui.historyError.hidden = false;
  }

  function isHistorySession(session) {
    return session
      && Number.isInteger(session.id)
      && typeof session.played_at === 'string'
      && ['classic', 'custom', 'constance'].includes(session.mode)
      && isIntegerInRange(session.duration_seconds, 1, 3600)
      && isIntegerInRange(session.score, 0, 9999)
      && ['timeout', 'stopped', 'exhausted'].includes(session.ended_reason)
      && ['not_applicable', 'pending', 'submitted'].includes(session.submission_status)
      && (session.nickname === null || typeof session.nickname === 'string');
  }

  function formatHistoryDate(playedAt) {
    const date = new Date(playedAt);
    if (Number.isNaN(date.valueOf())) return playedAt;
    return new Intl.DateTimeFormat('fr-CH', {
      dateStyle: 'short',
      timeStyle: 'short',
    }).format(date);
  }

  function renderHistory(sessions) {
    ui.historyList.replaceChildren();
    if (sessions.length === 0) {
      const empty = document.createElement('li');
      empty.className = 'history-empty';
      empty.textContent = 'Aucun score.';
      ui.historyList.append(empty);
      ui.clearHistoryButton.disabled = true;
      return;
    }

    sessions.forEach((session) => {
      const entry = document.createElement('li');
      const details = document.createElement('span');
      details.textContent = `${formatHistoryDate(session.played_at)} · ${session.mode} · ${session.duration_seconds}s · ${session.score}`;
      entry.append(details);

      if (session.ended_reason === 'stopped' || session.submission_status === 'pending') {
        const marks = document.createElement('span');
        marks.className = 'history-marks';
        if (session.ended_reason === 'stopped') {
          const stopped = document.createElement('span');
          stopped.textContent = '■';
          stopped.setAttribute('aria-label', 'Séance arrêtée');
          marks.append(stopped);
        }
        if (session.submission_status === 'pending') {
          const pending = document.createElement('span');
          pending.className = 'history-pending';
          pending.textContent = '○';
          pending.setAttribute('aria-label', 'Réservé pour le classement');
          marks.append(pending);
        }
        entry.append(marks);
      }
      ui.historyList.append(entry);
    });
    ui.clearHistoryButton.disabled = false;
  }

  async function loadHistory() {
    const token = ++state.historyToken;
    const generation = state.historyGeneration;
    clearHistoryError();
    ui.historyList.setAttribute('aria-busy', 'true');
    try {
      const response = await fetch('/games/calculatorx/history');
      if (!response.ok) throw new Error('history unavailable');
      const payload = await response.json();
      if (!payload || !Array.isArray(payload.sessions) || !payload.sessions.every(isHistorySession)) {
        throw new Error('invalid history');
      }
      if (
        token !== state.historyToken
        || generation !== state.historyGeneration
        || ui.scores.hidden
      ) return;
      renderHistory(payload.sessions);
    } catch (_error) {
      if (
        token === state.historyToken
        && generation === state.historyGeneration
        && !ui.scores.hidden
      ) {
        showHistoryError('Historique indisponible.');
      }
    } finally {
      if (token === state.historyToken) ui.historyList.removeAttribute('aria-busy');
    }
  }

  async function clearHistory() {
    if (!window.confirm('Effacer tous les scores locaux ?')) return;
    const token = ++state.historyToken;
    clearHistoryError();
    ui.clearHistoryButton.disabled = true;
    ui.historyList.setAttribute('aria-busy', 'true');
    try {
      const response = await fetch('/games/calculatorx/history', {method: 'DELETE'});
      if (!response.ok) throw new Error('history unavailable');
      ++state.historyGeneration;
      if (!ui.scores.hidden) loadHistory();
    } catch (_error) {
      if (token === state.historyToken && !ui.scores.hidden) {
        showHistoryError('Effacement impossible.');
        ui.clearHistoryButton.disabled = false;
      }
    } finally {
      if (token === state.historyToken) ui.historyList.removeAttribute('aria-busy');
    }
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
    validateCustomConfig(config);
    return config;
  }

  class SettingsError extends Error {
    constructor(message, field) {
      super(message);
      this.field = field;
    }
  }

  class SessionError extends Error {
    constructor(message, field = null) {
      super(message);
      this.field = field;
    }
  }

  function validateInteger(value, field, minimum, maximum, rangeMessage) {
    if (!Number.isInteger(value)) throw new SettingsError('Cette valeur doit être un entier.', field);
    if (value < minimum || value > maximum) throw new SettingsError(rangeMessage, field);
  }

  function validateRange(range, field) {
    validateInteger(range.minimum, `${field}.minimum`, 0, 9999, 'Le minimum doit être compris entre 0 et 9999.');
    validateInteger(range.maximum, `${field}.maximum`, 0, 9999, 'Le maximum doit être compris entre 0 et 9999.');
    if (range.minimum > range.maximum) {
      throw new SettingsError('Le minimum ne peut pas dépasser le maximum.', field);
    }
  }

  function validateCustomConfig(config) {
    validateInteger(config.duration_seconds, 'duration_seconds', 1, 3600, 'La durée doit être comprise entre 1 et 3600.');
    if (config.operations.length === 0) {
      throw new SettingsError('Choisis au moins une opération.', 'operations');
    }
    validateRange(config.addition.left, 'addition.left');
    validateRange(config.addition.right, 'addition.right');
    validateRange(config.multiplication.left, 'multiplication.left');
    validateRange(config.multiplication.right, 'multiplication.right');
    if (config.operations.includes('÷') && config.multiplication.left.maximum === 0) {
      throw new SettingsError('Le diviseur doit pouvoir être différent de zéro.', 'multiplication.left');
    }
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
    const enabledOperations = state.mode === 'custom' ? state.config.operations : OPERATIONS;
    enabledOperations.forEach((operator) => {
      const summary = statistics && statistics[operator];
      const group = document.createElement('div');
      const term = document.createElement('dt');
      const details = document.createElement('dd');
      term.textContent = operator;
      if (summary) {
        details.textContent = `${summary.count} · ${formatMilliseconds(summary.median_ms)} · ${formatMilliseconds(summary.fastest_ms)}–${formatMilliseconds(summary.slowest_ms)}`;
        details.setAttribute('aria-label', `${summary.count} réponses, médiane ${formatMilliseconds(summary.median_ms)}, meilleur temps ${formatMilliseconds(summary.fastest_ms)}, temps le plus lent ${formatMilliseconds(summary.slowest_ms)}`);
      } else {
        const emptySummary = {count: 0};
        details.textContent = `${emptySummary.count} · — · —–—`;
        details.setAttribute('aria-label', '0 réponse, aucune statistique de temps');
      }
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
    ui.activeMode.textContent = {classic: 'Classique', custom: 'Perso', constance: 'Constance'}[payload.mode];
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

  function showPreparationError(token, message = 'Impossible de préparer la partie.', field = null) {
    if (token !== state.roundToken) return;
    setPreparing(false);
    if (state.mode === 'custom' && field) {
      showPanel(ui.settings);
      showSettingsError(message, field);
      return;
    }
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
      .then(async (response) => {
        if (!response.ok) {
          const payload = await response.json().catch(() => null);
          throw new SessionError(
            typeof payload?.error === 'string' ? payload.error : 'Impossible de préparer la partie.',
            typeof payload?.field === 'string' ? payload.field : null,
          );
        }
        return response.json();
      })
      .then((payload) => {
        if (!isSession(payload)) throw new Error('invalid session');
        beginRound(payload, token);
      })
      .catch((error) => showPreparationError(token, error.message, error.field));
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
  ui.clearHistoryButton.addEventListener('click', clearHistory);
  ui.resetClassicButton.addEventListener('click', () => applyConfigToForm(classicCustomConfig()));
  ui.customForm.addEventListener('submit', (event) => {
    event.preventDefault();
    clearSettingsError();
    try {
      const config = configFromForm();
      state.mode = 'custom';
      state.config = config;
      prepareRound();
    } catch (error) {
      if (error instanceof SettingsError) showSettingsError(error.message, error.field);
      else showSettingsError('Réglages invalides.', null);
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
