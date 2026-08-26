(() => {
  'use strict';

  const ui = {
    welcome: document.getElementById('welcomePanel'),
    game: document.getElementById('gamePanel'),
    result: document.getElementById('resultPanel'),
    start: document.getElementById('startButton'),
    retry: document.getElementById('retryButton'),
    input: document.getElementById('answerInput'),
    problem: document.getElementById('problemText'),
    timer: document.getElementById('timerValue'),
    score: document.getElementById('scoreValue'),
    finalScore: document.getElementById('finalScore'),
    error: document.getElementById('errorMessage'),
  };

  const state = {
    roundToken: 0,
    preparing: false,
    problems: [],
    problemIndex: 0,
    score: 0,
    deadline: 0,
    frameId: 0,
    playing: false,
  };

  function showPanel(panel) {
    ui.welcome.hidden = panel !== ui.welcome;
    ui.game.hidden = panel !== ui.game;
    ui.result.hidden = panel !== ui.result;
  }

  function setPreparing(preparing) {
    state.preparing = preparing;
    ui.start.disabled = preparing;
    ui.retry.disabled = preparing;
    ui.start.textContent = preparing ? 'Préparation…' : 'C’est parti !';
    ui.retry.textContent = preparing ? 'Préparation…' : 'Rejouer';
  }

  function isProblem(problem) {
    return Number.isInteger(problem.left)
      && ['+', '−', '×', '÷'].includes(problem.operator)
      && Number.isInteger(problem.right)
      && Number.isInteger(problem.answer);
  }

  function isSession(payload) {
    return payload
      && payload.duration_seconds === 120
      && Array.isArray(payload.problems)
      && payload.problems.length > 0
      && payload.problems.every(isProblem);
  }

  function renderProblem() {
    const problem = state.problems[state.problemIndex];
    ui.problem.textContent = `${problem.left} ${problem.operator} ${problem.right} =`;
    ui.input.value = '';
    ui.input.focus();
  }

  function finishRound(token) {
    if (token !== state.roundToken || !state.playing) return;
    state.playing = false;
    cancelAnimationFrame(state.frameId);
    ui.input.disabled = true;
    ui.timer.textContent = '0';
    ui.finalScore.textContent = String(state.score);
    showPanel(ui.result);
    ui.retry.focus();
  }

  function updateClock(token) {
    if (token !== state.roundToken || !state.playing) return;
    const remaining = Math.max(0, state.deadline - performance.now());
    ui.timer.textContent = String(Math.ceil(remaining / 1000));
    if (remaining <= 0) {
      finishRound(token);
      return;
    }
    state.frameId = requestAnimationFrame(() => updateClock(token));
  }

  function beginRound(payload, token) {
    if (token !== state.roundToken) return;
    state.problems = payload.problems;
    state.problemIndex = 0;
    state.score = 0;
    state.deadline = performance.now() + payload.duration_seconds * 1000;
    state.playing = true;
    ui.score.textContent = '0';
    ui.timer.textContent = String(payload.duration_seconds);
    ui.input.disabled = false;
    setPreparing(false);
    showPanel(ui.game);
    renderProblem();
    updateClock(token);
  }

  function showPreparationError(token) {
    if (token !== state.roundToken) return;
    setPreparing(false);
    showPanel(ui.welcome);
    ui.error.textContent = 'Impossible de préparer la partie. Réessaie.';
    ui.error.hidden = false;
    ui.start.focus();
  }

  function prepareRound() {
    if (state.preparing) return;
    const token = ++state.roundToken;
    state.playing = false;
    cancelAnimationFrame(state.frameId);
    ui.error.hidden = true;
    setPreparing(true);
    fetch('/games/calculatorx/session', {method: 'POST'})
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

  function handleAnswer() {
    if (!state.playing) return;
    const token = state.roundToken;
    if (performance.now() >= state.deadline) {
      finishRound(token);
      return;
    }
    if (!/^\d+$/.test(ui.input.value)) return;
    const current = state.problems[state.problemIndex];
    if (Number(ui.input.value) !== current.answer) return;
    state.score += 1;
    state.problemIndex += 1;
    ui.score.textContent = String(state.score);
    if (state.problemIndex >= state.problems.length) {
      finishRound(token);
      return;
    }
    renderProblem();
  }

  ui.start.addEventListener('click', prepareRound);
  ui.retry.addEventListener('click', prepareRound);
  ui.input.addEventListener('input', handleAnswer);
  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Enter' || state.playing || state.preparing) return;
    if (ui.welcome.hidden && ui.result.hidden) return;
    event.preventDefault();
    prepareRound();
  });
})();
