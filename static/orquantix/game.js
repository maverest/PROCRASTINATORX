let guesses = [];
let guessCounter = 0;
let pendingSuggestion = null;
let timerRunning = false;
let timerStartedAt = null;
let timerCompletedMs = null;
let timerInterval = null;

function showSuggestion(word) {
  pendingSuggestion = word;
  document.getElementById('suggestionWord').textContent = word;
  document.getElementById('suggestionBox').style.display = 'flex';
}

function dismissSuggestion() {
  pendingSuggestion = null;
  document.getElementById('suggestionBox').style.display = 'none';
}

function acceptSuggestion() {
  const word = pendingSuggestion;
  dismissSuggestion();
  submitWord(word);
}

function esc(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function formatDuration(ms) {
  const totalSeconds = Math.max(0, Math.round(ms / 1000));
  const m = Math.floor(totalSeconds / 60);
  const s = String(totalSeconds % 60).padStart(2, '0');
  return m + ':' + s;
}

function updateTimerDisplay() {
  const el = document.getElementById('timerDisplay');
  if (timerRunning && timerStartedAt !== null) {
    el.textContent = 'Timer : ' + formatDuration(Date.now() - timerStartedAt);
    return;
  }
  if (timerCompletedMs !== null) {
    el.textContent = 'Timer : ' + formatDuration(timerCompletedMs);
    return;
  }
  el.textContent = 'Timer : --:--';
}

function updateTimerButton() {
  const button = document.getElementById('timerBtn');
  if (timerRunning) {
    button.textContent = 'Timer…';
    button.disabled = true;
    return;
  }
  if (timerCompletedMs !== null) {
    button.textContent = 'Timer ✓';
    button.disabled = true;
    return;
  }
  button.textContent = 'Timer';
  button.disabled = false;
}

function updateGiveUpButton() {
  const button = document.getElementById('giveUpBtn');
  const alreadyResolved = guesses.some(g => g.win);
  button.disabled = alreadyResolved;
}

function updateReplayButton(visible) {
  document.getElementById('orcaReplayBtn').style.display = visible ? 'inline-flex' : 'none';
}

function startTimerMode() {
  if (timerRunning || timerCompletedMs !== null) return;
  timerRunning = true;
  timerStartedAt = Date.now();
  clearInterval(timerInterval);
  timerInterval = setInterval(updateTimerDisplay, 250);
  updateTimerDisplay();
  updateTimerButton();
  speakOrca('timer-start', currentOrcaMood);
}

function stopTimer() {
  if (!timerRunning || timerStartedAt === null) return;
  timerCompletedMs = Date.now() - timerStartedAt;
  timerRunning = false;
  clearInterval(timerInterval);
  timerInterval = null;
  updateTimerDisplay();
  updateTimerButton();
}

function resetTimer() {
  timerRunning = false;
  timerStartedAt = null;
  timerCompletedMs = null;
  clearInterval(timerInterval);
  timerInterval = null;
  updateTimerDisplay();
  updateTimerButton();
}

function toggleHintPanel() {
  const panel = document.getElementById('hintPanel');
  panel.style.display = panel.style.display === 'flex' ? 'none' : 'flex';
}

function requestHint(type) {
  fetch('/games/orquantix/hint', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({type})
  })
    .then(r => r.json())
    .then(data => {
      if (data.error) {
        showError(data.error);
        return;
      }
      if (data.value && (type === 'better-word' || type === 'golden-fish')) {
        document.getElementById('guessInput').placeholder = 'Indice : ' + data.value;
      }
      speakOrca(type, currentOrcaMood);
      if (orcaMode !== 'mute') {
        document.getElementById('orcaBubble').textContent = data.message;
      }
    })
    .catch(() => showError('Erreur réseau.'));
}

function renderDifficulty(d) {
  document.getElementById('dailyDifficulty').textContent =
    'Difficulté : ' + '⭐'.repeat(d) + '☆'.repeat(5 - d);
}

function showError(msg) {
  const el = document.getElementById('errorMessage');
  el.textContent = msg;
  el.style.display = 'block';
}

function hideError() {
  document.getElementById('errorMessage').style.display = 'none';
}

// ─── Polling ─────────────────────────────────────────────────────────────
function pollStatus() {
  fetch('/games/orquantix/status')
    .then(r => r.json())
    .then(data => {
      document.getElementById('progressBar').style.width = data.progress + '%';
      document.getElementById('downloadDetail').textContent = data.detail || '';
      if (data.phase === 'ready') {
        activateGame();
      } else if (data.phase === 'error') {
        document.getElementById('downloadError').textContent = data.detail || 'Erreur inconnue.';
        document.getElementById('downloadError').style.display = 'block';
      } else {
        setTimeout(pollStatus, 500);
      }
    })
    .catch(() => setTimeout(pollStatus, 1000));
}

function activateGame() {
  // /session peut encore répondre 503 juste après que /status soit passé
  // à "ready" (deux routes distinctes). Tant que ce n'est pas le cas, on
  // retente sans jamais basculer sur l'écran de jeu avec un plateau vide.
  fetch('/games/orquantix/session')
    .then(r => {
      if (!r.ok) throw new Error('session not ready');
      return r.json();
    })
    .then(data => {
      document.getElementById('downloadScreen').style.display = 'none';
      document.getElementById('gameScreen').style.display = 'block';
      guessCounter = 0;

      renderDifficulty(data.difficulty);
      guesses = data.guesses.map((g, i) => ({...g, attempt: i + 1, progressAnimated: true}));
      guessCounter = guesses.length;
      guesses.sort((a, b) => b.progress - a.progress);
      renderTable();

      document.getElementById('guessInput').focus();
      document.body.classList.toggle('dyslexic-mode', dyslexicMode);
      document.getElementById('dyslexicToggle').textContent =
        'Dys. ' + (dyslexicMode ? 'ON' : 'OFF');
      document.getElementById('dyslexicToggle').classList.toggle('active', dyslexicMode);
      resetTimer();
      updateGiveUpButton();
      applyOrcaTool(orcaMode, 'Ola que tal');

      if (data.resolved) showVictory();
    })
    .catch(() => setTimeout(activateGame, 500));
}

function submitGuess(event) {
  event.preventDefault();
  const input = document.getElementById('guessInput');
  const word  = input.value.trim();
  if (!word) return;
  input.value = '';
  hideError();
  dismissSuggestion();
  submitWord(word);
}

function submitWord(word) {
  triggerEasterEgg(word);
  fetch('/games/orquantix/guess', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({word})
  })
    .then(r => r.json())
    .then(data => {
      if (data.error) {
        if (data.error === 'inconnu') {
          speakOrca('unknown', 'sick');
        }
        if (data.error === 'inconnu' && dyslexicMode) {
          fetchSuggestion(word);
        } else {
          const msg = data.error === 'inconnu'
            ? '"' + esc(word) + '" n\'est pas dans le vocabulaire.'
            : data.error;
          showError(msg);
        }
        return;
      }
      guesses.push({
        ...data,
        attempt: ++guessCounter,
        progressAnimated: false,
      });
      guesses.sort((a, b) => b.progress - a.progress);
      speakOrca(data.mood, data.mood);
      updateGiveUpButton();
      renderTable().then(() => {
        if (data.win) showVictory();
      });
    })
    .catch(() => showError('Erreur réseau.'));
}

function giveUp() {
  fetch('/games/orquantix/give-up', {method: 'POST'})
    .then(r => r.json())
    .then(data => {
      if (data.error) {
        showError(data.error);
        return;
      }
      guesses.push({
        ...data,
        attempt: ++guessCounter,
        progressAnimated: false,
      });
      guesses.sort((a, b) => b.progress - a.progress);
      updateGiveUpButton();
      if (orcaMode !== 'mute') {
        document.getElementById('orcaBubble').textContent = 'Bah alors, on abandonne ??';
      }
      renderTable().then(() => {
        showVictory();
      });
    })
    .catch(() => showError('Erreur réseau.'));
}

function fetchSuggestion(word) {
  fetch('/games/orquantix/suggest', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({word})
  })
    .then(r => r.json())
    .then(data => {
      if (data.suggestion) {
        showSuggestion(data.suggestion);
      } else {
        showError('"' + esc(word) + '" n\'est pas dans le vocabulaire.');
      }
    })
    .catch(() => showError('Erreur réseau.'));
}

// La courbe est très plate en bas : au rang 800 elle vaut 0,43 %. Arrondir
// à l'entier écraserait toute cette zone à « 0 % » et rendrait deux voisins
// éloignés indistinguables, ce que l'affichage doit justement éviter.
function formatProgress(value) {
  const v = Math.max(0, Math.min(100, Number(value) || 0));
  if (v >= 10) return String(Math.round(v));
  if (v >= 1) return v.toFixed(1);
  return v.toFixed(2);
}

function animateProgress(row, guess) {
  const valueEl = row.querySelector('.progress-value');
  const fillEl = row.querySelector('.progress-bar-fill');
  const target = Math.max(0, Math.min(100, Number(guess.progress) || 0));

  guess.progressAnimated = true;

  if (!valueEl || !fillEl || target <= 0) {
    if (valueEl) valueEl.textContent = formatProgress(target) + '%';
    if (fillEl) fillEl.style.width = target + '%';
    return Promise.resolve();
  }

  fillEl.classList.add('is-animating');

  return new Promise(resolve => {
    const duration = Math.min(2200, 520 + target * 12);
    const start = performance.now();

    function step(now) {
      const ratio = Math.min((now - start) / duration, 1);
      const current = target * ratio;
      fillEl.style.width = current + '%';
      valueEl.textContent = formatProgress(current) + '%';

      if (ratio < 1) { requestAnimationFrame(step); return; }

      fillEl.classList.remove('is-animating');
      fillEl.style.width = target + '%';
      valueEl.textContent = formatProgress(target) + '%';
      resolve();
    }

    requestAnimationFrame(step);
  });
}

function renderTable() {
  const tbody = document.getElementById('guessTableBody');
  const animations = [];
  tbody.innerHTML = '';

  for (const g of guesses) {
    const tr = document.createElement('tr');
    const shouldAnimate = g.progressAnimated !== true;
    const shown = shouldAnimate ? 0 : g.progress;

    tr.className = 'guess-row orca-' + g.mood;
    tr.innerHTML =
      '<td class="guess-number">' + g.attempt + '</td>' +
      '<td class="guess-word">' + esc(g.word) + '</td>' +
      '<td class="guess-progress">' +
        '<div class="progress-row">' +
          '<span class="progress-value">' + Math.round(shown) + '°</span>' +
          '<div class="progress-bar">' +
            '<div class="progress-bar-fill" style="width:' + shown + '%"></div>' +
          '</div>' +
        '</div>' +
      '</td>' +
      '<td class="guess-rank">' +
        (g.rank ? '<span class="rank-badge">#' + g.rank + '</span>' : '<span class="rank-none">—</span>') +
      '</td>' +
      '<td class="guess-orca">' +
        '<img class="orca-emoji" src="' + esc(PROXIMITY_ICONS[g.mood] || PROXIMITY_ICONS.sick) +
        '" alt="' + esc(g.label) + '" title="' + esc(g.label) + '">' +
      '</td>';

    tbody.appendChild(tr);
    if (shouldAnimate) animations.push(animateProgress(tr, g));
  }

  return Promise.all(animations);
}

function showVictory() {
  if (timerRunning) {
    stopTimer();
  }
  document.getElementById('guessForm').style.display    = 'none';
  updateReplayButton(true);
  speakOrca('found', 'found');
}

function newGame() {
  fetch('/games/orquantix/new-game', {method: 'POST'})
    .then(r => r.json())
    .then(data => {
      guesses = [];
      guessCounter = 0;
      resetTimer();
      renderDifficulty(data.difficulty);
      renderTable();
      document.getElementById('guessForm').style.display    = 'flex';
      document.getElementById('hintPanel').style.display = 'none';
      document.getElementById('guessInput').placeholder = 'Proposez un mot…';
      hideError();
      updateGiveUpButton();
      updateReplayButton(false);
      document.getElementById('guessInput').focus();
      setOrcaState('neutral', 'Ola que tal');
    })
    .catch(() => showError('Erreur réseau.'));
}

pollStatus();
