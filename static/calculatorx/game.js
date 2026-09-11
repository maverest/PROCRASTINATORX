(() => {
  'use strict';

  const OPERATIONS = ['+', '−', '×', '÷'];
  const MODE_LABELS = {classic: 'Classique', custom: 'Perso', constance: 'Constance'};
  const PANELS = ['mode', 'settings', 'ready', 'game', 'result', 'scores'];
  const STORAGE_KEYS = {
    mode: 'calculatorx:last-mode',
    customConfig: 'calculatorx:custom-config',
    theme: 'calculatorx:theme',
  };

  const ui = {
    mode: document.getElementById('modePanel'),
    settings: document.getElementById('settingsPanel'),
    ready: document.getElementById('readyPanel'),
    game: document.getElementById('gamePanel'),
    result: document.getElementById('resultPanel'),
    scores: document.getElementById('scoresPanel'),
    themeToggle: document.getElementById('themeToggleButton'),
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
    startButton: document.getElementById('startButton'),
    readyModeValue: document.getElementById('readyModeValue'),
    readyDurationValue: document.getElementById('readyDurationValue'),
    retry: document.getElementById('retryButton'),
    stopButton: document.getElementById('stopButton'),
    chartToggleButton: document.getElementById('chartToggleButton'),
    input: document.getElementById('answerInput'),
    problem: document.getElementById('problemText'),
    timer: document.getElementById('timerValue'),
    score: document.getElementById('scoreValue'),
    activeMode: document.getElementById('activeMode'),
    projectedScore: document.getElementById('projectedScore'),
    finalScore: document.getElementById('finalScore'),
    responseChart: document.getElementById('responseChart'),
    responseFigure: document.getElementById('responseFigure'),
    resultChart: document.getElementById('resultChart'),
    operationSummaries: document.getElementById('operationSummaries'),
    error: document.getElementById('errorMessage'),
    settingsError: document.getElementById('settingsError'),
    resultError: document.getElementById('resultError'),
    submitScoreButton: document.getElementById('submitScoreButton'),
    historyList: document.getElementById('historyList'),
    historyError: document.getElementById('historyError'),
    clearHistoryButton: document.getElementById('clearHistoryButton'),
    classicLeaderboardTab: document.getElementById('classicLeaderboardTab'),
    constanceLeaderboardTab: document.getElementById('constanceLeaderboardTab'),
    classicLeaderboard: document.getElementById('classicLeaderboard'),
    constanceLeaderboard: document.getElementById('constanceLeaderboard'),
    leaderboardError: document.getElementById('leaderboardError'),
    profilePicker: document.getElementById('profilePicker'),
    profileList: document.getElementById('profileList'),
    profileForm: document.getElementById('profileForm'),
    newProfileInput: document.getElementById('newProfileInput'),
    createProfileButton: document.getElementById('createProfileButton'),
    profileCancelButton: document.getElementById('profileCancelButton'),
    profileError: document.getElementById('profileError'),
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
    leaderboardMode: 'classic',
    leaderboardTokens: {classic: 0, constance: 0},
    profilePickerToken: 0,
    profilePickerTrigger: null,
    pendingSubmissionSessionId: null,
    pendingSubmissionMode: null,
    profileCreateInFlight: false,
    submissionInFlight: false,
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
    const storedTheme = readStoredJson(STORAGE_KEYS.theme);
    const systemTheme = window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
    applyTheme(storedTheme === 'light' || storedTheme === 'dark' ? storedTheme : systemTheme);
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

  function applyTheme(theme) {
    document.documentElement.dataset.theme = theme;
    const lightIsActive = theme === 'light';
    ui.themeToggle.textContent = lightIsActive ? '☾' : '☀︎';
    ui.themeToggle.setAttribute(
      'aria-label',
      lightIsActive ? 'Activer le thème sombre' : 'Activer le thème clair',
    );
  }

  function showPanel(panel) {
    PANELS.forEach((name) => {
      ui[name].hidden = ui[name] !== panel;
    });
  }

  function setPreparing(preparing) {
    state.preparing = preparing;
    [ui.classicButton, ui.constanceButton, ui.startCustomButton, ui.startButton, ui.retry].forEach((button) => {
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
    closeProfilePicker({restoreFocus: false});
    ++state.historyToken;
    showPanel(panel);
    if (panel === ui.mode) loadHistory();
    if (panel === ui.scores) {
      selectLeaderboard(state.leaderboardMode);
    }
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

  function clearLeaderboardError() {
    ui.leaderboardError.hidden = true;
    ui.leaderboardError.textContent = '';
  }

  function showLeaderboardError(message) {
    ui.leaderboardError.textContent = message;
    ui.leaderboardError.hidden = false;
  }

  function clearProfileError() {
    ui.profileError.hidden = true;
    ui.profileError.textContent = '';
  }

  function showProfileError(message) {
    ui.profileError.textContent = message;
    ui.profileError.hidden = false;
  }

  function isHistorySession(session) {
    return session
      && Number.isInteger(session.id)
      && typeof session.played_at === 'string'
      && ['classic', 'custom', 'constance'].includes(session.mode)
      && isIntegerInRange(session.duration_seconds, 1, 3600)
      && (
        session.elapsed_ms === null
        || isIntegerInRange(session.elapsed_ms, 1, session.duration_seconds * 1000)
      )
      && isIntegerInRange(session.score, 0, historyScoreLimit(session))
      && typeof session.responses_per_second === 'number'
      && Number.isFinite(session.responses_per_second)
      && session.responses_per_second >= 0
      && ['timeout', 'stopped', 'exhausted'].includes(session.ended_reason)
      && ['not_applicable', 'pending', 'submitted'].includes(session.submission_status)
      && (session.nickname === null || typeof session.nickname === 'string');
  }

  function historyScoreLimit(session) {
    return session.mode === 'custom'
      ? Math.max(512, Math.ceil(512 * session.duration_seconds / 120))
      : 9999;
  }

  function isPendingEligibleSession(session) {
    return isHistorySession(session)
      && session.submission_status === 'pending'
      && ['classic', 'constance'].includes(session.mode)
      && session.duration_seconds === 120
      && ['timeout', 'exhausted'].includes(session.ended_reason);
  }

  function isProfile(profile) {
    return profile
      && typeof profile.id === 'string'
      && typeof profile.nickname === 'string'
      && profile.nickname.length > 0;
  }

  function isLeaderboardScore(score) {
    return score
      && isIntegerInRange(score.rank, 1, 999999)
      && typeof score.nickname === 'string'
      && isIntegerInRange(score.score, 0, 9999);
  }

  function renderResultSubmission(response) {
    const session = response?.session;
    const eligible = response?.leaderboard_eligible === true && isPendingEligibleSession(session);
    ui.submitScoreButton.hidden = !eligible;
  }

  function profilePickerFocusable() {
    return Array.from(
      ui.profilePicker.querySelectorAll('button:not([disabled]), input:not([disabled])'),
    ).filter((element) => !element.hidden);
  }

  function setProfilePickerBusy(busy) {
    ui.profilePicker.setAttribute('aria-busy', String(busy));
    ui.profileCancelButton.disabled = busy;
    ui.newProfileInput.disabled = busy;
    ui.createProfileButton.disabled = busy;
    ui.profileList.querySelectorAll('button').forEach((button) => {
      button.disabled = busy;
    });
  }

  function closeProfilePicker({restoreFocus = true} = {}) {
    if (ui.profilePicker.hidden) return;
    ++state.profilePickerToken;
    ui.profilePicker.hidden = true;
    state.pendingSubmissionSessionId = null;
    state.pendingSubmissionMode = null;
    state.profileCreateInFlight = false;
    state.submissionInFlight = false;
    setProfilePickerBusy(false);
    const trigger = state.profilePickerTrigger;
    state.profilePickerTrigger = null;
    if (restoreFocus && trigger && trigger.isConnected && !trigger.hidden && !trigger.disabled) {
      trigger.focus();
    }
  }

  function renderProfiles(profiles, token) {
    if (token !== state.profilePickerToken || ui.profilePicker.hidden) return;
    ui.profileList.replaceChildren();
    profiles.forEach((profile) => {
      const button = document.createElement('button');
      button.className = 'profile-button';
      button.type = 'button';
      button.textContent = profile.nickname;
      button.addEventListener('click', () => submitPendingScore(profile.id));
      ui.profileList.append(button);
    });
  }

  async function openProfilePicker(session, trigger) {
    if (!isPendingEligibleSession(session) || state.submissionInFlight) return;
    const token = ++state.profilePickerToken;
    state.pendingSubmissionSessionId = session.id;
    state.pendingSubmissionMode = session.mode;
    state.profilePickerTrigger = trigger;
    state.profileCreateInFlight = false;
    clearProfileError();
    ui.newProfileInput.value = '';
    ui.profileList.replaceChildren();
    ui.profilePicker.hidden = false;
    setProfilePickerBusy(true);
    try {
      const response = await fetch('/games/calculatorx/profiles');
      if (!response.ok) throw new Error('profiles unavailable');
      const payload = await response.json();
      if (!payload || !Array.isArray(payload.profiles) || !payload.profiles.every(isProfile)) {
        throw new Error('invalid profiles');
      }
      renderProfiles(payload.profiles, token);
      if (token !== state.profilePickerToken || ui.profilePicker.hidden) return;
      setProfilePickerBusy(false);
      ui.newProfileInput.focus();
    } catch (_error) {
      if (token !== state.profilePickerToken || ui.profilePicker.hidden) return;
      setProfilePickerBusy(false);
      showProfileError('Profils indisponibles.');
      ui.profileCancelButton.focus();
    }
  }

  async function submitPendingScore(profileId) {
    if (!state.pendingSubmissionSessionId || state.submissionInFlight || !profileId) return;
    const sessionId = state.pendingSubmissionSessionId;
    const mode = state.pendingSubmissionMode;
    const token = state.profilePickerToken;
    state.submissionInFlight = true;
    clearProfileError();
    setProfilePickerBusy(true);
    try {
      const response = await fetch('/games/calculatorx/leaderboard/submit', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({session_id: state.pendingSubmissionSessionId, profile_id: profileId}),
      });
      const payload = await response.json().catch(() => null);
      if (!response.ok || !payload || !isHistorySession(payload.session)
        || payload.session.id !== sessionId || payload.session.submission_status !== 'submitted') {
        throw new Error(typeof payload?.error === 'string' ? payload.error : 'submit unavailable');
      }
      if (token !== state.profilePickerToken || ui.profilePicker.hidden) return;
      if (state.lastResult?.response?.session?.id === sessionId) {
        state.lastResult.response.session = payload.session;
        renderResultSubmission(state.lastResult.response);
      }
      ++state.historyGeneration;
      closeProfilePicker({restoreFocus: false});
      if (!ui.scores.hidden) loadHistory();
      if (mode) loadLeaderboard(mode);
    } catch (error) {
      if (token === state.profilePickerToken && !ui.profilePicker.hidden) {
        showProfileError(error.message || 'Envoi impossible.');
      }
    } finally {
      if (token === state.profilePickerToken && !ui.profilePicker.hidden) {
        state.submissionInFlight = false;
        setProfilePickerBusy(false);
      }
    }
  }

  async function createAndSubmitProfile() {
    if (state.profileCreateInFlight || state.submissionInFlight) return;
    const nickname = ui.newProfileInput.value.trim();
    if (!nickname) {
      showProfileError('Pseudo requis.');
      ui.newProfileInput.focus();
      return;
    }
    const token = state.profilePickerToken;
    state.profileCreateInFlight = true;
    clearProfileError();
    setProfilePickerBusy(true);
    try {
      const response = await fetch('/games/calculatorx/profiles', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({nickname}),
      });
      const payload = await response.json().catch(() => null);
      if (!response.ok || !payload || !isProfile(payload.profile)) {
        throw new Error(typeof payload?.error === 'string' ? payload.error : 'profile unavailable');
      }
      if (token !== state.profilePickerToken || ui.profilePicker.hidden) return;
      state.profileCreateInFlight = false;
      state.submissionInFlight = false;
      setProfilePickerBusy(false);
      await submitPendingScore(payload.profile.id);
    } catch (error) {
      if (token === state.profilePickerToken && !ui.profilePicker.hidden) {
        state.profileCreateInFlight = false;
        setProfilePickerBusy(false);
        showProfileError(error.message || 'Création impossible.');
      }
    }
  }

  function renderLeaderboard(mode, scores) {
    const list = mode === 'classic' ? ui.classicLeaderboard : ui.constanceLeaderboard;
    list.replaceChildren();
    scores.slice(0, 100).forEach((score) => {
      const entry = document.createElement('li');
      const rank = document.createElement('span');
      const nickname = document.createElement('span');
      const value = document.createElement('strong');
      rank.textContent = String(score.rank);
      nickname.textContent = score.nickname;
      value.textContent = String(score.score);
      entry.append(rank, nickname, value);
      list.append(entry);
    });
  }

  async function loadLeaderboard(mode) {
    if (!['classic', 'constance'].includes(mode)) return;
    const token = ++state.leaderboardTokens[mode];
    const list = mode === 'classic' ? ui.classicLeaderboard : ui.constanceLeaderboard;
    clearLeaderboardError();
    list.setAttribute('aria-busy', 'true');
    try {
      const response = await fetch(`/games/calculatorx/leaderboards/${mode}`);
      const payload = await response.json().catch(() => null);
      if (!response.ok || !payload || !Array.isArray(payload.scores) || !payload.scores.every(isLeaderboardScore)) {
        throw new Error('leaderboard unavailable');
      }
      if (token !== state.leaderboardTokens[mode]) return;
      renderLeaderboard(mode, payload.scores);
    } catch (_error) {
      if (token === state.leaderboardTokens[mode]) showLeaderboardError('Classement indisponible.');
    } finally {
      if (token === state.leaderboardTokens[mode]) list.removeAttribute('aria-busy');
    }
  }

  function selectLeaderboard(mode) {
    if (!['classic', 'constance'].includes(mode)) return;
    state.leaderboardMode = mode;
    const isClassic = mode === 'classic';
    ui.classicLeaderboard.hidden = !isClassic;
    ui.constanceLeaderboard.hidden = isClassic;
    ui.classicLeaderboardTab.classList.toggle('is-active', isClassic);
    ui.constanceLeaderboardTab.classList.toggle('is-active', !isClassic);
    ui.classicLeaderboardTab.setAttribute('aria-selected', String(isClassic));
    ui.constanceLeaderboardTab.setAttribute('aria-selected', String(!isClassic));
    loadLeaderboard(mode);
  }

  function formatHistoryDate(playedAt) {
    const date = new Date(playedAt);
    if (Number.isNaN(date.valueOf())) return playedAt;
    return new Intl.DateTimeFormat('fr-CH', {
      dateStyle: 'short',
      timeStyle: 'short',
    }).format(date);
  }

  function formatResponseRate(rate) {
    return rate.toFixed(2).replace('.', ',');
  }

  function renderHistory(sessions) {
    ui.historyList.replaceChildren();
    const orderedSessions = sessions.slice().sort((left, right) => (
      right.score - left.score || right.played_at.localeCompare(left.played_at)
    ));
    if (orderedSessions.length === 0) {
      const empty = document.createElement('li');
      empty.className = 'history-empty';
      empty.textContent = 'Aucun score.';
      ui.historyList.append(empty);
      ui.clearHistoryButton.disabled = true;
      return;
    }

    orderedSessions.forEach((session) => {
      const entry = document.createElement('li');
      const score = document.createElement('strong');
      const details = document.createElement('span');
      const rate = document.createElement('span');
      const playedAt = document.createElement('time');
      const actions = document.createElement('div');
      score.className = 'history-score';
      score.textContent = String(session.score);
      details.className = 'history-details';
      details.textContent = `${MODE_LABELS[session.mode]} · ${session.duration_seconds}s`;
      rate.className = 'history-rate';
      rate.textContent = `${formatResponseRate(session.responses_per_second)} rép/s`;
      playedAt.className = 'history-date';
      playedAt.dateTime = session.played_at;
      playedAt.textContent = formatHistoryDate(session.played_at);
      actions.className = 'history-actions';

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
        actions.append(marks);
      }
      if (isPendingEligibleSession(session)) {
        const submit = document.createElement('button');
        submit.className = 'text-button history-submit';
        submit.type = 'button';
        submit.textContent = '+';
        submit.setAttribute('aria-label', 'Ajouter ce score au classement');
        submit.addEventListener('click', () => openProfilePicker(session, submit));
        actions.append(submit);
      }
      const remove = document.createElement('button');
      remove.className = 'text-button history-delete';
      remove.type = 'button';
      remove.textContent = '×';
      remove.setAttribute('aria-label', 'Supprimer cette partie');
      remove.addEventListener('click', () => deleteHistorySession(session, remove));
      actions.append(remove);
      entry.append(score, details, rate, playedAt, actions);
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
        || ui.mode.hidden
      ) return;
      renderHistory(payload.sessions);
    } catch (_error) {
      if (
        token === state.historyToken
        && generation === state.historyGeneration
        && !ui.mode.hidden
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
      if (!ui.mode.hidden) loadHistory();
    } catch (_error) {
      if (token === state.historyToken && !ui.mode.hidden) {
        showHistoryError('Effacement impossible.');
        ui.clearHistoryButton.disabled = false;
      }
    } finally {
      if (token === state.historyToken) ui.historyList.removeAttribute('aria-busy');
    }
  }

  async function deleteHistorySession(session, button) {
    if (!window.confirm('Supprimer cette partie de l’historique local ?')) return;
    const token = ++state.historyToken;
    clearHistoryError();
    button.disabled = true;
    ui.historyList.setAttribute('aria-busy', 'true');
    try {
      const response = await fetch(`/games/calculatorx/history/${session.id}`, {
        method: 'DELETE',
      });
      if (!response.ok) throw new Error('history unavailable');
      ++state.historyGeneration;
      if (!ui.mode.hidden) loadHistory();
    } catch (_error) {
      if (token === state.historyToken && !ui.mode.hidden) {
        showHistoryError('Suppression impossible.');
        button.disabled = false;
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

  function setLiveChartVisible(visible) {
    ui.responseFigure.hidden = !visible;
    ui.chartToggleButton.textContent = visible ? 'Courbe ↑' : 'Courbe ↓';
    ui.chartToggleButton.setAttribute('aria-expanded', String(visible));
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
        details.textContent = `${summary.count} · ${formatMilliseconds(summary.mean_ms)} (${formatMilliseconds(summary.standard_deviation_ms)})`;
        details.setAttribute('aria-label', `${summary.count} réponses, moyenne ${formatMilliseconds(summary.mean_ms)}, écart-type ${formatMilliseconds(summary.standard_deviation_ms)}`);
      } else {
        const emptySummary = {count: 0};
        details.textContent = `${emptySummary.count} · — (—)`;
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
      elapsed_ms: reason === 'timeout'
        ? state.durationSeconds * 1000
        : Math.min(
          state.durationSeconds * 1000,
          Math.max(1, Math.round(performance.now() - state.roundStartedAt)),
        ),
      score: state.score,
      ended_reason: reason,
      samples: state.samples.map((sample) => ({...sample})),
    };
    state.lastResult = {request: resultPayload, response: null};
    renderResultSubmission(null);

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
      renderResultSubmission(payload);
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
    ui.activeMode.textContent = MODE_LABELS[payload.mode];
    state.roundStartedAt = now;
    state.deadline = now + payload.duration_seconds * 1000;
    state.endedReason = null;
    state.lastResult = null;
    renderResultSubmission(null);
    state.playing = true;
    state.finishing = false;
    ui.score.textContent = '0';
    ui.timer.textContent = String(payload.duration_seconds);
    ui.projectedScore.hidden = true;
    ui.input.disabled = false;
    setLiveChartVisible(true);
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
    showPanel(ui.ready);
    showError(message);
    ui.startButton.focus();
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
      .catch((error) => {
        const sessionError = error instanceof SessionError
          ? error
          : new SessionError('Impossible de préparer la partie.');
        showPreparationError(token, sessionError.message, sessionError.field);
      });
  }

  function selectMode(mode) {
    state.mode = mode;
    state.config = {mode};
    showReadyPanel();
  }

  function showReadyPanel() {
    clearError();
    ui.readyModeValue.textContent = MODE_LABELS[state.mode];
    ui.readyDurationValue.textContent = `${state.config.duration_seconds || 120} s`;
    showPanel(ui.ready);
    ui.startButton.focus();
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
  ui.classicLeaderboardTab.addEventListener('click', () => selectLeaderboard('classic'));
  ui.constanceLeaderboardTab.addEventListener('click', () => selectLeaderboard('constance'));
  ui.submitScoreButton.addEventListener('click', () => {
    const session = state.lastResult?.response?.session;
    if (state.lastResult?.response?.leaderboard_eligible === true) {
      openProfilePicker(session, ui.submitScoreButton);
    }
  });
  ui.profileCancelButton.addEventListener('click', () => closeProfilePicker());
  ui.profileForm.addEventListener('submit', (event) => {
    event.preventDefault();
    createAndSubmitProfile();
  });
  ui.resetClassicButton.addEventListener('click', () => applyConfigToForm(classicCustomConfig()));
  ui.customForm.addEventListener('submit', (event) => {
    event.preventDefault();
    clearSettingsError();
    try {
      const config = configFromForm();
      state.mode = 'custom';
      state.config = config;
      showReadyPanel();
    } catch (error) {
      if (error instanceof SettingsError) showSettingsError(error.message, error.field);
      else showSettingsError('Réglages invalides.', null);
    }
  });
  ui.startButton.addEventListener('click', prepareRound);
  ui.themeToggle.addEventListener('click', () => {
    const theme = document.documentElement.dataset.theme === 'light' ? 'dark' : 'light';
    applyTheme(theme);
    writeStoredJson(STORAGE_KEYS.theme, theme);
  });
  ui.retry.addEventListener('click', prepareRound);
  ui.stopButton.addEventListener('click', () => finishRound(state.roundToken, 'stopped'));
  ui.chartToggleButton.addEventListener('click', () => {
    setLiveChartVisible(ui.responseFigure.hidden);
  });
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

  function handleProfilePickerKeydown(event) {
    if (ui.profilePicker.hidden) return false;
    if (event.key === 'Escape') {
      event.preventDefault();
      closeProfilePicker();
      return true;
    }
    if (event.key !== 'Tab') return true;
    const focusable = profilePickerFocusable();
    if (focusable.length === 0) return true;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
    return true;
  }

  document.addEventListener('keydown', (event) => {
    if (handleProfilePickerKeydown(event)) return;
    if (event.key !== 'Enter' || state.playing || state.preparing || state.finishing) return;
    if (event.target.closest('a, button, input, select, textarea, [role="button"]')) return;
    if (ui.ready.hidden && ui.result.hidden) return;
    event.preventDefault();
    prepareRound();
  });

  loadPreferences();
  showPanel(ui.mode);
  loadHistory();
})();
