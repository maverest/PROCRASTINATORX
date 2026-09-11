const ORCA_TOOLS = {
  neutral: {
    kind: 'mode',
    mode: 'neutral',
    badge: '💧',
    bubble: 'retour à la chill'
  },
  mute: {
    kind: 'mode',
    mode: 'mute',
    badge: '🩹',
    bubble: '...'
  },
  trashtalk: {
    kind: 'mode',
    mode: 'trashtalk',
    badge: '🧃',
    bubble: 'ehehehehehehe'
  },
  'golden-fish': {
    kind: 'hint',
    hintType: 'golden-fish',
    badge: '🐟',
    bubble: 'Le poisson doré remonte un voisin très fort.'
  }
};
const ORCA_MASCOTS = {
  default: {
    neutral: '/static/orca_assets/orque_base.png',
    mute: '/static/orca_assets/orque_scotche.png',
    trashtalk: '/static/orca_assets/orque_trash_talk.png'
  },
  dyslexic: {
    neutral: '/static/orca_assets/orque_base_dislex.png',
    mute: '/static/orca_assets/orque_scotche_dislex.png',
    trashtalk: '/static/orca_assets/orque_trash_talk_dislex.png'
  }
};
const PROXIMITY_ICONS = {
  sick: '/static/proximity_assets/1.png',
  vexed: '/static/proximity_assets/2.png',
  intrigued: '/static/proximity_assets/3.png',
  overexcited: '/static/proximity_assets/4.png',
  solar: '/static/proximity_assets/5.png',
  found: '/static/proximity_assets/6.png'
};
const ORCA_LINES = {
  neutral: {
    sick: ['Nope…'],
    vexed: ['Mouais….'],
    intrigued: ['Hmmmm okok'],
    overexcited: ['Dammmmnnnn !!'],
    solar: ['WWWWOOOOOOOAAAAAAAAAAAAWWWW !!!!'],
    found: ['Bien ouej !!!'],
    unknown: [
      '¿Hablas español?',
      'Je trouve pas ce mot dans le vocabulaire.'
    ],
    'first-letter': ['voila le première lettre'],
    'word-length': ['Voila la taille du mot'],
    'better-word': ['Essaie ce voisin'],
    'golden-fish': ['Amen'],
    'timer-start': ['Hajime']
  },
  trashtalk: {
    sick: [
      'Nope, nope nope nope c’est vraiment nul',
      'vrmt t’abuses fais un effort',
      'Je crois t’as cours de dessin la faut que t’y aille',
      'Sinon demande de l’aide à tes élèves de 8 ans nan ??',
      'pfffffffffff',
      'zZZzZZzzZzzZZZzzzzZZZ',
      'nononononononon tjr bien nul',
      'N.  U.  L. '
    ],
    vexed: [
      'Nope, nope nope nope c’est vraiment nul',
      'vrmt t’abuses fais un effort',
      'Je crois t’as cours de dessin la faut que t’y aille',
      'Sinon demande de l’aide à tes élèves de 8 ans nan ??',
      'pfffffffffff',
      'zZZzZZzzZzzZZZzzzzZZZ',
      'nononononononon tjr bien nul'
    ],
    intrigued: ['Hmmmm okok', 'Mouaiiiisss daccc', 'pfffffffffff', 'zZZzZZzzZzzZZZzzzzZZZ'],
    overexcited: ['DAMMMNNN !!'],
    solar: ['WOWOWOWOWOWO CALMA'],
    found: ['EZ !'],
    unknown: [
      'Sorry le jeu est pas en espagnol enft, on parle français ici',
      '¿Hablas español?',
      'On apprend pas l’orthographe à la HEP ??'
    ]
    ,
    'first-letter': ['voila le première lettre'],
    'word-length': ['Voila la taille du mot'],
    'better-word': ['Essaie ce voisin'],
    'golden-fish': ['Va te faire foutre'],
    'timer-start': ['Hajime']
  }
};

let dyslexicMode = localStorage.getItem('dyslexicMode') === 'true';
let orcaMode = localStorage.getItem('orcaMode') || 'neutral';
let currentOrcaMood = 'intrigued';
let draggedOrcaTool = null;
let kefirRainBuilt = false;

function toggleDyslexic() {
  dyslexicMode = !dyslexicMode;
  localStorage.setItem('dyslexicMode', dyslexicMode);
  document.getElementById('dyslexicToggle').textContent =
    'Dys. ' + (dyslexicMode ? 'ON' : 'OFF');
  document.getElementById('dyslexicToggle').classList.toggle('active', dyslexicMode);
  document.body.classList.toggle('dyslexic-mode', dyslexicMode);
  setOrcaState(currentOrcaMood, document.getElementById('orcaBubble').textContent || '...');
}

function buildKefirRain() {
  if (kefirRainBuilt) return;
  const container = document.getElementById('kefirRain');
  if (!container) return;

  const grains = [
    [4, 0.0, 0.8, 0.92, 0.1],
    [9, 0.18, -0.5, 1.05, 0.16],
    [14, 0.4, 1.1, 0.84, -0.12],
    [19, 0.08, -1.3, 0.96, 0.22],
    [24, 0.3, 0.6, 1.12, -0.28],
    [29, 0.52, -0.8, 0.76, 0.08],
    [35, 0.14, 1.5, 1.04, 0.24],
    [40, 0.44, -0.2, 0.9, -0.16],
    [46, 0.22, 0.9, 1.18, 0.12],
    [52, 0.6, -1.0, 0.8, -0.2],
    [58, 0.06, 0.3, 1.08, 0.18],
    [63, 0.36, -1.6, 0.88, -0.1],
    [69, 0.2, 1.2, 1.14, 0.26],
    [74, 0.48, -0.6, 0.82, -0.18],
    [80, 0.28, 0.4, 0.98, 0.1],
    [85, 0.66, -1.4, 1.1, -0.24],
    [90, 0.12, 0.7, 0.86, 0.14],
    [94, 0.54, -0.9, 1.06, -0.12]
  ];

  for (const [left, delay, drift, scale, squish] of grains) {
    const grain = document.createElement('span');
    grain.className = 'kefir-grain';
    grain.style.setProperty('--grain-left', left + '%');
    grain.style.setProperty('--grain-delay', delay + 's');
    grain.style.setProperty('--grain-drift', drift + 'vw');
    grain.style.setProperty('--grain-scale', scale);
    grain.style.setProperty('--grain-squish', squish);
    container.appendChild(grain);
  }

  kefirRainBuilt = true;
}

function proximityClass(mood) {
  return 'orca-' + mood;
}

function pick(list) {
  return list[Math.floor(Math.random() * list.length)];
}

function setOrcaState(mood, message) {
  currentOrcaMood = mood;
  const panel = document.getElementById('orcaPanel');
  panel.className = 'orca-panel ' + proximityClass(mood) + ' orca-mode-' + orcaMode + (orcaMode === 'mute' ? ' orca-muted' : '');
  document.getElementById('orcaAvatarImage').src =
    (dyslexicMode ? ORCA_MASCOTS.dyslexic[orcaMode] : ORCA_MASCOTS.default[orcaMode]) || ORCA_MASCOTS.default.neutral;
  document.getElementById('orcaAccessory').textContent = ORCA_TOOLS[orcaMode]?.badge || '';
  document.getElementById('orcaBubble').textContent = orcaMode === 'mute' ? '...' : message;
  syncOrcaTools();
}

function speakOrca(kind, mood) {
  const resolvedMood = mood || currentOrcaMood || 'neutral';
  if (orcaMode === 'mute') {
    setOrcaState(resolvedMood, '...');
    return;
  }

  const bank = ORCA_LINES[orcaMode][kind] || ORCA_LINES[orcaMode][resolvedMood] || ORCA_LINES.neutral.intrigued;
  setOrcaState(resolvedMood, pick(bank));
}

function syncOrcaTools() {
  document.querySelectorAll('.orca-tool').forEach(tool => {
    const toolConfig = ORCA_TOOLS[tool.dataset.orcaTool];
    tool.classList.toggle('active', toolConfig?.kind === 'mode' && tool.dataset.orcaTool === orcaMode);
  });
}

function applyOrcaTool(toolName, forceMessage) {
  const tool = ORCA_TOOLS[toolName];
  if (!tool || tool.kind !== 'mode') return;
  orcaMode = tool.mode;
  localStorage.setItem('orcaMode', orcaMode);
  if (orcaMode === 'mute') {
    setOrcaState(currentOrcaMood, '...');
    return;
  }
  const message = forceMessage || tool.bubble;
  setOrcaState(currentOrcaMood, message);
}

// --- Charlie : confetti + étoiles, portés depuis charlie.html ---
const CHARLIE_CONFETTI_COLORS = ['#ffd23f', '#7fe3f0', '#e03131', '#eaf4fb', '#5ec8e5', '#ff8fab'];

function buildCharlieStar(x, y, size, delayMs) {
  const star = document.createElement('div');
  star.className = 'charlie-star';
  star.style.left = x + 'px';
  star.style.top = y + 'px';
  star.style.animationDelay = delayMs + 'ms';
  star.innerHTML =
    '<svg width="' + size + '" height="' + size + '" viewBox="0 0 24 24">' +
    '<path d="M12,0 L14.4,9.6 L24,12 L14.4,14.4 L12,24 L9.6,14.4 L0,12 L9.6,9.6 Z" fill="#ffd23f"/></svg>';
  return star;
}

// Déclenché par le clic sur le bateau (onclick dans le template, pas de
// listener JS séparé — cohérent avec le style onclick="..." déjà utilisé
// partout ailleurs dans ce template).
function triggerCharlieParty() {
  const party = document.getElementById('charlieParty');
  if (!party) return;
  party.innerHTML = '';
  party.classList.add('active');

  const banner = document.createElement('div');
  banner.className = 'charlie-banner';
  banner.innerHTML = '<b>TRÈS RARE SONT CEUX<br>QUI TROUVENT CHARLI</b><small>tu l\'as vu</small>';
  party.appendChild(banner);

  const width = party.clientWidth;
  const height = party.clientHeight;
  for (let i = 0; i < 70; i++) {
    const piece = document.createElement('div');
    piece.className = 'charlie-confetti';
    piece.style.left = Math.random() * width + 'px';
    piece.style.top = (-20 - Math.random() * 60) + 'px';
    piece.style.background = CHARLIE_CONFETTI_COLORS[i % CHARLIE_CONFETTI_COLORS.length];
    piece.style.setProperty('--confetti-spin', (Math.random() * 900 - 450) + 'deg');
    piece.style.animationDelay = (Math.random() * 550) + 'ms';
    piece.style.animationDuration = (1500 + Math.random() * 900) + 'ms';
    party.appendChild(piece);
  }
  for (let i = 0; i < 16; i++) {
    party.appendChild(buildCharlieStar(
      Math.random() * width,
      Math.random() * height * 0.8,
      10 + Math.random() * 16,
      Math.random() * 900
    ));
  }

  setTimeout(() => {
    party.classList.remove('active');
    party.innerHTML = '';
  }, 3400);
}

// --- Aigles : la fille bascule sur son visage joyeux le temps du passage ---
function showGirlJoy() {
  document.querySelectorAll('.scene-girl-calme').forEach(el => {
    el.style.animation = 'none';
    el.style.opacity = '0';
  });
  document.querySelectorAll('.scene-girl-joie').forEach(el => {
    el.style.animation = 'none';
    el.style.opacity = '1';
  });
}

function restoreGirlCycle() {
  document.querySelectorAll('.scene-girl-calme, .scene-girl-joie').forEach(el => {
    el.style.animation = '';
    el.style.opacity = '';
  });
}

// Table de déclaration : ajouter un easter egg = une entrée ici + son
// balisage dans templates/orquantix/index.html. `onShow`/`onHide` sont
// optionnels (ex : construire la pluie de kefir à la volée, ou faire
// basculer la fille sur son visage joyeux pendant le passage des
// aigles) ; `duration` surcharge les 3200 ms par défaut pour les eggs
// qui ont besoin de plus de temps que leur animation CSS (vélo : 7 s
// d'aller-retour ; Charlie : 9 s de traversée + marge pour la fête
// s'il est cliqué juste avant de sortir de l'écran).
const EASTER_EGGS = [
  { id: 'easterShachi', triggers: ['shachi'] },
  { id: 'easterMathieu', triggers: ['mathieu'] },
  { id: 'easterConstance', triggers: ['constance'] },
  { id: 'easterKefir', triggers: ['kefir'], onShow: buildKefirRain },
  { id: 'easterVelo', triggers: ['velo', 'vélo'], duration: 7200 },
  { id: 'easterStLuc', triggers: ['st-luc', 'stluc', 'st luc'] },
  { id: 'easterMullet', triggers: ['mullet'] },
  { id: 'easterVoisin', triggers: ['voisin'] },
  { id: 'easterCharlie', triggers: ['charlie'], duration: 13000 },
  { id: 'easterAigles', triggers: ['aigle', 'aigles'], duration: 6700, onShow: showGirlJoy, onHide: restoreGirlCycle }
];

let activeEasterEgg = null;
let easterEggTimeoutId = null;

function triggerEasterEgg(word) {
  const normalized = String(word || '').trim().toLowerCase();
  const layer = document.getElementById('easterEggLayer');

  // Coupe proprement l'egg précédent (timeout + onHide) avant d'en
  // afficher un nouveau, plutôt que de balayer tous les eggs à chaque
  // appel : un retrigger pendant qu'un egg tourne encore doit annuler
  // son timeout en attente, sans quoi il se déclenche plus tard sur
  // le mauvais egg (ex : restoreGirlCycle qui retombe après coup sur
  // un état qui n'a plus rien à voir avec aigles).
  if (easterEggTimeoutId !== null) {
    clearTimeout(easterEggTimeoutId);
    easterEggTimeoutId = null;
  }
  if (activeEasterEgg) {
    const prevTarget = document.getElementById(activeEasterEgg.id);
    if (prevTarget) prevTarget.classList.remove('active');
    if (activeEasterEgg.onHide) activeEasterEgg.onHide();
    activeEasterEgg = null;
  }
  layer.classList.remove('active');

  const match = EASTER_EGGS.find(egg => egg.triggers.includes(normalized));
  if (!match) return;

  const target = document.getElementById(match.id);
  if (!target) return;

  if (match.onShow) match.onShow();

  layer.classList.add('active');
  // Force un reflow avant de réappliquer .active : un même easter egg
  // redéclenché pendant que son animation tourne encore (ex : retaper
  // « vélo » avant la fin de l'aller-retour) ne redémarrerait pas son
  // animation CSS sinon — le remove + add synchrones seraient fusionnés
  // par le navigateur sans jamais faire apparaître l'état « off ».
  void target.offsetWidth;
  target.classList.add('active');
  activeEasterEgg = match;

  easterEggTimeoutId = setTimeout(() => {
    target.classList.remove('active');
    layer.classList.remove('active');
    if (match.onHide) match.onHide();
    if (activeEasterEgg === match) activeEasterEgg = null;
    easterEggTimeoutId = null;
  }, match.duration || 3200);
}

function initOrcaDragAndDrop() {
  const panel = document.getElementById('orcaPanel');
  const tools = document.querySelectorAll('.orca-tool');

  tools.forEach(tool => {
    tool.addEventListener('dragstart', event => {
      draggedOrcaTool = tool.dataset.orcaTool;
      tool.classList.add('dragging');
      event.dataTransfer.effectAllowed = 'move';
      event.dataTransfer.setData('text/plain', draggedOrcaTool);
    });

    tool.addEventListener('dragend', () => {
      draggedOrcaTool = null;
      tool.classList.remove('dragging');
      panel.classList.remove('drop-target');
    });
  });

  panel.addEventListener('dragover', event => {
    event.preventDefault();
    panel.classList.add('drop-target');
  });

  panel.addEventListener('dragleave', event => {
    if (!panel.contains(event.relatedTarget)) {
      panel.classList.remove('drop-target');
    }
  });

  panel.addEventListener('drop', event => {
    event.preventDefault();
    panel.classList.remove('drop-target');
    const toolName = event.dataTransfer.getData('text/plain') || draggedOrcaTool;
    const tool = ORCA_TOOLS[toolName];
    if (!tool) return;
    if (tool.kind === 'mode') {
      applyOrcaTool(toolName);
      return;
    }
      if (tool.kind === 'hint') {
        if (toolName === 'golden-fish' && orcaMode === 'trashtalk') {
          if (orcaMode !== 'mute') {
          document.getElementById('orcaBubble').textContent = 'T’as cru j’étais une michto, pas de golden fish pour moi !!!';
          }
          return;
        }
      requestHint(tool.hintType);
    }
  });
}

initOrcaDragAndDrop();
