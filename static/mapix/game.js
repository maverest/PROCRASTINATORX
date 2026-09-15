(() => {
  'use strict';

  const ui = Object.fromEntries([
    'setupPanel', 'gamePanel', 'resultPanel', 'fatalPanel', 'modeChoices',
    'regionChoices', 'playButton', 'quitButton', 'retryButton', 'menuButton',
    'fatalRetryButton', 'fatalMenuButton', 'backLink', 'mapContainer', 'flagPanel',
    'flagGrid', 'countryPrompt', 'progressValue', 'timerValue', 'nameForm',
    'nameInput', 'nameSubmit', 'regionLabel', 'resultTime', 'resultPerfectStat',
    'resultPerfect', 'resultErrors', 'resultAccuracy', 'gameFeedback',
  ].map(id => [id, document.getElementById(id)]));

  const state = {
    mode: 'territory',
    region: 'world',
    session: null,
    activeRequest: false,
    timerOrigin: null,
    timerFrame: null,
    map: null,
    countries: null,
  };
  let catalogPromise = null;

  function loadCatalog() {
    if (!catalogPromise) {
      catalogPromise = fetch('/static/mapix/countries.json').then(async response => {
        if (!response.ok) throw new Error('catalog');
        const countries = await response.json();
        if (!Array.isArray(countries)) throw new Error('catalog');
        state.countries = new Map(countries.map(country => [country.id, country]));
        return state.countries;
      }).catch(error => {
        catalogPromise = null;
        throw error;
      });
    }
    return catalogPromise;
  }

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
    syncGameControls();
    if (!busy && state.session?.mode === 'all' && !state.session.finished && !ui.gamePanel.hidden) {
      ui.nameInput.focus();
    }
  }

  function syncGameControls() {
    const canAnswer = Boolean(state.session && !state.session.finished && !state.activeRequest);
    const canName = canAnswer && state.session.mode === 'all';
    ui.nameInput.disabled = !canName;
    ui.nameSubmit.disabled = !canName;
    for (const button of ui.flagGrid.querySelectorAll('.flag-choice')) {
      button.disabled = !canAnswer || button.dataset.locked === 'true';
    }
  }

  function currentCountryId() {
    if (!state.session.current) return null;
    for (const [id, country] of state.countries) {
      if (country.name === state.session.current.name) return id;
    }
    return null;
  }

  function renderFlags() {
    ui.flagGrid.replaceChildren();
    if (!['flag-territory', 'flag-only'].includes(state.session.mode)) return;
    const lockedId = state.session.flag_done ? currentCountryId() : null;
    for (const id of state.session.remaining_flags) {
      const country = state.countries.get(id);
      if (!country) continue;
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'flag-choice';
      button.dataset.country = id;
      button.dataset.locked = String(id === lockedId);
      button.append(window.MapixFlags.createImage(country));
      button.setAttribute('aria-label', `Choisir le drapeau ${country.name}`);
      if (id === lockedId) {
        button.classList.add('is-selected');
        button.setAttribute('aria-pressed', 'true');
      }
      button.addEventListener('click', () => submitAnswer('flag', id));
      ui.flagGrid.append(button);
    }
    syncGameControls();
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
    renderFlags();
    state.map?.setFound(session.found);
    if (session.territory_done) state.map?.markCorrect(currentCountryId());
    syncGameControls();
  }

  function renderResult(result) {
    // La durée définitive est celle du serveur, pas l'estimation du chrono local.
    ui.resultTime.textContent = formatDuration(result.elapsed_seconds);
    ui.resultErrors.textContent = String(result.errors);
    ui.resultAccuracy.textContent = `${new Intl.NumberFormat('fr', {maximumFractionDigits: 1}).format(result.accuracy_percent)} %`;
    ui.resultPerfectStat.hidden = state.session.mode === 'all';
    if (state.session.mode !== 'all') {
      ui.resultPerfect.textContent = `${result.perfect_countries} / ${state.session.total}`;
    }
    showPanel(ui.resultPanel);
  }

  async function startGame() {
    if (state.activeRequest) return;
    setBusy(true);
    stopTimer();
    try {
      await loadCatalog();
      const response = await fetch('/games/mapix/session', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({mode: state.mode, region: state.region}),
      });
      if (!response.ok) throw new Error('start');
      state.session = await response.json();
      ui.flagPanel.scrollTop = 0;
      ui.gameFeedback.textContent = '';
      if (state.session.mode !== 'flag-only') {
        if (!state.map) {
          state.map = window.MapixMap.create(ui.mapContainer, {
            onCountry: id => {
              if (['territory', 'flag-territory'].includes(state.session?.mode)) {
                submitAnswer('territory', id);
              }
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
        if (state.session.mode === 'all') ui.nameInput.focus();
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

  function flashElement(element) {
    if (!element) return;
    element.classList.remove('is-wrong');
    // Relancer l'animation lorsque deux erreurs se suivent rapidement.
    void element.offsetWidth;
    element.classList.add('is-wrong');
    window.setTimeout(() => element.classList.remove('is-wrong'), 300);
  }

  function renderAnswer(payload, action) {
    const outcome = payload.outcome;
    state.session = payload;
    renderSession();
    if (outcome.duplicate) {
      ui.gameFeedback.textContent = '';
    } else if (outcome.correct) {
      if (action === 'territory' && !outcome.advanced) {
        state.map?.markCorrect(outcome.selected_country_id);
      }
      ui.gameFeedback.textContent = 'Bien trouvé !';
    } else {
      if (action === 'territory') state.map?.flashWrong(outcome.selected_country_id);
      if (action === 'flag') {
        flashElement(ui.flagGrid.querySelector(`[data-country="${outcome.selected_country_id}"]`));
      }
      if (action === 'name') flashElement(ui.nameInput);
      ui.gameFeedback.textContent = action === 'name' ? 'Pays inconnu.' : 'Essayez encore.';
    }
    if (action === 'name') {
      ui.nameInput.value = '';
      if (!payload.finished) ui.nameInput.focus();
    }
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
      renderAnswer(payload, action);
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
    ui.flagGrid.replaceChildren();
    ui.nameInput.value = '';
    syncGameControls();
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
  ui.nameForm.addEventListener('submit', event => {
    event.preventDefault();
    const value = ui.nameInput.value.trim();
    if (value) submitAnswer('name', value);
    else ui.nameInput.focus();
  });
  window.addEventListener('pagehide', stopTimer);
})();
