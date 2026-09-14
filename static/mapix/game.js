(() => {
  'use strict';

  const ui = Object.fromEntries([
    'setupPanel', 'gamePanel', 'resultPanel', 'fatalPanel', 'modeChoices',
    'regionChoices', 'playButton', 'quitButton', 'retryButton', 'menuButton',
    'fatalRetryButton', 'fatalMenuButton', 'backLink', 'mapContainer', 'flagPanel',
    'flagGrid', 'countryPrompt', 'progressValue', 'timerValue', 'nameForm',
    'nameInput', 'regionLabel', 'resultTime', 'resultPerfect', 'resultErrors',
    'resultAccuracy', 'gameFeedback',
  ].map(id => [id, document.getElementById(id)]));

  const state = {
    mode: 'territory',
    region: 'world',
    session: null,
    activeRequest: false,
    timerOrigin: null,
    timerFrame: null,
    map: null,
  };

  function stopTimer() {
    if (state.timerFrame !== null) cancelAnimationFrame(state.timerFrame);
    state.timerFrame = null;
    state.timerOrigin = null;
  }

  function showPanel(panel) {
    if (panel !== ui.gamePanel) stopTimer();
    for (const candidate of [ui.setupPanel, ui.gamePanel, ui.resultPanel, ui.fatalPanel]) {
      candidate.hidden = candidate !== panel;
    }
    const title = panel.querySelector('h2');
    (title && !title.hidden ? title : panel).focus();
  }

  function formatDuration(seconds) {
    const total = Math.max(0, Math.floor(seconds));
    const minutes = Math.floor(total / 60);
    return `${String(minutes).padStart(2, '0')}:${String(total % 60).padStart(2, '0')}`;
  }

  function startTimer() {
    stopTimer();
    state.timerOrigin = performance.now() - state.session.elapsed_seconds * 1000;
    const tick = () => {
      ui.timerValue.textContent = formatDuration((performance.now() - state.timerOrigin) / 1000);
      state.timerFrame = requestAnimationFrame(tick);
    };
    tick();
  }

  function setBusy(busy) {
    state.activeRequest = busy;
    for (const button of [ui.playButton, ui.quitButton, ui.retryButton, ui.fatalRetryButton, ui.menuButton, ui.fatalMenuButton]) {
      button.disabled = busy;
    }
    for (const button of document.querySelectorAll('[data-mode], [data-region]')) button.disabled = busy;
    ui.playButton.setAttribute('aria-busy', String(busy));
  }

  function renderSession() {
    const session = state.session;
    ui.gamePanel.dataset.mode = session.mode;
    ui.mapContainer.hidden = session.mode === 'flag-only';
    ui.flagPanel.hidden = !['flag-territory', 'flag-only'].includes(session.mode);
    ui.nameForm.hidden = session.mode !== 'all';
    ui.countryPrompt.hidden = session.mode === 'all';
    ui.countryPrompt.textContent = session.current?.name || '';
    ui.progressValue.textContent = `${session.found.length} / ${session.total}`;
    ui.regionLabel.textContent = [...ui.regionChoices.querySelectorAll('button')]
      .find(button => button.dataset.region === session.region).textContent;
  }

  function renderResult(result) {
    // La durée définitive est celle du serveur, pas l'estimation du chrono local.
    ui.resultTime.textContent = formatDuration(result.elapsed_seconds);
    ui.resultErrors.textContent = String(result.errors);
    ui.resultAccuracy.textContent = `${new Intl.NumberFormat('fr', {maximumFractionDigits: 1}).format(result.accuracy_percent)} %`;
    ui.resultPerfect.closest('.result-stat').hidden = state.session.mode === 'all';
    ui.resultPerfect.textContent = `${result.perfect_countries} / ${state.session.total}`;
    showPanel(ui.resultPanel);
  }

  async function startGame() {
    if (state.activeRequest) return;
    setBusy(true);
    stopTimer();
    try {
      const response = await fetch('/games/mapix/session', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({mode: state.mode, region: state.region}),
      });
      if (!response.ok) throw new Error('start');
      state.session = await response.json();
      ui.gameFeedback.textContent = '';
      if (state.session.mode !== 'flag-only') {
        if (!state.map) {
          state.map = window.MapixMap.create(ui.mapContainer, {
            onCountry: id => {
              if (state.session?.mode === 'territory') submitAnswer('territory', id);
            },
          });
        }
        await state.map.ready;
        state.map.setRegion(state.session.region);
        state.map.setFound(state.session.found);
      }
      renderSession();
      if (state.session.finished) {
        renderResult(state.session.result);
      } else {
        showPanel(ui.gamePanel);
        startTimer();
      }
    } catch {
      state.map?.destroy();
      state.map = null;
      showPanel(ui.fatalPanel);
    } finally {
      setBusy(false);
    }
  }

  function handleAnswerError(status, payload) {
    if (status === 404 || status === 409 || status >= 500) {
      showPanel(ui.fatalPanel);
    } else {
      ui.gameFeedback.textContent = payload.error || 'Cette réponse est impossible.';
    }
  }

  function renderAnswer(payload) {
    const outcome = payload.outcome;
    if (outcome.correct) {
      state.map.markCorrect(outcome.selected_country_id);
      ui.gameFeedback.textContent = 'Bien trouvé !';
    } else {
      state.map.flashWrong(outcome.selected_country_id);
      ui.gameFeedback.textContent = 'Essayez un autre territoire.';
    }
    state.session = payload;
    if (outcome.advanced) state.map.setFound(payload.found);
    renderSession();
    if (payload.finished) renderResult(payload.result);
  }

  async function submitAnswer(action, value) {
    if (state.activeRequest || !state.session || state.session.finished || ui.gamePanel.hidden) return;
    setBusy(true);
    try {
      const response = await fetch('/games/mapix/answer', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          token: state.session.token,
          question_index: state.session.question_index,
          action,
          value,
        }),
      });
      const payload = await response.json();
      if (!response.ok) return handleAnswerError(response.status, payload);
      renderAnswer(payload);
    } catch {
      // La réponse a peut-être été enregistrée : ne pas renvoyer aveuglément
      // une proposition avec un index de question devenu périmé.
      showPanel(ui.fatalPanel);
    } finally {
      setBusy(false);
    }
  }

  function showSetup() {
    state.session = null;
    showPanel(ui.setupPanel);
  }

  async function quitGame(destination = null) {
    if (state.activeRequest || !window.confirm('Quitter cette partie ?')) return;
    setBusy(true);
    try {
      const response = await fetch('/games/mapix/quit', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({token: state.session.token}),
      });
      if (!response.ok && response.status !== 404 && response.status !== 409) throw new Error('quit');
      showSetup();
      if (destination) window.location.assign(destination);
    } catch {
      showPanel(ui.fatalPanel);
    } finally {
      setBusy(false);
    }
  }

  for (const [group, key] of [[ui.modeChoices, 'mode'], [ui.regionChoices, 'region']]) {
    group.addEventListener('click', event => {
      const button = event.target.closest('button');
      if (!button || !group.contains(button) || state.activeRequest) return;
      state[key] = button.dataset[key];
      for (const choice of group.querySelectorAll('button')) {
        choice.setAttribute('aria-pressed', String(choice === button));
      }
    });
  }

  ui.playButton.addEventListener('click', startGame);
  ui.retryButton.addEventListener('click', startGame);
  ui.fatalRetryButton.addEventListener('click', startGame);
  ui.menuButton.addEventListener('click', showSetup);
  ui.fatalMenuButton.addEventListener('click', showSetup);
  ui.quitButton.addEventListener('click', () => quitGame());
  ui.backLink.addEventListener('click', event => {
    if (state.activeRequest) {
      event.preventDefault();
    } else if (state.session && !state.session.finished) {
      event.preventDefault();
      quitGame('/');
    }
  });
  // Le formulaire du mode Tous sera câblé avec les autres modes.
  ui.nameForm.addEventListener('submit', event => event.preventDefault());
  window.addEventListener('pagehide', stopTimer);
})();
