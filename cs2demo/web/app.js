const RADAR_SIZE = 1024;

const state = {
  demos: [],
  demoId: null,
  manifest: null,
  replayIndex: null,
  roundCache: new Map(),
  roundData: null,
  currentRound: null,
  currentTick: null,
  frameIndex: 0,
  playing: false,
  lastStep: 0,
  rafId: null,
  playStartTime: 0,
  playStartTick: null,
  roundLoadSeq: 0,
  yawCacheBySteamid: new Map(),
  yawUnit: 'degree',
  debugYaw: false,
  radarImage: new Image(),
  sandbox: null,
  drag: null,
  arrowDraft: null,
  brushDraft: null,
  laserPoint: null,
  remoteCursors: new Map(),
  activeFindingId: null,
  selectedUtility: null,
  utilityPuffCache: new Map(),
  activeBottomTab: 'findings',
  bottomDockCollapsed: false,
  layoutResize: null,
  activeMapTool: 'select',
  viewport: {
    zoom: 1,
    panX: 0,
    panY: 0,
    fitScale: 1,
    minZoom: 0.5,
    maxZoom: 5,
    userAdjusted: false,
  },
  viewportDrag: null,
  playerSideBySteamid: new Map(),
  selectedPlayerId: null,
  room: {
    code: null,
    clientId: null,
    socket: null,
    connected: false,
    participants: {},
    suppressBroadcast: false,
    remoteApplying: false,
    lastMoveSentAt: 0,
    pendingSnapshot: null,
    shareUrl: null,
    publicReady: false,
    shareMode: 'local',
    warning: null,
    pendingJoin: null,
    stableClientId: null,
    joinProfile: null,
    heartbeatTimer: null,
    reconnectTimer: null,
    reconnectAttempts: 0,
    intentionalClose: false,
    reconnecting: false,
    lastHeartbeatAckAt: 0,
    lastCursorSentAt: 0,
  },
  shareStatus: {
    publicReady: false,
    publicBaseUrl: '',
    shareMode: 'local',
    warning: null,
  },
  analysisFilters: {
    side: 'all',
    playerId: 'all',
    severity: 'all',
    visualMode: 'highlight',
    findingTypes: {
      trade_failure: true,
      trade_fail: true,
      entry_success: true,
      entry_failure: true,
      entry_failed: true,
      stall: true,
      postplant_loss: true,
      postplant: true,
    },
  },
  filters: {
    showHealthBars: true,
    showNames: true,
    showYaw: true,
    showUtilities: true,
    showUtilityTrajectories: true,
    showUtilityEffects: true,
    showFlashBurst: true,
    showBlindHalo: true,
    showHeBlast: true,
    showHeSmoke: true,
    showSmokeRange: true,
    showSmokeTimer: true,
    showMolotovRange: true,
    types: {
      smoke: true,
      flashbang: true,
      hegrenade: true,
      molotov: true,
      decoy: false,
    },
  },
};

const els = {
  demoSelect: document.getElementById('demoSelect'),
  prepareBtn: document.getElementById('prepareBtn'),
  createRoomBtn: document.getElementById('createRoomBtn'),
  roomBar: document.getElementById('roomBar'),
  roomCodeText: document.getElementById('roomCodeText'),
  roomParticipantsText: document.getElementById('roomParticipantsText'),
  roomModeText: document.getElementById('roomModeText'),
  copyRoomLinkBtn: document.getElementById('copyRoomLinkBtn'),
  leaveRoomBtn: document.getElementById('leaveRoomBtn'),
  shareStatusText: document.getElementById('shareStatusText'),
  shareRoomModal: document.getElementById('shareRoomModal'),
  shareRoomTitle: document.getElementById('shareRoomTitle'),
  shareRoomMessage: document.getElementById('shareRoomMessage'),
  shareRoomCodeInput: document.getElementById('shareRoomCodeInput'),
  shareRoomUrlInput: document.getElementById('shareRoomUrlInput'),
  shareRoomWarning: document.getElementById('shareRoomWarning'),
  copyShareRoomLinkBtn: document.getElementById('copyShareRoomLinkBtn'),
  enterCreatedRoomBtn: document.getElementById('enterCreatedRoomBtn'),
  closeShareRoomModalBtn: document.getElementById('closeShareRoomModalBtn'),
  joinRoomModal: document.getElementById('joinRoomModal'),
  joinRoomTitle: document.getElementById('joinRoomTitle'),
  joinRoomMessage: document.getElementById('joinRoomMessage'),
  joinDisplayNameInput: document.getElementById('joinDisplayNameInput'),
  joinRoleSelect: document.getElementById('joinRoleSelect'),
  joinRoomWarning: document.getElementById('joinRoomWarning'),
  confirmJoinRoomBtn: document.getElementById('confirmJoinRoomBtn'),
  cancelJoinRoomBtn: document.getElementById('cancelJoinRoomBtn'),
  roundSelect: document.getElementById('roundSelect'),
  prevRoundBtn: document.getElementById('prevRoundBtn'),
  back5Btn: document.getElementById('back5Btn'),
  playBtn: document.getElementById('playBtn'),
  pauseBtn: document.getElementById('pauseBtn'),
  forward5Btn: document.getElementById('forward5Btn'),
  nextRoundBtn: document.getElementById('nextRoundBtn'),
  sandboxBtn: document.getElementById('sandboxBtn'),
  resumeDemoBtn: document.getElementById('resumeDemoBtn'),
  resetSandboxBtn: document.getElementById('resetSandboxBtn'),
  saveSandboxBtn: document.getElementById('saveSandboxBtn'),
  statusText: document.getElementById('statusText'),
  canvas: document.getElementById('radarCanvas'),
  mapStage: document.getElementById('mapStage'),
  mapToolbar: document.getElementById('mapToolbar'),
  rightResizeHandle: document.getElementById('rightResizeHandle'),
  bottomResizeHandle: document.getElementById('bottomResizeHandle'),
  mapToolButtons: Array.from(document.querySelectorAll('.map-tool-button[data-map-tool]')),
  zoomInBtn: document.getElementById('zoomInBtn'),
  zoomOutBtn: document.getElementById('zoomOutBtn'),
  fitMapBtn: document.getElementById('fitMapBtn'),
  resetViewBtn: document.getElementById('resetViewBtn'),
  sandboxToolbarActions: document.getElementById('sandboxToolbarActions'),
  markerCanvas: document.getElementById('markerCanvas'),
  timeline: document.getElementById('timeline'),
  tickText: document.getElementById('tickText'),
  modeText: document.getElementById('modeText'),
  findingsList: document.getElementById('findingsList'),
  utilitiesList: document.getElementById('utilitiesList'),
  playersList: document.getElementById('playersList'),
  sandboxObjectsList: document.getElementById('sandboxObjectsList'),
  roomStatusText: document.getElementById('roomStatusText'),
  roomParticipantsList: document.getElementById('roomParticipantsList'),
  filterSide: document.getElementById('filterSide'),
  filterPlayer: document.getElementById('filterPlayer'),
  filterSeverity: document.getElementById('filterSeverity'),
  filterVisualMode: document.getElementById('filterVisualMode'),
  findingTypeFilters: Array.from(document.querySelectorAll('.finding-type-filter')),
  clearAnalysisFiltersBtn: document.getElementById('clearAnalysisFiltersBtn'),
  utilityDetail: document.getElementById('utilityDetail'),
  showHealthBars: document.getElementById('showHealthBars'),
  showNames: document.getElementById('showNames'),
  showYaw: document.getElementById('showYaw'),
  showUtilities: document.getElementById('showUtilities'),
  showUtilityTrajectories: document.getElementById('showUtilityTrajectories'),
  showUtilityEffects: document.getElementById('showUtilityEffects'),
  showFlashBurst: document.getElementById('showFlashBurst'),
  showBlindHalo: document.getElementById('showBlindHalo'),
  showHeBlast: document.getElementById('showHeBlast'),
  showHeSmoke: document.getElementById('showHeSmoke'),
  showSmokeRange: document.getElementById('showSmokeRange'),
  showSmokeTimer: document.getElementById('showSmokeTimer'),
  showMolotovRange: document.getElementById('showMolotovRange'),
  showSmoke: document.getElementById('showSmoke'),
  showFlashbang: document.getElementById('showFlashbang'),
  showHegrenade: document.getElementById('showHegrenade'),
  showMolotov: document.getElementById('showMolotov'),
  showDecoy: document.getElementById('showDecoy'),
  sandboxStatus: document.getElementById('sandboxStatus'),
  sandboxSelectedPlayer: document.getElementById('sandboxSelectedPlayer'),
  sandboxSelectedUtility: document.getElementById('sandboxSelectedUtility'),
  sandboxUtilityMenu: document.getElementById('sandboxUtilityMenu'),
  cancelUtilityThrowBtn: document.getElementById('cancelUtilityThrowBtn'),
  clearSandboxUtilitiesBtn: document.getElementById('clearSandboxUtilitiesBtn'),
  playSandboxBtn: document.getElementById('playSandboxBtn'),
  resetSandboxTimeBtn: document.getElementById('resetSandboxTimeBtn'),
  bottomDock: document.getElementById('bottomDock'),
  bottomDockToggle: document.getElementById('bottomDockToggle'),
  tabButtons: Array.from(document.querySelectorAll('.tab-button')),
  tabPanels: Array.from(document.querySelectorAll('.tab-panel')),
};
const ctx = els.canvas.getContext('2d');
const markerCtx = els.markerCanvas.getContext('2d');

const utilityStyle = {
  smoke: { color: '#8f959e', fill: 'rgba(75,75,75,0.42)' },
  flashbang: { color: '#ffffff', fill: 'rgba(255,255,255,0.32)' },
  hegrenade: { color: '#ef4444', fill: 'rgba(239,68,68,0.25)' },
  molotov: { color: '#f97316', fill: 'rgba(249,115,22,0.28)' },
  decoy: { color: '#a78bfa', fill: 'rgba(167,139,250,0.22)' },
};

const defaultUtilityEffects = {
  flashbang: { flash_visual_duration_sec: 0.8, flash_core_radius: 160, flash_fade_radius: 500, max_blind_duration_sec: 5.0 },
  hegrenade: { blast_visual_duration_sec: 0.7, smoke_visual_duration_sec: 2.5, damage_radius: 350, inner_radius: 120, outer_radius: 350 },
  smoke: { duration_sec: 18.0, radius: 170, fade_in_sec: 1.0, fade_out_sec: 1.5, core_color: 'rgba(55,55,55,0.62)', outer_color: 'rgba(95,95,95,0.34)', edge_color: 'rgba(120,120,120,0.18)', t_core_color: 'rgba(255,177,66,0.68)', t_outer_color: 'rgba(245,158,11,0.40)', t_edge_color: 'rgba(251,191,36,0.20)', ct_core_color: 'rgba(96,165,250,0.68)', ct_outer_color: 'rgba(59,130,246,0.40)', ct_edge_color: 'rgba(147,197,253,0.20)', timer_bg_color: 'rgba(15,17,23,0.72)', timer_fill_color: 'rgba(238,242,247,0.82)', timer_text_color: 'rgba(255,255,255,0.88)' },
  molotov: { duration_sec: 7.0, max_duration_sec: 7.5, radius: 180, fade_in_sec: 0.5, fade_out_sec: 0.8 },
  decoy: { duration_sec: 8.0, radius: 90, fade_in_sec: 0.2, fade_out_sec: 0.5 },
};

async function api(path, options = {}) {
  const res = await fetch(path, options);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status} ${text}`);
  }
  return res.json();
}

function setStatus(text) {
  els.statusText.textContent = text;
}

function roomCodeFromUrl() {
  const pathMatch = window.location.pathname.match(/^\/r\/([^/]+)\/?$/);
  if (pathMatch) return decodeURIComponent(pathMatch[1]);
  return new URLSearchParams(window.location.search).get('room');
}

function isRoomMode() {
  return Boolean(state.room.code && state.room.connected && state.room.socket);
}

function canonicalRoomPath(roomCode) {
  return `/r/${encodeURIComponent(roomCode)}`;
}

function wsUrlForRoom(roomCode) {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}/ws/rooms/${encodeURIComponent(roomCode)}`;
}

function storedJoinProfile() {
  return {
    display_name: localStorage.getItem('cs2demo.room.displayName') || '',
    role: localStorage.getItem('cs2demo.room.role') || 'viewer',
    assigned_player_id: localStorage.getItem('cs2demo.room.assignedPlayerId') || '',
  };
}

function saveJoinProfile(profile) {
  localStorage.setItem('cs2demo.room.displayName', profile.display_name || '');
  localStorage.setItem('cs2demo.room.role', profile.role || 'viewer');
  localStorage.setItem('cs2demo.room.assignedPlayerId', profile.assigned_player_id || '');
}

function stableRoomClientId() {
  const key = 'cs2demo.room.clientId';
  let clientId = localStorage.getItem(key);
  if (!clientId) {
    clientId = crypto.randomUUID ? crypto.randomUUID() : `client-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    localStorage.setItem(key, clientId);
  }
  state.room.stableClientId = clientId;
  return clientId;
}

function joinProfileWithClientId(profile = {}) {
  return {
    ...profile,
    client_id: stableRoomClientId(),
  };
}

async function loadDemoReplay(demoId, options = {}) {
  pause({ redraw: false });
  state.demoId = demoId;
  els.demoSelect.value = demoId;
  state.roundCache = new Map();
  state.roundData = null;
  state.currentRound = null;
  state.currentTick = null;
  state.frameIndex = 0;
  state.activeFindingId = null;
  state.selectedUtility = null;
  state.yawCacheBySteamid.clear();
  setStatus('准备 replay 数据...');
  await api(`/api/demos/${state.demoId}/prepare`, { method: 'POST' });
  state.manifest = await api(`/api/demos/${state.demoId}/replay.json`);
  state.replayIndex = buildReplayIndex(state.manifest);
  await loadRadarImage(state.manifest.map.radar_url);
  fillRounds();
  refreshPlayerFilterOptions();
  renderFindings();
  renderUtilityDetail();
  const firstRound = options.roundNumber ?? state.replayIndex.roundNumbers[0];
  if (firstRound !== undefined) await switchToRound(firstRound, { tick: options.tick, suppressBroadcast: true });
  setStatus('已加载');
}

async function init() {
  await loadShareStatus();
  const payload = await api('/api/demos');
  state.demos = payload.demos;
  state.demoId = payload.default_demo_id;
  els.demoSelect.innerHTML = '';
  for (const demo of state.demos) {
    const opt = document.createElement('option');
    opt.value = demo.demo_id;
    opt.textContent = demo.filename;
    if (demo.demo_id === state.demoId) opt.selected = true;
    els.demoSelect.appendChild(opt);
  }
  setStatus('请选择 demo 并加载');
  bindEvents();
  resizeCanvasToStage({ forceFit: true });
  updateNavigationButtons();
  updateSandboxButtons();
  updateMapToolbar();
  renderRoomPanel();
  drawEmpty();
  const roomCode = roomCodeFromUrl();
  if (roomCode) await loadRoomFromUrl(roomCode);
}

function bindEvents() {
  els.demoSelect.addEventListener('change', () => { state.demoId = els.demoSelect.value; });
  els.prepareBtn.addEventListener('click', prepareAndLoad);
  els.createRoomBtn?.addEventListener('click', createRoomFromCurrentState);
  els.copyRoomLinkBtn?.addEventListener('click', () => openShareRoomModal());
  els.leaveRoomBtn?.addEventListener('click', leaveRoom);
  els.copyShareRoomLinkBtn?.addEventListener('click', copyRoomLink);
  els.enterCreatedRoomBtn?.addEventListener('click', enterCreatedRoom);
  els.closeShareRoomModalBtn?.addEventListener('click', closeShareRoomModal);
  els.confirmJoinRoomBtn?.addEventListener('click', confirmJoinRoom);
  els.cancelJoinRoomBtn?.addEventListener('click', cancelJoinRoom);
  els.roundSelect.addEventListener('change', () => switchToRound(Number(els.roundSelect.value)));
  els.prevRoundBtn.addEventListener('click', previousRound);
  els.back5Btn.addEventListener('click', () => seekBySeconds(-5));
  els.playBtn.addEventListener('click', play);
  els.pauseBtn.addEventListener('click', pause);
  els.forward5Btn.addEventListener('click', () => seekBySeconds(5));
  els.nextRoundBtn.addEventListener('click', nextRound);
  els.timeline.addEventListener('input', () => {
    const idx = Number(els.timeline.value);
    const tick = state.roundData?.frames?.[idx]?.tick;
    if (tick !== undefined) seekToTick(tick, { keepPlaying: false });
  });
  els.sandboxBtn.addEventListener('click', enterSandbox);
  els.resumeDemoBtn.addEventListener('click', resumeDemoPlayback);
  els.resetSandboxBtn.addEventListener('click', resetSandboxToSource);
  els.saveSandboxBtn.addEventListener('click', saveSandbox);
  els.cancelUtilityThrowBtn.addEventListener('click', cancelUtilityThrow);
  els.clearSandboxUtilitiesBtn.addEventListener('click', clearSandboxUtilities);
  els.playSandboxBtn.addEventListener('click', toggleSandboxPlayback);
  els.resetSandboxTimeBtn.addEventListener('click', resetSandboxTime);
  els.sandboxUtilityMenu.addEventListener('click', onSandboxUtilityMenuClick);
  document.addEventListener('keydown', handleGlobalKeydown);
  window.addEventListener('resize', () => resizeCanvasToStage());
  bindBottomTabs();
  bindMapToolbar();
  bindLayoutResize();
  els.canvas.addEventListener('wheel', onCanvasWheel, { passive: false });
  els.canvas.addEventListener('mousedown', onCanvasDown);
  els.canvas.addEventListener('mousemove', onCanvasMove);
  els.canvas.addEventListener('mouseup', onCanvasUp);
  els.canvas.addEventListener('mouseleave', onCanvasUp);
  els.canvas.addEventListener('click', onCanvasClick);
  els.canvas.addEventListener('dblclick', onCanvasDblClick);
  bindFilter(els.showHealthBars, value => { state.filters.showHealthBars = value; });
  bindFilter(els.showNames, value => { state.filters.showNames = value; });
  bindFilter(els.showYaw, value => { state.filters.showYaw = value; });
  bindFilter(els.showUtilities, value => { state.filters.showUtilities = value; });
  bindFilter(els.showUtilityTrajectories, value => { state.filters.showUtilityTrajectories = value; });
  bindFilter(els.showUtilityEffects, value => { state.filters.showUtilityEffects = value; });
  bindFilter(els.showFlashBurst, value => { state.filters.showFlashBurst = value; });
  bindFilter(els.showBlindHalo, value => { state.filters.showBlindHalo = value; });
  bindFilter(els.showHeBlast, value => { state.filters.showHeBlast = value; });
  bindFilter(els.showHeSmoke, value => { state.filters.showHeSmoke = value; });
  bindFilter(els.showSmokeRange, value => { state.filters.showSmokeRange = value; });
  bindFilter(els.showSmokeTimer, value => { state.filters.showSmokeTimer = value; });
  bindFilter(els.showMolotovRange, value => { state.filters.showMolotovRange = value; });
  bindFilter(els.showSmoke, value => { state.filters.types.smoke = value; });
  bindFilter(els.showFlashbang, value => { state.filters.types.flashbang = value; });
  bindFilter(els.showHegrenade, value => { state.filters.types.hegrenade = value; });
  bindFilter(els.showMolotov, value => { state.filters.types.molotov = value; });
  bindFilter(els.showDecoy, value => { state.filters.types.decoy = value; });
  bindAnalysisFilters();
}

function bindAnalysisFilters() {
  els.filterSide?.addEventListener('change', () => {
    state.analysisFilters.side = els.filterSide.value;
    refreshAnalysisFilterViews();
  });
  els.filterPlayer?.addEventListener('change', () => {
    state.analysisFilters.playerId = els.filterPlayer.value;
    refreshAnalysisFilterViews();
  });
  els.filterSeverity?.addEventListener('change', () => {
    state.analysisFilters.severity = els.filterSeverity.value;
    refreshAnalysisFilterViews();
  });
  els.filterVisualMode?.addEventListener('change', () => {
    state.analysisFilters.visualMode = els.filterVisualMode.value;
    refreshAnalysisFilterViews();
  });
  for (const input of els.findingTypeFilters || []) {
    input.addEventListener('change', () => {
      state.analysisFilters.findingTypes[input.dataset.findingType] = input.checked;
      refreshAnalysisFilterViews();
    });
  }
  els.clearAnalysisFiltersBtn?.addEventListener('click', clearAnalysisFilters);
}

function bindFilter(input, setter) {
  input.addEventListener('change', () => {
    setter(input.checked);
    renderMarkers();
    draw();
  });
}

function bindBottomTabs() {
  for (const button of els.tabButtons) {
    button.addEventListener('click', () => setBottomTab(button.dataset.tab));
  }
  els.bottomDockToggle.addEventListener('click', toggleBottomDock);
}

function toggleBottomDock() {
  state.bottomDockCollapsed = !state.bottomDockCollapsed;
  els.bottomDock.classList.toggle('collapsed', state.bottomDockCollapsed);
  document.body.classList.toggle('dock-collapsed', state.bottomDockCollapsed);
  els.bottomDockToggle.textContent = state.bottomDockCollapsed ? '展开' : '收起';
  resizeCanvasToStage();
}

function bindLayoutResize() {
  els.rightResizeHandle?.addEventListener('pointerdown', evt => startLayoutResize(evt, 'right'));
  els.bottomResizeHandle?.addEventListener('pointerdown', evt => startLayoutResize(evt, 'bottom'));
  window.addEventListener('pointermove', onLayoutResizeMove);
  window.addEventListener('pointerup', stopLayoutResize);
  window.addEventListener('pointercancel', stopLayoutResize);
}

function startLayoutResize(evt, type) {
  evt.preventDefault();
  const layoutRect = document.querySelector('.layout')?.getBoundingClientRect();
  const dockRect = els.bottomDock?.getBoundingClientRect();
  state.layoutResize = {
    type,
    startX: evt.clientX,
    startY: evt.clientY,
    layoutWidth: layoutRect?.width || window.innerWidth,
    startRightWidth: Number.parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--right-width')) || 300,
    startDockHeight: dockRect?.height || 172,
  };
  document.body.classList.add(type === 'right' ? 'resizing-right' : 'resizing-bottom');
}

function onLayoutResizeMove(evt) {
  if (!state.layoutResize) return;
  evt.preventDefault();
  if (state.layoutResize.type === 'right') {
    const minRight = 240;
    const maxRight = Math.max(minRight, Math.min(520, state.layoutResize.layoutWidth - 620));
    const nextWidth = clamp(state.layoutResize.startRightWidth - (evt.clientX - state.layoutResize.startX), minRight, maxRight);
    document.documentElement.style.setProperty('--right-width', `${Math.round(nextWidth)}px`);
  } else {
    const minDock = 92;
    const maxDock = Math.min(360, Math.max(minDock, window.innerHeight - 360));
    const nextHeight = clamp(state.layoutResize.startDockHeight - (evt.clientY - state.layoutResize.startY), minDock, maxDock);
    state.bottomDockCollapsed = false;
    els.bottomDock.classList.remove('collapsed');
    document.body.classList.remove('dock-collapsed');
    els.bottomDockToggle.textContent = '收起';
    document.documentElement.style.setProperty('--bottom-dock-height', `${Math.round(nextHeight)}px`);
  }
  resizeCanvasToStage();
}

function stopLayoutResize() {
  if (!state.layoutResize) return;
  state.layoutResize = null;
  document.body.classList.remove('resizing-right', 'resizing-bottom');
  resizeCanvasToStage();
}

function setBottomTab(tabName) {
  state.activeBottomTab = tabName || 'findings';
  for (const button of els.tabButtons) button.classList.toggle('active', button.dataset.tab === state.activeBottomTab);
  for (const panel of els.tabPanels) {
    const active = panel.dataset.panel === state.activeBottomTab;
    panel.hidden = !active;
    panel.classList.toggle('active', active);
  }
}

function handleGlobalKeydown(evt) {
  if (evt.key === 'Escape') handleSandboxEscape();
}

function bindMapToolbar() {
  for (const button of els.mapToolButtons) {
    button.addEventListener('click', () => setMapTool(button.dataset.mapTool));
  }
  els.zoomInBtn.addEventListener('click', () => zoomAt(els.canvas.width / 2, els.canvas.height / 2, state.viewport.zoom * 1.2));
  els.zoomOutBtn.addEventListener('click', () => zoomAt(els.canvas.width / 2, els.canvas.height / 2, state.viewport.zoom / 1.2));
  els.fitMapBtn.addEventListener('click', () => resetViewportToFit({ userAdjusted: false }));
  els.resetViewBtn.addEventListener('click', () => resetViewportToFit({ userAdjusted: false }));
}

function setMapTool(tool) {
  state.activeMapTool = tool || (state.sandbox ? 'move' : 'select');
  closeUtilityMenu();
  updateMapToolbar();
}

function updateMapToolbar() {
  const inSandbox = Boolean(state.sandbox);
  if (!inSandbox && ['move', 'arrow', 'text', 'brush', 'eraser', 'laser', 'utility'].includes(state.activeMapTool)) state.activeMapTool = 'select';
  for (const button of els.mapToolButtons) {
    const sandboxOnly = button.classList.contains('sandbox-only');
    button.hidden = sandboxOnly && !inSandbox;
    button.classList.toggle('active', button.dataset.mapTool === state.activeMapTool);
  }
  if (els.sandboxToolbarActions) els.sandboxToolbarActions.hidden = !inSandbox;
}

function resizeCanvasToStage(options = {}) {
  if (!els.canvas || !els.mapStage) return;
  const rect = els.mapStage.getBoundingClientRect();
  const width = Math.max(320, Math.round(rect.width));
  const height = Math.max(320, Math.round(rect.height));
  const oldCenter = screenToRadar(els.canvas.width / 2, els.canvas.height / 2);
  if (els.canvas.width !== width) els.canvas.width = width;
  if (els.canvas.height !== height) els.canvas.height = height;
  const shouldFit = options.forceFit || !state.viewport.userAdjusted;
  if (shouldFit) {
    resetViewportToFit({ userAdjusted: false });
  } else {
    state.viewport.panX = els.canvas.width / 2 - oldCenter.x * state.viewport.zoom;
    state.viewport.panY = els.canvas.height / 2 - oldCenter.y * state.viewport.zoom;
    clampViewportPan();
    syncSandboxUtilityMenu();
    draw();
  }
}

function resetViewportToFit(options = {}) {
  const fitScale = Math.min(els.canvas.width / RADAR_SIZE, els.canvas.height / RADAR_SIZE);
  state.viewport.fitScale = fitScale;
  state.viewport.minZoom = Math.max(0.2, fitScale * 0.5);
  state.viewport.maxZoom = Math.max(4, fitScale * 5);
  state.viewport.zoom = fitScale;
  state.viewport.panX = (els.canvas.width - RADAR_SIZE * fitScale) / 2;
  state.viewport.panY = (els.canvas.height - RADAR_SIZE * fitScale) / 2;
  state.viewport.userAdjusted = options.userAdjusted ?? false;
  clampViewportPan();
  syncSandboxUtilityMenu();
  draw();
}

function radarToScreen(radarX, radarY) {
  return {
    x: Number(radarX) * state.viewport.zoom + state.viewport.panX,
    y: Number(radarY) * state.viewport.zoom + state.viewport.panY,
  };
}

function screenToRadar(screenX, screenY) {
  return {
    x: (Number(screenX) - state.viewport.panX) / state.viewport.zoom,
    y: (Number(screenY) - state.viewport.panY) / state.viewport.zoom,
  };
}

function applyViewportTransform(context) {
  context.setTransform(state.viewport.zoom, 0, 0, state.viewport.zoom, state.viewport.panX, state.viewport.panY);
}

function screenPoint(evt) {
  const rect = els.canvas.getBoundingClientRect();
  return {
    x: (evt.clientX - rect.left) * (els.canvas.width / rect.width),
    y: (evt.clientY - rect.top) * (els.canvas.height / rect.height),
  };
}

function canvasRadarPoint(evt) {
  const point = screenPoint(evt);
  return screenToRadar(point.x, point.y);
}

function zoomAt(screenX, screenY, nextZoom) {
  const before = screenToRadar(screenX, screenY);
  state.viewport.zoom = Math.max(state.viewport.minZoom, Math.min(state.viewport.maxZoom, nextZoom));
  state.viewport.panX = screenX - before.x * state.viewport.zoom;
  state.viewport.panY = screenY - before.y * state.viewport.zoom;
  state.viewport.userAdjusted = true;
  clampViewportPan();
  syncSandboxUtilityMenu();
  draw();
}

function panViewportBy(dx, dy) {
  state.viewport.panX += dx;
  state.viewport.panY += dy;
  state.viewport.userAdjusted = true;
  clampViewportPan();
  syncSandboxUtilityMenu();
  draw();
}

function clampViewportPan() {
  const mapWidth = RADAR_SIZE * state.viewport.zoom;
  const mapHeight = RADAR_SIZE * state.viewport.zoom;
  const keepVisible = Math.min(180, Math.max(60, Math.min(els.canvas.width, els.canvas.height) * 0.25));
  if (mapWidth <= els.canvas.width) {
    state.viewport.panX = (els.canvas.width - mapWidth) / 2;
  } else {
    state.viewport.panX = Math.min(els.canvas.width - keepVisible, Math.max(keepVisible - mapWidth, state.viewport.panX));
  }
  if (mapHeight <= els.canvas.height) {
    state.viewport.panY = (els.canvas.height - mapHeight) / 2;
  } else {
    state.viewport.panY = Math.min(els.canvas.height - keepVisible, Math.max(keepVisible - mapHeight, state.viewport.panY));
  }
}

function onCanvasWheel(evt) {
  evt.preventDefault();
  const point = screenPoint(evt);
  const factor = evt.deltaY < 0 ? 1.12 : 1 / 1.12;
  zoomAt(point.x, point.y, state.viewport.zoom * factor);
}

async function prepareAndLoad() {
  try {
    if (isRoomMode()) {
      await switchRoomDemo(els.demoSelect.value);
      return;
    }
    await loadDemoReplay(els.demoSelect.value);
  } catch (err) {
    console.error(err);
    setStatus(`加载失败：${err.message}`);
  }
}

async function switchRoomDemo(demoId) {
  const previousDemoId = state.demoId;
  try {
    await loadDemoReplay(demoId, { suppressRoomSwitch: true });
    sendRoomMessage('switch_demo', {
      demo_id: state.demoId,
      round_number: state.currentRound,
      tick: state.currentTick,
      title: `${state.demoId} R${state.currentRound || 1}`,
    });
    setStatus(`房间已切换到 ${state.demoId}`);
  } catch (err) {
    if (previousDemoId && previousDemoId !== demoId) els.demoSelect.value = previousDemoId;
    throw err;
  }
}

async function loadShareStatus() {
  try {
    const status = await api('/api/share/status');
    state.shareStatus.publicReady = Boolean(status.public_ready);
    state.shareStatus.publicBaseUrl = status.public_base_url || '';
    state.shareStatus.shareMode = status.share_mode || 'local';
    state.shareStatus.warning = status.warning || status.message || null;
    renderShareStatus();
  } catch (err) {
    console.error(err);
    state.shareStatus.warning = '无法读取公网分享状态。';
    renderShareStatus();
  }
}

function renderShareStatus() {
  if (!els.shareStatusText) return;
  els.shareStatusText.classList.toggle('public-ready', state.shareStatus.publicReady);
  els.shareStatusText.textContent = state.shareStatus.publicReady ? `公网分享：${state.shareStatus.shareMode}` : '本地模式：队友打不开本机链接';
}

async function createRoomFromCurrentState() {
  try {
    if (!state.manifest) await loadDemoReplay(els.demoSelect.value);
    const payload = {
      demo_id: state.demoId,
      round_number: state.currentRound,
      tick: state.currentTick,
      title: `${state.demoId} R${state.currentRound || 1}`,
    };
    const result = await api('/api/rooms', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const room = result.room;
    applyRoomShareMetadata(result, room.room_code);
    history.replaceState(null, '', canonicalRoomPath(room.room_code));
    await applyRoomSnapshot(room, null);
    openShareRoomModal();
    setBottomTab('room');
  } catch (err) {
    console.error(err);
    setStatus(`创建房间失败：${err.message}`);
  }
}

async function loadRoomFromUrl(roomCode) {
  try {
    const payload = await api(`/api/rooms/${encodeURIComponent(roomCode)}`);
    applyRoomShareMetadata(payload, payload.room.room_code);
    await applyRoomSnapshot(payload.room, null);
    openJoinRoomModal(payload.room);
    setStatus(`房间 ${payload.room.room_code} 已加载，等待加入`);
  } catch (err) {
    console.error(err);
    setStatus(`加入房间失败：${err.message}`);
  }
}

function applyRoomShareMetadata(payload, fallbackCode = null) {
  state.room.code = payload.room_code || fallbackCode || state.room.code;
  state.room.shareUrl = payload.share_url || payload.join_url || state.room.shareUrl || (state.room.code ? `${window.location.origin}${canonicalRoomPath(state.room.code)}` : null);
  state.room.publicReady = Boolean(payload.public_ready);
  state.room.shareMode = payload.share_mode || 'local';
  state.room.warning = payload.warning || null;
}

async function applyRoomSnapshot(room, clientId) {
  if (!room) return;
  state.room.code = room.room_code;
  if (clientId) state.room.clientId = clientId;
  state.room.participants = room.participants || {};
  state.room.pendingSnapshot = room;
  if (room.demo_id && (room.demo_id !== state.demoId || !state.manifest)) {
    await loadDemoReplay(room.demo_id, { roundNumber: room.playback?.round_number, tick: room.playback?.tick });
  } else if (room.playback?.round_number !== undefined) {
    await withSuppressedRoomBroadcastAsync(() => switchToRound(room.playback.round_number, { tick: room.playback.tick, suppressBroadcast: true }));
  }
  if (room.mode === 'sandbox' && room.sandbox?.active !== false) {
    applyRoomSandbox(room.sandbox);
  } else if (state.sandbox && room.mode === 'replay') {
    exitSandboxLocal();
  }
  renderRoomPanel();
}

async function connectRoom(roomCode, profile = {}) {
  const profileHasClientId = Boolean(profile.client_id);
  resetRoomConnectionTimers();
  if (state.room.socket) {
    state.room.intentionalClose = true;
    state.room.socket.intentionalClose = true;
    state.room.socket.close();
  }
  state.room.code = roomCode;
  state.room.joinProfile = profileHasClientId ? profile : joinProfileWithClientId(profile);
  state.room.intentionalClose = false;
  const socket = new WebSocket(wsUrlForRoom(roomCode));
  const profileForConnection = state.room.joinProfile;
  state.room.socket = socket;
  await new Promise((resolve, reject) => {
    socket.addEventListener('open', resolve, { once: true });
    socket.addEventListener('error', () => reject(new Error('房间连接失败。可能是公网隧道不支持 WebSocket，或服务已停止。')), { once: true });
  });
  socket.send(JSON.stringify({ type: 'join_room', payload: profileForConnection }));
  socket.addEventListener('message', event => handleRoomSocketMessage(event));
  socket.addEventListener('close', event => {
    if (state.room.socket !== socket && !socket.intentionalClose) return;
    const duplicateSession = event.code === 4410;
    const shouldReconnect = !duplicateSession && !state.room.intentionalClose && !socket.intentionalClose && state.room.code && state.room.joinProfile;
    state.room.connected = false;
    if (state.room.socket === socket) state.room.socket = null;
    stopRoomHeartbeat();
    if (duplicateSession) {
      state.room.reconnecting = false;
      setStatus('同一身份已在其他页面连接，此页面已断开房间。');
    } else if (shouldReconnect) {
      scheduleRoomReconnect();
    }
    renderRoomPanel();
  });
}

function resetRoomConnectionTimers() {
  stopRoomHeartbeat();
  if (state.room.reconnectTimer) clearTimeout(state.room.reconnectTimer);
  state.room.reconnectTimer = null;
  state.room.reconnecting = false;
}

function startRoomHeartbeat() {
  stopRoomHeartbeat();
  state.room.lastHeartbeatAckAt = Date.now();
  state.room.heartbeatTimer = setInterval(() => {
    if (!state.room.socket || state.room.socket.readyState !== WebSocket.OPEN) return;
    const sinceAck = Date.now() - state.room.lastHeartbeatAckAt;
    if (sinceAck > 45000) {
      state.room.socket.close();
      return;
    }
    state.room.socket.send(JSON.stringify({ type: 'heartbeat', payload: { client_time_ms: Date.now() } }));
  }, 12000);
}

function stopRoomHeartbeat() {
  if (state.room.heartbeatTimer) clearInterval(state.room.heartbeatTimer);
  state.room.heartbeatTimer = null;
}

function scheduleRoomReconnect() {
  if (state.room.reconnectTimer || !state.room.code || !state.room.joinProfile) return;
  state.room.reconnecting = true;
  const delay = Math.min(30000, 1000 * 2 ** Math.min(state.room.reconnectAttempts, 5));
  state.room.reconnectTimer = setTimeout(async () => {
    state.room.reconnectTimer = null;
    state.room.reconnectAttempts += 1;
    try {
      await connectRoom(state.room.code, state.room.joinProfile);
      state.room.reconnectAttempts = 0;
      state.room.reconnecting = false;
      setStatus(`房间 ${state.room.code} 已重连`);
    } catch (err) {
      console.error(err);
      setStatus('房间连接中断，正在重试...');
      scheduleRoomReconnect();
    } finally {
      renderRoomPanel();
    }
  }, delay);
  renderRoomPanel();
}

async function handleRoomSocketMessage(event) {
  const message = JSON.parse(event.data);
  if (message.type === 'heartbeat_ack') {
    state.room.lastHeartbeatAckAt = Date.now();
    return;
  }
  if (message.type === 'room_snapshot') {
    state.room.connected = true;
    state.room.reconnecting = false;
    state.room.reconnectAttempts = 0;
    state.room.clientId = message.client_id;
    startRoomHeartbeat();
    await applyRoomSnapshot(message.room, message.client_id);
    setStatus(`房间 ${state.room.code} 已连接`);
    return;
  }
  if (message.type === 'participant_update') {
    state.room.participants = message.participants || {};
    renderRoomPanel();
    return;
  }
  if (message.type === 'cursor') {
    applyRemoteCursor(message.client_id, message.payload);
    return;
  }
  if (message.type === 'state_update') {
    await applyRoomStateUpdate(message);
  }
}

function isOwnRoomEcho(message) {
  return message.client_id && state.room.clientId && message.client_id === state.room.clientId;
}

async function applyRoomStateUpdate(message) {
  if (isOwnRoomEcho(message)) {
    renderRoomPanel();
    return;
  }
  const payload = message.payload || {};
  if (message.patch_type === 'playback_control' && state.sandbox) exitSandboxLocal();
  state.room.remoteApplying = true;
  try {
    if (payload.mode) {
      if (els.roomModeText) els.roomModeText.textContent = payload.mode;
    }
    if (message.patch_type === 'switch_demo' && payload.demo_id) {
      await loadDemoReplay(payload.demo_id, { roundNumber: payload.playback?.round_number, tick: payload.playback?.tick, suppressRoomSwitch: true });
    }
    if (payload.playback) {
      const playback = payload.playback;
      await withSuppressedRoomBroadcastAsync(async () => {
        if (Number(playback.round_number) !== Number(state.currentRound)) await switchToRound(Number(playback.round_number), { tick: playback.tick, suppressBroadcast: true });
        else if (playback.tick !== undefined) seekToTick(Number(playback.tick), { suppressBroadcast: true });
        if (playback.is_playing) play({ suppressBroadcast: true });
        else pause({ suppressBroadcast: true });
      });
    }
    if (message.patch_type === 'enter_sandbox' && payload.sandbox) {
      const sandboxRound = Number(payload.sandbox.source_round_number ?? payload.sandbox.round);
      if (Number.isFinite(sandboxRound) && sandboxRound !== Number(state.currentRound)) {
        await switchToRound(sandboxRound, { tick: payload.sandbox.source_tick, suppressBroadcast: true });
      }
      applyRoomSandbox(payload.sandbox);
    } else if (payload.sandbox && message.patch_type !== 'reset_sandbox_to_source') {
      applyRoomSandbox(payload.sandbox);
    }
    if (message.patch_type === 'resume_replay') {
      exitSandboxLocal();
      if (payload.playback) await switchToRound(Number(payload.playback.round_number), { tick: payload.playback.tick, autoplay: payload.playback.is_playing, suppressBroadcast: true });
    }
    if (message.patch_type === 'move_token') applyRemoteTokenMove(payload);
    if (message.patch_type === 'create_object') appendRemoteObject(payload.object);
    if (message.patch_type === 'delete_object') deleteRemoteObject(payload.object_id);
    if (message.patch_type === 'create_utility') appendRemoteUtility(payload.utility, payload.currentTick, payload.nextUtilityThrowTick);
    if (message.patch_type === 'clear_utilities' && state.sandbox) {
      state.sandbox.planned_utilities = [];
      state.sandbox.nextUtilityThrowTick = payload.nextUtilityThrowTick ?? state.sandbox.source_tick;
      state.selectedUtility = null;
    }
    if (message.patch_type === 'reset_sandbox_to_source' && payload.sandbox) applyRoomSandbox(payload.sandbox);
    if (message.patch_type === 'sandbox_time_control' && state.sandbox) {
      if (payload.currentTick !== undefined) state.sandbox.currentTick = payload.currentTick;
      if (payload.playing && !state.sandbox.playing) playSandbox({ suppressBroadcast: true });
      else if (!payload.playing) stopSandboxPlayback({ suppressBroadcast: true });
    }
    renderRoomPanel();
    renderSideLists();
    renderUtilityDetail();
    updateSandboxButtons();
    updateNavigationButtons();
    draw();
  } finally {
    state.room.remoteApplying = false;
  }
}

function disconnectRoom(options = {}) {
  state.room.intentionalClose = true;
  resetRoomConnectionTimers();
  if (state.room.socket) {
    state.room.socket.intentionalClose = true;
    state.room.socket.close();
  }
  state.room.socket = null;
  state.room.connected = false;
  state.room.clientId = null;
  state.room.participants = {};
  state.room.joinProfile = null;
  state.room.intentionalClose = false;
  if (!options.keepUrl && state.room.code) history.replaceState(null, '', '/');
  const currentCode = state.room.code;
  if (!options.keepMetadata) {
    state.room.shareUrl = null;
    state.room.publicReady = false;
    state.room.shareMode = 'local';
    state.room.warning = null;
    state.room.pendingJoin = null;
  }
  state.room.code = options.keepMetadata ? currentCode : null;
  renderRoomPanel();
}

function leaveRoom() {
  disconnectRoom();
  closeJoinRoomModal();
  closeShareRoomModal();
  setStatus('已离开房间');
}

async function copyRoomLink() {
  if (!state.room.code) return;
  const url = state.room.shareUrl || `${window.location.origin}${canonicalRoomPath(state.room.code)}`;
  await navigator.clipboard.writeText(url);
  setStatus(state.room.publicReady ? '公网房间链接已复制' : '本地房间链接已复制，但队友无法通过公网加入');
}

function openShareRoomModal() {
  if (!state.room.code || !els.shareRoomModal) return;
  els.shareRoomTitle.textContent = state.room.publicReady ? '房间已创建' : '房间已创建，但当前不是公网链接';
  els.shareRoomMessage.textContent = state.room.publicReady ? '复制下面的公网 HTTPS 链接给队友即可加入。' : '当前链接只适合本机调试，队友不能通过公网打开。';
  els.shareRoomCodeInput.value = state.room.code || '';
  els.shareRoomUrlInput.value = state.room.shareUrl || `${window.location.origin}${canonicalRoomPath(state.room.code)}`;
  els.shareRoomWarning.hidden = state.room.publicReady;
  els.shareRoomWarning.textContent = state.room.warning || '请使用 --tunnel cloudflared 或设置 CS2PLUGIN_PUBLIC_BASE_URL 后再分享给队友。';
  els.shareRoomModal.hidden = false;
}

function closeShareRoomModal() {
  if (els.shareRoomModal) els.shareRoomModal.hidden = true;
}

function openJoinRoomModal(room) {
  if (!room || !els.joinRoomModal) return;
  state.room.pendingJoin = room;
  const profile = storedJoinProfile();
  els.joinRoomTitle.textContent = '加入房间';
  els.joinRoomMessage.textContent = `你正在加入房间：${room.title || room.room_code}`;
  els.joinDisplayNameInput.value = profile.display_name || '';
  fillJoinRoleOptions(profile);
  els.joinRoomWarning.hidden = !state.room.warning;
  els.joinRoomWarning.textContent = state.room.warning || '';
  els.joinRoomModal.hidden = false;
  setTimeout(() => els.joinDisplayNameInput?.focus(), 0);
}

function closeJoinRoomModal() {
  if (els.joinRoomModal) els.joinRoomModal.hidden = true;
}

function fillJoinRoleOptions(profile = {}) {
  if (!els.joinRoleSelect) return;
  els.joinRoleSelect.innerHTML = '';
  const viewer = document.createElement('option');
  viewer.value = 'viewer:';
  viewer.textContent = '旁观者';
  els.joinRoleSelect.appendChild(viewer);
  for (const player of state.manifest?.players || []) {
    const playerId = String(player.steamid || player.name || '');
    if (!playerId) continue;
    const option = document.createElement('option');
    option.value = `player:${encodeURIComponent(playerId)}`;
    option.textContent = player.name || playerId;
    els.joinRoleSelect.appendChild(option);
  }
  const selected = profile.role === 'player' && profile.assigned_player_id ? `player:${encodeURIComponent(profile.assigned_player_id)}` : 'viewer:';
  els.joinRoleSelect.value = selected;
}

function joinProfileFromModal() {
  const rawName = els.joinDisplayNameInput?.value?.trim() || `User ${Math.floor(Math.random() * 1000)}`;
  const [role, encodedPlayerId] = String(els.joinRoleSelect?.value || 'viewer:').split(':');
  const assignedPlayerId = encodedPlayerId ? decodeURIComponent(encodedPlayerId) : '';
  return {
    display_name: rawName.slice(0, 40),
    role: role || 'viewer',
    assigned_player_id: assignedPlayerId || null,
  };
}

async function enterCreatedRoom() {
  if (!state.room.code) return;
  closeShareRoomModal();
  openJoinRoomModal(state.room.pendingSnapshot || { room_code: state.room.code, title: state.room.code });
}

async function confirmJoinRoom() {
  if (!state.room.code) return;
  if (els.confirmJoinRoomBtn) els.confirmJoinRoomBtn.disabled = true;
  const profile = joinProfileFromModal();
  saveJoinProfile(profile);
  try {
    await connectRoom(state.room.code, profile);
    closeJoinRoomModal();
    history.replaceState(null, '', canonicalRoomPath(state.room.code));
    setBottomTab('room');
  } catch (err) {
    console.error(err);
    if (els.joinRoomWarning) {
      els.joinRoomWarning.hidden = false;
      els.joinRoomWarning.textContent = '房间连接失败。可能是公网隧道不支持 WebSocket，或服务已停止。';
    }
    setStatus(`房间连接失败：${err.message}`);
  } finally {
    if (els.confirmJoinRoomBtn) els.confirmJoinRoomBtn.disabled = false;
  }
}

function cancelJoinRoom() {
  closeJoinRoomModal();
  disconnectRoom();
  setStatus('已返回本地模式');
}

function sendRoomMessage(type, payload = {}) {
  if (!isRoomMode() || state.room.suppressBroadcast || state.room.remoteApplying) return;
  if (state.room.socket.readyState !== WebSocket.OPEN) return;
  state.room.socket.send(JSON.stringify({ type, payload }));
}

function withSuppressedRoomBroadcast(fn) {
  state.room.suppressBroadcast = true;
  try {
    return fn();
  } finally {
    state.room.suppressBroadcast = false;
  }
}

async function withSuppressedRoomBroadcastAsync(fn) {
  state.room.suppressBroadcast = true;
  try {
    return await fn();
  } finally {
    state.room.suppressBroadcast = false;
  }
}

function renderRoomPanel() {
  const participants = Object.values(state.room.participants || {});
  const online = participants.filter(participant => participant.online).length;
  const connectionText = state.room.connected ? '已连接' : state.room.reconnecting ? '重连中' : '未连接';
  if (els.roomBar) els.roomBar.hidden = !state.room.code;
  if (els.roomCodeText) els.roomCodeText.textContent = state.room.code || '-';
  if (els.roomParticipantsText) els.roomParticipantsText.textContent = `${online}/5`;
  if (els.roomModeText) els.roomModeText.textContent = state.sandbox ? 'Sandbox' : 'Replay';
  if (els.roomStatusText) els.roomStatusText.textContent = state.room.code ? `房间 ${state.room.code} · ${connectionText} · 在线 ${online}/5` : '未加入房间。';
  if (els.roomParticipantsList) {
    els.roomParticipantsList.innerHTML = '';
    for (const participant of participants) {
      const item = document.createElement('div');
      item.className = 'compact-list-item';
      item.innerHTML = `<strong>${escapeHtml(participant.display_name || participant.client_id || '-')}</strong><span>${participant.online ? 'online' : 'offline'} · ${participant.role || 'player'}</span>`;
      els.roomParticipantsList.appendChild(item);
    }
  }
}

function broadcastPlaybackState(overrides = {}) {
  if (!state.currentRound || state.currentTick === null || state.sandbox) return;
  sendRoomMessage('playback_control', {
    round_number: state.currentRound,
    tick: state.currentTick,
    is_playing: state.playing,
    ...overrides,
  });
}

function applyRoomSandbox(sandbox) {
  if (!sandbox) return;
  stopSandboxPlayback({ suppressBroadcast: true });
  state.sandbox = {
    schema_version: sandbox.schema_version || 1,
    demo_id: sandbox.demo_id || state.demoId,
    source_match_id: sandbox.source_match_id || state.demoId,
    source_round_number: sandbox.source_round_number ?? sandbox.round ?? state.currentRound,
    source_tick: sandbox.source_tick ?? sandbox.currentTick ?? state.currentTick,
    source_frame_index: sandbox.source_frame_index ?? state.frameIndex,
    created_at: sandbox.created_at || new Date().toISOString(),
    dirty: false,
    round: sandbox.round ?? sandbox.source_round_number ?? state.currentRound,
    currentTick: sandbox.currentTick ?? sandbox.source_tick ?? state.currentTick,
    nextUtilityThrowTick: sandbox.nextUtilityThrowTick ?? sandbox.next_utility_throw_tick ?? sandbox.nextUtilityTick ?? null,
    playing: false,
    playStartTime: 0,
    playStartTick: sandbox.currentTick ?? sandbox.source_tick ?? state.currentTick,
    rafId: null,
    mode: 'idle',
    selectedThrower: null,
    selectedThrowerId: null,
    selectedUtilityType: null,
    menuAnchor: null,
    awaitingUtilityLanding: false,
    tokens: JSON.parse(JSON.stringify(sandbox.tokens || sandbox.token_positions || [])),
    annotations: normalizedAnnotations(JSON.parse(JSON.stringify(sandbox.annotations || []))),
    planned_utilities: (sandbox.planned_utilities || []).map(utility => normalizeUtilityEvent(utility, 'sandbox')),
  };
  state.activeMapTool = 'move';
  if (sandbox.playing) playSandbox({ suppressBroadcast: true });
}

function exitSandboxLocal() {
  if (!state.sandbox) return;
  stopSandboxPlayback({ suppressBroadcast: true });
  closeUtilityMenu();
  state.sandbox = null;
  state.drag = null;
  state.arrowDraft = null;
  state.brushDraft = null;
  state.laserPoint = null;
  state.remoteCursors.clear();
  state.selectedUtility = null;
  state.activeMapTool = 'select';
  renderUtilityDetail();
  updateSandboxButtons();
  updateNavigationButtons();
  updateMapToolbar();
  renderSideLists();
  draw();
}

function applyRemoteTokenMove(payload) {
  if (!state.sandbox || !payload) return;
  const tokenId = String(payload.token_id || payload.steamid || payload.id || '');
  const token = (state.sandbox.tokens || []).find(item => String(item.steamid || item.id || item.name) === tokenId);
  if (!token) return;
  if (payload.radar_x !== undefined) token.radar_x = payload.radar_x;
  if (payload.radar_y !== undefined) token.radar_y = payload.radar_y;
  if (payload.currentTick !== undefined) state.sandbox.currentTick = payload.currentTick;
}

function annotationId(prefix = 'ann') {
  return `${prefix}_${Date.now()}_${Math.floor(Math.random() * 100000)}`;
}

function normalizeAnnotation(annotation) {
  if (!annotation || typeof annotation !== 'object') return null;
  return {
    ...annotation,
    id: annotation.id || annotation.annotation_id || annotationId(annotation.type || 'ann'),
  };
}

function normalizedAnnotations(annotations) {
  return (annotations || []).map(normalizeAnnotation).filter(Boolean);
}

function appendRemoteObject(object) {
  if (!state.sandbox || !object) return;
  const normalized = normalizeAnnotation(object);
  if (!normalized) return;
  state.sandbox.annotations.push(normalized);
}

function deleteRemoteObject(objectId) {
  if (!state.sandbox || !objectId) return;
  state.sandbox.annotations = (state.sandbox.annotations || []).filter(annotation => annotation.id !== objectId);
}

function applyRemoteCursor(clientId, payload = {}) {
  if (!clientId || clientId === state.room.clientId || payload.tool !== 'laser') return;
  const x = Number(payload.radar_x);
  const y = Number(payload.radar_y);
  if (!Number.isFinite(x) || !Number.isFinite(y)) return;
  state.remoteCursors.set(clientId, { x, y, displayName: payload.display_name || clientId, updatedAt: performance.now() });
  draw();
}

function appendRemoteUtility(utility, currentTickValue, nextUtilityThrowTick) {
  if (!state.sandbox || !utility) return;
  state.sandbox.planned_utilities.push(normalizeUtilityEvent(utility, 'sandbox'));
  if (currentTickValue !== undefined && state.sandbox.playing) state.sandbox.currentTick = currentTickValue;
  state.sandbox.nextUtilityThrowTick = nextUtilityThrowTick ?? utility.detonate_tick ?? sandboxUtilityPlanningTick(state.sandbox);
}

function roomTokenPayload(token) {
  return {
    token_id: String(token?.steamid || token?.id || token?.name || ''),
    radar_x: token?.radar_x,
    radar_y: token?.radar_y,
    currentTick: state.sandbox?.currentTick,
  };
}

function broadcastSandboxTime() {
  if (!state.sandbox) return;
  sendRoomMessage('sandbox_time_control', {
    currentTick: state.sandbox.currentTick,
    playing: Boolean(state.sandbox.playing),
  });
}

function buildReplayIndex(manifest) {
  const rounds = manifest?.rounds || [];
  const roundsByNumber = new Map();
  const roundPositionByNumber = new Map();
  const tickRangeByRound = new Map();
  const findingsByRound = new Map();
  const markersByRound = new Map();
  const utilitiesByRound = new Map();
  const roundNumbers = rounds.map(round => Number(round.round)).filter(Number.isFinite);

  rounds.forEach((round, idx) => {
    const roundNumber = Number(round.round);
    if (!Number.isFinite(roundNumber)) return;
    roundsByNumber.set(roundNumber, round);
    roundPositionByNumber.set(roundNumber, idx);
    tickRangeByRound.set(roundNumber, { startTick: toFiniteNumber(round.start_tick), endTick: toFiniteNumber(round.end_tick) });
  });
  for (const finding of manifest?.findings || []) {
    const roundNumber = Number(finding.round_number);
    if (!Number.isFinite(roundNumber)) continue;
    pushIndex(findingsByRound, roundNumber, finding);
  }
  for (const marker of manifest?.markers || []) {
    const roundNumber = Number(marker.round_number);
    if (!Number.isFinite(roundNumber)) continue;
    pushIndex(markersByRound, roundNumber, marker);
  }
  for (const utility of manifest?.utility_events || []) {
    const normalized = normalizeUtilityEvent(utility, 'demo');
    const roundNumber = Number(normalized.round_number);
    if (!Number.isFinite(roundNumber)) continue;
    pushIndex(utilitiesByRound, roundNumber, normalized);
  }
  return {
    roundsByNumber,
    roundNumbers,
    roundPositionByNumber,
    tickRangeByRound,
    findingsByRound,
    markersByRound,
    utilitiesByRound,
    tickRate: getManifestTickRate(manifest),
  };
}

function pushIndex(index, key, value) {
  if (!index.has(key)) index.set(key, []);
  index.get(key).push(value);
}

function getManifestTickRate(manifest) {
  const rate = Number(manifest?.match?.metrics?.metadata?.tick_rate);
  return Number.isFinite(rate) && rate > 0 ? rate : 64;
}

function getTickRate() {
  return state.replayIndex?.tickRate || 64;
}

function secondsToTicks(seconds) {
  return Math.round(seconds * getTickRate());
}

function normalizeUtilityEvent(raw, source = 'demo') {
  const type = raw?.type === 'incgrenade' ? 'molotov' : raw?.type;
  const effect = { ...(raw?.effect || {}) };
  const detonatePos = raw?.radar_detonate_pos || effect.radar_pos || raw?.detonate_radar_pos;
  const throwPos = raw?.radar_throw_pos || raw?.throw_radar_pos;
  effect.radar_pos = effect.radar_pos || detonatePos;
  effect.start_tick = toFiniteNumber(effect.start_tick) ?? toFiniteNumber(raw?.detonate_tick);
  effect.end_tick = toFiniteNumber(effect.end_tick) ?? toFiniteNumber(raw?.expire_tick);
  effect.blinded_players = effect.blinded_players || effect.target_players || [];
  effect.target_players = effect.target_players || effect.blinded_players;
  effect.damaged_players = effect.damaged_players || [];
  return {
    ...raw,
    source: raw?.source || source,
    type,
    thrower_player_id: raw?.thrower_player_id || raw?.thrower_steamid,
    radar_throw_pos: throwPos,
    radar_detonate_pos: detonatePos,
    approximate_trajectory: Boolean(raw?.approximate_trajectory),
    effect,
  };
}

function getUtilityConfig(type) {
  const normalizedType = type === 'incgrenade' ? 'molotov' : type;
  return { ...(defaultUtilityEffects[normalizedType] || {}), ...(state.manifest?.utility_effects?.[normalizedType] || {}) };
}

function effectRadiusToRadarPixels(gameUnitsRadius) {
  const radius = Number(gameUnitsRadius);
  const scale = Number(state.manifest?.map?.scale);
  if (!Number.isFinite(radius)) return 80;
  return Number.isFinite(scale) && scale > 0 ? radius / scale : radius;
}

function getUtilityEffectWindow(utility) {
  const cfg = getUtilityConfig(utility.type);
  const effect = utility.effect || {};
  const startTick = toFiniteNumber(effect.start_tick) ?? toFiniteNumber(utility.detonate_tick) ?? toFiniteNumber(utility.throw_tick);
  let endTick = toFiniteNumber(effect.end_tick) ?? toFiniteNumber(utility.expire_tick);
  if (Number.isFinite(startTick) && Number.isFinite(endTick)) {
    const maxDuration = toFiniteNumber(cfg.max_duration_sec);
    if (endTick <= startTick || (maxDuration !== null && endTick - startTick > secondsToTicks(maxDuration))) endTick = null;
  }
  if (!Number.isFinite(endTick) && Number.isFinite(startTick)) {
    if (utility.type === 'flashbang') endTick = startTick + secondsToTicks(cfg.flash_visual_duration_sec ?? 0.8);
    else if (utility.type === 'hegrenade') endTick = startTick + secondsToTicks(Math.max(Number(cfg.blast_visual_duration_sec || 0.7), Number(cfg.smoke_visual_duration_sec || 2.5)));
    else endTick = startTick + secondsToTicks(cfg.duration_sec ?? 1);
  }
  return {
    startTick,
    endTick,
    fadeInTicks: toFiniteNumber(effect.fade_in_ticks) ?? secondsToTicks(cfg.fade_in_sec ?? 0),
    fadeOutTicks: toFiniteNumber(effect.fade_out_ticks) ?? secondsToTicks(cfg.fade_out_sec ?? 0),
  };
}

function getUtilityOpacityByTick(utility, tick) {
  const window = getUtilityEffectWindow(utility);
  if (!Number.isFinite(window.startTick) || !Number.isFinite(window.endTick) || tick < window.startTick || tick > window.endTick) return 0;
  if (window.fadeInTicks > 0 && tick < window.startTick + window.fadeInTicks) return Math.max(0, Math.min(1, (tick - window.startTick) / window.fadeInTicks));
  if (window.fadeOutTicks > 0 && tick > window.endTick - window.fadeOutTicks) return Math.max(0, Math.min(1, (window.endTick - tick) / window.fadeOutTicks));
  return 1;
}

function sandboxUtilityPlanningTick(sandbox) {
  if (!sandbox) return null;
  const explicitTick = toFiniteNumber(sandbox.nextUtilityThrowTick ?? sandbox.next_utility_throw_tick);
  if (Number.isFinite(explicitTick)) return explicitTick;
  const utilityTicks = (sandbox.planned_utilities || [])
    .map(utility => toFiniteNumber(utility.detonate_tick) ?? toFiniteNumber(utility.throw_tick))
    .filter(Number.isFinite);
  if (utilityTicks.length) return Math.max(...utilityTicks);
  return toFiniteNumber(sandbox.source_tick) ?? toFiniteNumber(sandbox.currentTick) ?? toFiniteNumber(state.currentTick);
}

function isPausedSandboxUtility(utility) {
  return Boolean(state.sandbox && !state.sandbox.playing && utility?.source === 'sandbox');
}

function loadRadarImage(url) {
  return new Promise((resolve, reject) => {
    state.radarImage.onload = resolve;
    state.radarImage.onerror = reject;
    state.radarImage.src = url;
  });
}

function fillRounds() {
  els.roundSelect.innerHTML = '';
  for (const round of state.manifest.rounds) {
    const opt = document.createElement('option');
    opt.value = round.round;
    opt.textContent = `Round ${round.round} (${round.winner_side || '-'} win)`;
    els.roundSelect.appendChild(opt);
  }
}

async function loadRoundData(roundNumber) {
  if (state.roundCache.has(roundNumber)) return state.roundCache.get(roundNumber).roundData;
  const roundData = await api(`/api/demos/${state.demoId}/rounds/${roundNumber}`);
  roundData.utility_events = (roundData.utility_events || []).map(utility => normalizeUtilityEvent(utility, 'demo'));
  const frames = roundData.frames || [];
  const ticks = frames.map(frame => Number(frame.tick));
  const frameIndexByTick = new Map();
  ticks.forEach((tick, idx) => frameIndexByTick.set(tick, idx));
  mergeRoundShardIndex(roundNumber, roundData);
  state.roundCache.set(roundNumber, { roundData, ticks, frameIndexByTick });
  return roundData;
}

function mergeRoundShardIndex(roundNumber, roundData) {
  if (!state.replayIndex) return;
  const key = Number(roundNumber);
  if (Array.isArray(roundData.markers)) state.replayIndex.markersByRound.set(key, roundData.markers);
  if (Array.isArray(roundData.utility_events)) state.replayIndex.utilitiesByRound.set(key, roundData.utility_events);
}

function getRoundRange(roundNumber) {
  const indexed = state.replayIndex?.tickRangeByRound.get(Number(roundNumber));
  const cached = state.roundCache.get(Number(roundNumber))?.roundData;
  const frames = cached?.frames || [];
  let startTick = indexed?.startTick;
  let endTick = indexed?.endTick;
  if (!Number.isFinite(startTick)) startTick = toFiniteNumber(cached?.start_tick) ?? toFiniteNumber(frames[0]?.tick);
  if (!Number.isFinite(endTick)) endTick = toFiniteNumber(cached?.end_tick) ?? toFiniteNumber(frames[frames.length - 1]?.tick);
  return { startTick, endTick };
}

async function switchToRound(roundNumber, options = {}) {
  const targetRound = Number(roundNumber);
  if (!state.replayIndex?.roundsByNumber.has(targetRound)) return false;
  if (!confirmExitSandbox()) {
    if (state.currentRound !== null) els.roundSelect.value = String(state.currentRound);
    return false;
  }

  const autoplay = options.autoplay === true;
  const keepFinding = options.keepFinding === true;
  pause({ redraw: false });
  const seq = ++state.roundLoadSeq;
  setStatus(`加载 Round ${targetRound}...`);
  try {
    const roundData = await loadRoundData(targetRound);
    if (seq !== state.roundLoadSeq) return false;
    state.roundData = roundData;
    state.currentRound = targetRound;
    state.selectedUtility = null;
    state.selectedPlayerId = null;
    buildPlayerSideCache(roundData.frames || []);
    state.yawCacheBySteamid.clear();
    state.yawUnit = inferYawUnit(roundData.frames || []);
    if (!keepFinding) state.activeFindingId = null;
    const range = getRoundRange(targetRound);
    let targetTick = options.tick ?? null;
    if (targetTick === null || targetTick === undefined) {
      targetTick = options.at === 'end' ? range.endTick : range.startTick;
    }
    if (!Number.isFinite(Number(targetTick))) targetTick = roundData.frames?.[0]?.tick ?? 0;
    state.currentTick = clampTick(Number(targetTick), targetRound);
    state.frameIndex = getNearestFrameIndex(targetRound, state.currentTick);
    els.timeline.min = 0;
    els.timeline.max = Math.max(0, (roundData.frames || []).length - 1);
    updateViewStateFromTick(targetRound, state.currentTick);
    setStatus('已加载');
    if (autoplay) play({ suppressBroadcast: options.suppressBroadcast });
    if (!options.suppressBroadcast) broadcastPlaybackState({ round_number: targetRound, tick: state.currentTick, is_playing: autoplay });
    return true;
  } catch (err) {
    console.error(err);
    setStatus(`切换回合失败：${err.message}`);
    return false;
  }
}

function confirmExitSandbox() {
  if (!state.sandbox) return true;
  if (state.sandbox.dirty && !confirm('切换回合会退出当前推演，未保存修改会丢失，是否继续？')) return false;
  stopSandboxPlayback();
  closeUtilityMenu();
  state.sandbox = null;
  state.drag = null;
  state.arrowDraft = null;
  state.brushDraft = null;
  state.laserPoint = null;
  state.remoteCursors.clear();
  state.activeMapTool = 'select';
  updateSandboxButtons();
  updateMapToolbar();
  renderSideLists();
  return true;
}

function previousRound() {
  if (!state.replayIndex || state.currentRound === null) return;
  const pos = state.replayIndex.roundPositionByNumber.get(state.currentRound);
  if (pos === undefined || pos <= 0) return;
  switchToRound(state.replayIndex.roundNumbers[pos - 1]);
}

function nextRound() {
  if (!state.replayIndex || state.currentRound === null) return;
  const pos = state.replayIndex.roundPositionByNumber.get(state.currentRound);
  if (pos === undefined || pos >= state.replayIndex.roundNumbers.length - 1) return;
  switchToRound(state.replayIndex.roundNumbers[pos + 1]);
}

function seekBySeconds(deltaSeconds) {
  if (!state.roundData || state.currentTick === null || state.sandbox) return;
  pause({ redraw: false });
  seekToTick(state.currentTick + secondsToTicks(deltaSeconds));
}

function seekToTick(targetTick, options = {}) {
  if (!state.roundData || state.currentRound === null) return;
  const keepPlaying = options.keepPlaying === true;
  const tick = options.clampToRound === false ? Number(targetTick) : clampTick(Number(targetTick), state.currentRound);
  state.currentTick = tick;
  state.frameIndex = getNearestFrameIndex(state.currentRound, tick);
  updateViewStateFromTick(state.currentRound, tick, { skipDraw: true, lightweight: keepPlaying });
  if (!keepPlaying) draw();
  if (!keepPlaying && !options.suppressBroadcast) broadcastPlaybackState({ tick, is_playing: state.playing });
}

function updateViewStateFromTick(roundNumber, tick, options = {}) {
  els.timeline.value = String(state.frameIndex);
  els.roundSelect.value = String(roundNumber);
  if (!options.lightweight) {
    renderMarkers();
    renderUtilityDetail();
    renderFindings();
    renderSideLists();
  }
  updateNavigationButtons();
  if (!options.skipDraw) draw();
}

function play(options = {}) {
  if (!state.roundData || state.sandbox || state.currentTick === null) return;
  pause({ redraw: false, suppressBroadcast: true });
  state.playing = true;
  state.playStartTime = performance.now();
  state.playStartTick = state.currentTick;
  updateNavigationButtons();
  state.rafId = requestAnimationFrame(loop);
  draw();
  if (!options.suppressBroadcast) broadcastPlaybackState({ is_playing: true });
}

function pause(options = {}) {
  const wasPlaying = state.playing;
  state.playing = false;
  if (state.rafId !== null) {
    cancelAnimationFrame(state.rafId);
    state.rafId = null;
  }
  updateNavigationButtons();
  if (options.redraw !== false) draw();
  if (wasPlaying && !options.suppressBroadcast) broadcastPlaybackState({ is_playing: false });
}

function loop(now) {
  if (!state.playing || !state.roundData || state.currentRound === null) return;
  const range = getRoundRange(state.currentRound);
  const elapsedSeconds = (now - state.playStartTime) / 1000;
  let targetTick = state.playStartTick + Math.floor(elapsedSeconds * getTickRate());
  if (Number.isFinite(range.endTick) && targetTick >= range.endTick) {
    targetTick = range.endTick;
    seekToTick(targetTick, { keepPlaying: true });
    pause({ redraw: true });
    return;
  }
  seekToTick(targetTick, { keepPlaying: true });
  draw();
  state.rafId = requestAnimationFrame(loop);
}

function seekFrame(index) {
  if (!state.roundData) return;
  const safeIndex = Math.max(0, Math.min(index, state.roundData.frames.length - 1));
  seekToTick(state.roundData.frames[safeIndex].tick);
}

function getNearestFrameIndex(roundNumber, tick) {
  const cache = state.roundCache.get(Number(roundNumber));
  const ticks = cache?.ticks || state.roundData?.frames?.map(frame => Number(frame.tick)) || [];
  if (!ticks.length) return 0;
  const target = Number(tick);
  if (!Number.isFinite(target)) return 0;
  let left = 0;
  let right = ticks.length - 1;
  while (left < right) {
    const mid = Math.floor((left + right) / 2);
    if (ticks[mid] < target) left = mid + 1;
    else right = mid;
  }
  const prev = Math.max(0, left - 1);
  return Math.abs(ticks[left] - target) < Math.abs(ticks[prev] - target) ? left : prev;
}

function buildPlayerSideCache(frames) {
  state.playerSideBySteamid = new Map();
  const counts = new Map();
  for (const frame of frames || []) {
    for (const player of frame.players || []) {
      const steamid = String(player.steamid || '');
      const team = normalizeSide(player.team);
      if (!steamid || !team) continue;
      if (!counts.has(steamid)) counts.set(steamid, { T: 0, CT: 0 });
      counts.get(steamid)[team] += 1;
    }
  }
  for (const [steamid, value] of counts.entries()) {
    state.playerSideBySteamid.set(steamid, value.T >= value.CT ? 'T' : 'CT');
  }
}

function getNearestFrame(roundNumber, tick) {
  const cache = state.roundCache.get(Number(roundNumber));
  const frames = cache?.roundData?.frames || state.roundData?.frames || [];
  return frames[getNearestFrameIndex(roundNumber, tick)] || null;
}

function getPlayerStatesAtTick(roundNumber, tick) {
  return getNearestFrame(roundNumber, tick)?.players || [];
}

async function jumpToFinding(finding) {
  state.activeFindingId = finding.finding_id;
  const round = Number(finding.round_number);
  const tick = Number(finding.jump_tick ?? finding.tick);
  if (round !== state.currentRound) await switchToRound(round, { tick, keepFinding: true });
  else seekToTick(tick);
  renderFindings();
}

function renderFindings() {
  els.findingsList.innerHTML = '';
  const findings = filteredFindings();
  for (const finding of findings) {
    const div = document.createElement('div');
    div.className = `finding-card ${finding.sentiment || ''} ${finding.finding_id === state.activeFindingId ? 'active' : ''}`;
    div.innerHTML = `
      <div class="finding-title">${escapeHtml(finding.title || finding.finding_type)}</div>
      <div class="finding-meta">R${finding.round_number} tick ${finding.jump_tick ?? finding.tick} · ${finding.team || '-'}</div>
      <div class="finding-message">${escapeHtml(finding.message || '')}</div>
    `;
    div.addEventListener('click', () => jumpToFinding(finding));
    els.findingsList.appendChild(div);
  }
}

function renderSideLists() {
  renderUtilitiesList();
  renderPlayersList();
  renderSandboxObjectsList();
}

function renderUtilitiesList() {
  if (!els.utilitiesList) return;
  els.utilitiesList.innerHTML = '';
  for (const utility of currentUtilities()) {
    const item = document.createElement('button');
    item.type = 'button';
    item.className = `compact-list-item ${utility.id === state.selectedUtility?.id ? 'active' : ''}`;
    item.innerHTML = `<strong>${escapeHtml(utilityLabel(utility.type))}</strong><span>R${utility.round_number ?? '-'} · ${utility.thrower || '-'} · tick ${utility.detonate_tick ?? utility.throw_tick ?? '-'}</span>`;
    item.addEventListener('click', () => {
      state.selectedUtility = utility;
      state.selectedPlayerId = null;
      if (Number.isFinite(Number(utility.detonate_tick))) seekToTick(Number(utility.detonate_tick));
      renderUtilityDetail();
      draw();
    });
    els.utilitiesList.appendChild(item);
  }
}

function renderPlayersList() {
  if (!els.playersList) return;
  els.playersList.innerHTML = '';
  const frame = currentFrame();
  for (const player of filteredPlayers(frame?.players || [])) {
    const item = document.createElement('button');
    item.type = 'button';
    item.className = `compact-list-item player ${player.team || ''}`;
    item.innerHTML = `<strong>${escapeHtml(player.name || player.steamid || '-')}</strong><span>${player.team || '-'} · HP ${player.health ?? '-'} · ${player.is_alive === false ? 'dead' : 'alive'}</span>`;
    item.addEventListener('click', () => {
      state.selectedPlayerId = String(player.steamid || player.name || '');
      state.selectedUtility = null;
      renderPlayerDetail(player);
      draw();
    });
    els.playersList.appendChild(item);
  }
}

function renderSandboxObjectsList() {
  if (!els.sandboxObjectsList) return;
  els.sandboxObjectsList.innerHTML = '';
  if (!state.sandbox) {
    els.sandboxObjectsList.textContent = '进入推演模式后显示 planned utility、箭头和文字。';
    return;
  }
  const objects = [
    ...(state.sandbox.planned_utilities || []).map(utility => ({ type: 'utility', label: utilityLabel(utility.type), detail: `tick ${utility.detonate_tick ?? '-'}`, ref: utility })),
    ...(state.sandbox.annotations || []).map((ann, idx) => ({ type: ann.type, label: ann.type === 'arrow' ? '箭头' : ann.type === 'brush' ? '画笔' : '文字', detail: ann.text || `${ann.points?.length || ''} #${idx + 1}`, ref: ann })),
  ];
  for (const object of objects) {
    const item = document.createElement('button');
    item.type = 'button';
    item.className = 'compact-list-item';
    item.innerHTML = `<strong>${escapeHtml(object.label)}</strong><span>${escapeHtml(object.detail)}</span>`;
    if (object.type === 'utility') {
      item.addEventListener('click', () => {
        state.selectedUtility = object.ref;
        renderUtilityDetail();
        draw();
      });
    } else {
      item.addEventListener('click', () => {
        state.selectedUtility = null;
        els.utilityDetail.textContent = `${object.label} · ${object.detail}`;
        draw();
      });
    }
    els.sandboxObjectsList.appendChild(item);
  }
}

function renderPlayerDetail(player) {
  els.utilityDetail.innerHTML = `
    <strong>${escapeHtml(player.name || player.steamid || '-')}</strong><br />
    阵营：${escapeHtml(player.team || '-')} · HP ${player.health ?? '-'} · ${player.is_alive === false ? 'dead' : 'alive'}<br />
    radar：${round2(Number(player.radar_x))}, ${round2(Number(player.radar_y))}<br />
    yaw：${player.yaw ?? '-'}
  `;
}

function renderMarkers() {
  markerCtx.clearRect(0, 0, els.markerCanvas.width, els.markerCanvas.height);
  markerCtx.fillStyle = '#0b1220';
  markerCtx.fillRect(0, 0, els.markerCanvas.width, els.markerCanvas.height);
  if (!state.manifest || !state.roundData || state.currentRound === null) return;
  const range = getRoundRange(state.currentRound);
  const start = range.startTick ?? state.roundData.start_tick ?? 0;
  const end = range.endTick ?? state.roundData.end_tick ?? start + 1;
  const span = Math.max(1, end - start);
  const markers = state.replayIndex?.markersByRound.get(Number(state.currentRound)) || [];
  for (const marker of markers) {
    if (marker.type?.startsWith('utility') && (!state.filters.showUtilities || !state.filters.types[marker.utility_type])) continue;
    if (!markerMatchesFilters(marker)) continue;
    const x = Math.max(0, Math.min(els.markerCanvas.width - 1, ((marker.tick - start) / span) * els.markerCanvas.width));
    markerCtx.strokeStyle = markerColor(marker);
    markerCtx.beginPath();
    markerCtx.moveTo(x, 4);
    markerCtx.lineTo(x, els.markerCanvas.height - 4);
    markerCtx.stroke();
  }
}

function markerColor(marker) {
  if (marker.type === 'kill') return '#ef4444';
  if (marker.type === 'finding') return '#a78bfa';
  if (marker.type?.startsWith('utility')) return utilityStyle[marker.utility_type]?.color || '#22c55e';
  return '#f59e0b';
}

function currentFrame() {
  if (!state.roundData) return null;
  return state.roundData.frames[state.frameIndex] || null;
}

function previousFrame() {
  if (!state.roundData || state.frameIndex <= 0) return null;
  return state.roundData.frames[state.frameIndex - 1] || null;
}

function currentTick() {
  return state.currentTick ?? currentFrame()?.tick ?? null;
}

function currentUtilities(options = {}) {
  if (!state.roundData || !state.filters.showUtilities) return [];
  const utilities = (state.roundData.utility_events || []).filter(utility => state.filters.types[utility.type] !== false);
  return options.forOverlay ? utilities : filteredUtilities(utilities);
}

function refreshAnalysisFilterViews() {
  renderFindings();
  renderSideLists();
  renderMarkers();
  draw();
}

function clearAnalysisFilters() {
  state.analysisFilters.side = 'all';
  state.analysisFilters.playerId = 'all';
  state.analysisFilters.severity = 'all';
  state.analysisFilters.visualMode = 'highlight';
  for (const key of Object.keys(state.analysisFilters.findingTypes)) state.analysisFilters.findingTypes[key] = true;
  if (els.filterSide) els.filterSide.value = 'all';
  if (els.filterPlayer) els.filterPlayer.value = 'all';
  if (els.filterSeverity) els.filterSeverity.value = 'all';
  if (els.filterVisualMode) els.filterVisualMode.value = 'highlight';
  for (const input of els.findingTypeFilters || []) input.checked = true;
  refreshAnalysisFilterViews();
}

function refreshPlayerFilterOptions() {
  if (!els.filterPlayer) return;
  const selected = state.analysisFilters.playerId;
  const players = new Map();
  for (const player of state.manifest?.players || []) {
    const key = normalizePlayerKey(player.steamid || player.name);
    if (key) players.set(key, player.name || player.steamid || key);
  }
  els.filterPlayer.innerHTML = '<option value="all">全部</option>';
  for (const [key, label] of players.entries()) {
    const option = document.createElement('option');
    option.value = key;
    option.textContent = label;
    if (key === selected) option.selected = true;
    els.filterPlayer.appendChild(option);
  }
}

function filteredFindings() {
  return (state.manifest?.findings || []).filter(matchesFindingFilter);
}

function filteredUtilities(utilities) {
  return (utilities || []).filter(matchesUtilityFilter);
}

function filteredPlayers(players) {
  return (players || []).filter(player => analysisItemDisplay(player, 'player').visibleInList);
}

function normalizePlayerKey(value) {
  const text = String(value ?? '').trim();
  return text || null;
}

function findingTypeAliases(type) {
  const normalized = String(type || '').toLowerCase();
  const aliases = new Set([normalized]);
  if (normalized.includes('trade')) aliases.add('trade_failure').add('trade_fail');
  if (normalized.includes('entry') && normalized.includes('success')) aliases.add('entry_success');
  if (normalized.includes('entry') && (normalized.includes('fail') || normalized.includes('failure'))) aliases.add('entry_failure').add('entry_failed');
  if (normalized.includes('stall')) aliases.add('stall');
  if (normalized.includes('postplant') || normalized.includes('post_plant')) aliases.add('postplant_loss').add('postplant');
  return aliases;
}

function findingPlayerKeys(finding) {
  const keys = new Set();
  for (const player of finding.players || []) {
    if (typeof player === 'object') {
      const key = normalizePlayerKey(player.steamid || player.player_id || player.name);
      if (key) keys.add(key);
    } else {
      const key = normalizePlayerKey(player);
      if (key) keys.add(key);
    }
  }
  const evidence = finding.evidence || {};
  for (const value of Object.values(evidence)) {
    if (typeof value === 'string' || typeof value === 'number') {
      const key = normalizePlayerKey(value);
      if (key) keys.add(key);
    }
  }
  return keys;
}

function findingSide(finding) {
  return normalizeSide(finding.team || finding.side);
}

function utilityPlayerKey(utility) {
  return normalizePlayerKey(utility.thrower_player_id || utility.thrower_steamid || utility.thrower);
}

function matchesSide(side) {
  return state.analysisFilters.side === 'all' || normalizeSide(side) === state.analysisFilters.side;
}

function playerAliasSet(playerOrKey) {
  const aliases = new Set();
  if (playerOrKey && typeof playerOrKey === 'object') {
    for (const value of [playerOrKey.steamid, playerOrKey.name, playerOrKey.player_id]) {
      const key = normalizePlayerKey(value);
      if (key) aliases.add(key);
    }
  } else {
    const key = normalizePlayerKey(playerOrKey);
    if (key) aliases.add(key);
  }
  return aliases;
}

function matchesPlayer(keySetOrKey) {
  const target = state.analysisFilters.playerId;
  if (target === 'all') return true;
  if (keySetOrKey instanceof Set) return keySetOrKey.has(target);
  if (keySetOrKey && typeof keySetOrKey === 'object') return playerAliasSet(keySetOrKey).has(target);
  return normalizePlayerKey(keySetOrKey) === target;
}

function matchesFindingFilter(finding) {
  if (!matchesSide(findingSide(finding))) return false;
  if (!matchesPlayer(findingPlayerKeys(finding))) return false;
  const severity = String(finding.severity || '').toLowerCase();
  if (state.analysisFilters.severity !== 'all' && severity !== state.analysisFilters.severity) return false;
  const aliases = findingTypeAliases(finding.finding_type);
  return Array.from(aliases).some(type => state.analysisFilters.findingTypes[type] !== false);
}

function matchesUtilityFilter(utility) {
  if (!matchesSide(resolveUtilitySide(utility))) return false;
  if (!matchesPlayer(utilityPlayerKey(utility))) return false;
  return true;
}

function markerMatchesFilters(marker) {
  if (marker.type === 'finding') {
    const findingId = marker.payload?.finding_id;
    const finding = (state.manifest?.findings || []).find(item => item.finding_id === findingId);
    return finding ? matchesFindingFilter(finding) : true;
  }
  if (marker.type?.startsWith('utility')) {
    const utilities = state.replayIndex?.utilitiesByRound.get(Number(marker.round_number)) || [];
    const utility = utilities.find(item => item.id === marker.utility_id || Number(item.detonate_tick ?? item.throw_tick) === Number(marker.tick));
    return utility ? matchesUtilityFilter(utility) : true;
  }
  return matchesSide(marker.team || marker.side);
}

function analysisItemDisplay(item, kind) {
  const mode = state.analysisFilters.visualMode;
  const matches = kind === 'utility' ? matchesUtilityFilter(item) : kind === 'player' ? (matchesSide(item.team || item.side) && matchesPlayer(item)) : true;
  if (matches) return { visible: true, visibleInList: true, alpha: 1, highlight: mode === 'highlight' && (state.analysisFilters.side !== 'all' || state.analysisFilters.playerId !== 'all') };
  if (mode === 'hide_others') return { visible: false, visibleInList: false, alpha: 0, highlight: false };
  if (mode === 'ghost_others') return { visible: true, visibleInList: false, alpha: 0.22, highlight: false };
  return { visible: true, visibleInList: false, alpha: 0.45, highlight: false };
}

function drawEmpty() {
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.fillStyle = '#0b0f15';
  ctx.fillRect(0, 0, els.canvas.width, els.canvas.height);
  ctx.fillStyle = '#9ca3af';
  ctx.font = '18px sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText('加载 demo 后显示 Dust2 radar replay', els.canvas.width / 2, els.canvas.height / 2);
  ctx.textAlign = 'start';
}

function draw() {
  if (!els.canvas || !ctx) return;
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.clearRect(0, 0, els.canvas.width, els.canvas.height);
  ctx.fillStyle = '#0b0f15';
  ctx.fillRect(0, 0, els.canvas.width, els.canvas.height);

  ctx.save();
  applyViewportTransform(ctx);
  if (state.radarImage.complete && state.radarImage.naturalWidth) {
    ctx.drawImage(state.radarImage, 0, 0, RADAR_SIZE, RADAR_SIZE);
  } else {
    ctx.fillStyle = '#111';
    ctx.fillRect(0, 0, RADAR_SIZE, RADAR_SIZE);
  }

  const tick = currentTick();
  if (!state.sandbox && tick !== null) {
    drawUtilityEvents(tick, currentUtilities({ forOverlay: true }));
  }

  const frame = currentFrame();
  if (state.sandbox) {
    drawSandbox();
  } else if (frame) {
    drawTokens(frame.players, false, tick, frame, previousFrame());
  }
  ctx.restore();

  updateStatusText(frame);
}

function updateStatusText(frame) {
  if (!frame || state.currentRound === null) {
    els.tickText.textContent = 'tick -';
    els.modeText.textContent = 'Replay';
    return;
  }
  const totalRounds = state.replayIndex?.roundNumbers.length || 0;
  const range = getRoundRange(state.currentRound);
  const displayTick = state.sandbox ? (state.sandbox.currentTick ?? frame.tick) : frame.tick;
  const roundSeconds = Number.isFinite(range.startTick) ? Math.max(0, (displayTick - range.startTick) / getTickRate()) : 0;
  els.tickText.textContent = `R${state.currentRound}/${totalRounds} · ${formatSeconds(roundSeconds)} · tick ${displayTick} · frame ${state.frameIndex + 1}/${state.roundData.frames.length}`;
  els.modeText.textContent = state.sandbox ? (state.sandbox.playing ? 'Sandbox / Playing' : 'Sandbox / Paused') : (state.playing ? 'Replay / Playing' : 'Replay / Paused');
}

function drawUtilityEvents(tick, utilities) {
  if (!state.filters.showUtilities) return;
  const effectsOnly = { ...state.filters, showUtilityTrajectories: false };
  const trajectoriesOnly = { ...state.filters, showUtilityEffects: false };
  for (const utility of utilities) drawUtilityEvent(ctx, utility, tick, effectsOnly);
  for (const utility of utilities) drawUtilityEvent(ctx, utility, tick, trajectoriesOnly);
}

function drawUtilityEvent(context, utility, tick, options) {
  if (!utility || options.types[utility.type] === false) return;
  const display = analysisItemDisplay(utility, 'utility');
  if (!display.visible) return;
  const pausedSandboxUtility = isPausedSandboxUtility(utility);
  context.save();
  context.globalAlpha *= display.alpha;
  if (options.showUtilityEffects && !pausedSandboxUtility) {
    if (utility.type === 'flashbang' && options.showFlashBurst) drawFlashBurst(context, utility, tick);
    if (utility.type === 'hegrenade' && options.showHeBlast) drawHeBlast(context, utility, tick);
    if (utility.type === 'smoke' && options.showSmokeRange) drawSmokeCloud(context, utility, tick);
    if (utility.type === 'molotov' && options.showMolotovRange) drawMolotovFire(context, utility, tick);
    if (utility.type === 'decoy') drawSimpleUtilityArea(context, utility, tick);
  }
  if (options.showUtilityTrajectories) drawUtilityTrajectory(context, utility, tick, { forceFull: pausedSandboxUtility });
  context.restore();
}

function drawFlashBurst(context, utility, tick) {
  const cfg = getUtilityConfig('flashbang');
  const start = toFiniteNumber(utility.detonate_tick) ?? getUtilityEffectWindow(utility).startTick;
  const duration = secondsToTicks(cfg.flash_visual_duration_sec ?? 0.8);
  if (!Number.isFinite(start) || duration <= 0 || tick < start || tick > start + duration) return;
  const pos = utility.effect?.radar_pos || utility.radar_detonate_pos;
  if (!pos) return;
  const t = (tick - start) / duration;
  const pulse = 0.75 + 0.25 * Math.sin(t * Math.PI * 6);
  const alpha = Math.max(0, (1 - t) * pulse);
  const coreRadius = effectRadiusToRadarPixels(cfg.flash_core_radius ?? 160);
  const fadeRadius = effectRadiusToRadarPixels(cfg.flash_fade_radius ?? 500);
  const radius = coreRadius + fadeRadius * t;
  const x = Number(pos.x);
  const y = Number(pos.y);
  if (!Number.isFinite(x) || !Number.isFinite(y)) return;
  context.save();
  const gradient = context.createRadialGradient(x, y, 0, x, y, radius);
  gradient.addColorStop(0, `rgba(255,255,255,${Math.min(0.95, alpha)})`);
  gradient.addColorStop(0.35, `rgba(255,255,255,${alpha * 0.45})`);
  gradient.addColorStop(1, 'rgba(255,255,255,0)');
  context.fillStyle = gradient;
  context.beginPath();
  context.arc(x, y, radius, 0, Math.PI * 2);
  context.fill();
  context.restore();
}

function drawHeBlast(context, utility, tick) {
  const cfg = getUtilityConfig('hegrenade');
  const start = toFiniteNumber(utility.detonate_tick) ?? getUtilityEffectWindow(utility).startTick;
  const blastTicks = secondsToTicks(cfg.blast_visual_duration_sec ?? 0.7);
  const smokeTicks = secondsToTicks(cfg.smoke_visual_duration_sec ?? 2.5);
  if (!Number.isFinite(start) || tick < start || tick > start + Math.max(blastTicks, smokeTicks)) return;
  const pos = utility.effect?.radar_pos || utility.radar_detonate_pos;
  const x = Number(pos?.x);
  const y = Number(pos?.y);
  if (!Number.isFinite(x) || !Number.isFinite(y)) return;
  const outer = effectRadiusToRadarPixels(utility.effect?.outer_radius || cfg.outer_radius || cfg.damage_radius || 350);
  const inner = effectRadiusToRadarPixels(utility.effect?.inner_radius || cfg.inner_radius || 120);
  context.save();
  context.strokeStyle = 'rgba(239,68,68,0.42)';
  context.fillStyle = 'rgba(239,68,68,0.08)';
  context.lineWidth = utility.id === state.selectedUtility?.id ? 4 : 2;
  context.beginPath();
  context.arc(x, y, outer, 0, Math.PI * 2);
  context.fill();
  context.stroke();
  if (blastTicks > 0 && tick <= start + blastTicks) {
    const t = (tick - start) / blastTicks;
    const core = Math.max(8, inner * (1 - t * 0.4));
    const wave = inner + (outer - inner) * t;
    const gradient = context.createRadialGradient(x, y, 0, x, y, core);
    gradient.addColorStop(0, `rgba(255,245,180,${0.8 * (1 - t)})`);
    gradient.addColorStop(0.55, `rgba(249,115,22,${0.5 * (1 - t)})`);
    gradient.addColorStop(1, 'rgba(239,68,68,0)');
    context.fillStyle = gradient;
    context.beginPath();
    context.arc(x, y, core, 0, Math.PI * 2);
    context.fill();
    context.strokeStyle = `rgba(255,235,180,${0.65 * (1 - t)})`;
    context.lineWidth = 3;
    context.beginPath();
    context.arc(x, y, wave, 0, Math.PI * 2);
    context.stroke();
  }
  if (state.filters.showHeSmoke && smokeTicks > 0) drawPuffs(context, utility, x, y, outer * 0.55, tick, start, smokeTicks, 'he');
  context.restore();
}

function drawSmokeCloud(context, utility, tick) {
  const opacity = getUtilityOpacityByTick(utility, tick);
  if (opacity <= 0) return;
  const cfg = getUtilityConfig('smoke');
  const pos = utility.effect?.radar_pos || utility.radar_detonate_pos;
  const x = Number(pos?.x);
  const y = Number(pos?.y);
  if (!Number.isFinite(x) || !Number.isFinite(y)) return;
  const radius = effectRadiusToRadarPixels(utility.effect?.radius || cfg.radius || 170);
  const window = getUtilityEffectWindow(utility);
  const palette = smokePalette(utility, cfg);
  context.save();
  context.globalAlpha = opacity;
  drawPuffs(context, utility, x, y, radius, tick, window.startTick, Math.max(1, window.endTick - window.startTick), 'smoke', palette);
  const core = context.createRadialGradient(x, y, 0, x, y, radius * 0.68);
  core.addColorStop(0, palette.core);
  core.addColorStop(0.68, palette.outer);
  core.addColorStop(1, 'rgba(120,120,120,0)');
  context.fillStyle = core;
  context.beginPath();
  context.arc(x, y, radius * 0.62, 0, Math.PI * 2);
  context.fill();
  if (state.filters.showSmokeTimer && Number.isFinite(window.startTick) && Number.isFinite(window.endTick) && window.endTick > window.startTick) {
    const remainingTicks = Math.max(0, window.endTick - tick);
    const remainingRatio = Math.max(0, Math.min(1, remainingTicks / (window.endTick - window.startTick)));
    drawSmokeTimer(context, x, y, remainingRatio, ticksToSeconds(remainingTicks), cfg);
  }
  context.restore();
}

function drawMolotovFire(context, utility, tick) {
  const opacity = getUtilityOpacityByTick(utility, tick);
  if (opacity <= 0) return;
  const cfg = getUtilityConfig('molotov');
  const pos = utility.effect?.radar_pos || utility.radar_detonate_pos;
  const x = Number(pos?.x);
  const y = Number(pos?.y);
  if (!Number.isFinite(x) || !Number.isFinite(y)) return;
  const radius = effectRadiusToRadarPixels(utility.effect?.radius || cfg.radius || 180);
  const flicker = 0.9 + 0.1 * Math.sin((tick + stableHash(utility.id)) * 0.35);
  context.save();
  context.globalAlpha = opacity;
  const gradient = context.createRadialGradient(x, y, 0, x, y, radius * flicker);
  gradient.addColorStop(0, 'rgba(255,230,120,0.5)');
  gradient.addColorStop(0.45, 'rgba(249,115,22,0.34)');
  gradient.addColorStop(1, 'rgba(185,28,28,0.05)');
  context.fillStyle = gradient;
  context.strokeStyle = 'rgba(251,146,60,0.65)';
  context.lineWidth = utility.id === state.selectedUtility?.id ? 4 : 2;
  context.beginPath();
  context.arc(x, y, radius * flicker, 0, Math.PI * 2);
  context.fill();
  context.stroke();
  context.restore();
}

function drawSimpleUtilityArea(context, utility, tick) {
  const opacity = getUtilityOpacityByTick(utility, tick);
  if (opacity <= 0) return;
  const effect = utility.effect || {};
  const pos = effect.radar_pos || utility.radar_detonate_pos;
  const x = Number(pos?.x);
  const y = Number(pos?.y);
  if (!Number.isFinite(x) || !Number.isFinite(y)) return;
  const style = utilityStyle[utility.type] || utilityStyle.flashbang;
  context.save();
  context.globalAlpha = opacity;
  context.fillStyle = style.fill;
  context.strokeStyle = style.color;
  context.lineWidth = utility.id === state.selectedUtility?.id ? 4 : 2;
  context.beginPath();
  context.arc(x, y, effectRadiusToRadarPixels(effect.radius || 90), 0, Math.PI * 2);
  context.fill();
  context.stroke();
  context.restore();
}

function drawSmokeTimer(context, x, y, remainingRatio, remainingSec, cfg) {
  const radius = 15;
  const startAngle = -Math.PI / 2;
  const endAngle = startAngle + Math.PI * 2 * remainingRatio;
  context.save();
  context.globalAlpha = 1;
  context.fillStyle = cfg.timer_bg_color || 'rgba(15,17,23,0.72)';
  context.beginPath();
  context.arc(x, y, radius, 0, Math.PI * 2);
  context.fill();
  context.fillStyle = cfg.timer_fill_color || 'rgba(238,242,247,0.82)';
  context.beginPath();
  context.moveTo(x, y);
  context.arc(x, y, radius - 3, startAngle, endAngle, false);
  context.closePath();
  context.fill();
  context.strokeStyle = 'rgba(255,255,255,0.5)';
  context.lineWidth = 1.5;
  context.beginPath();
  context.arc(x, y, radius, 0, Math.PI * 2);
  context.stroke();
  if (remainingSec <= 9.5) {
    context.fillStyle = cfg.timer_text_color || 'rgba(255,255,255,0.88)';
    context.font = '10px sans-serif';
    context.textAlign = 'center';
    context.textBaseline = 'middle';
    context.fillText(String(Math.ceil(remainingSec)), x, y + 0.5);
  }
  context.restore();
}

function drawPuffs(context, utility, x, y, radius, tick, startTick, durationTicks, kind, palette = null) {
  const puffs = utilityPuffs(utility, kind);
  const age = Number.isFinite(startTick) && durationTicks > 1 ? Math.max(0, Math.min(1, (tick - startTick) / durationTicks)) : 0;
  const smokeCfg = kind === 'smoke' ? (palette || smokePalette(utility, getUtilityConfig('smoke'))) : null;
  for (const puff of puffs) {
    const px = x + puff.dx * radius * (1 + age * 0.25);
    const py = y + puff.dy * radius * (1 + age * 0.25);
    const pr = radius * puff.r * (kind === 'he' ? 0.42 + age * 0.28 : 0.34);
    context.fillStyle = kind === 'he' ? `rgba(35,35,35,${0.24 * (1 - age)})` : smokePuffColor(puff, smokeCfg);
    context.beginPath();
    context.arc(px, py, pr, 0, Math.PI * 2);
    context.fill();
  }
}

function smokePuffColor(puff, cfg) {
  if (puff.r > 0.46) return cfg?.core || cfg?.core_color || 'rgba(55,55,55,0.62)';
  if (puff.a > 0.55) return cfg?.outer || cfg?.outer_color || 'rgba(95,95,95,0.34)';
  return cfg?.edge || cfg?.edge_color || 'rgba(120,120,120,0.18)';
}

function smokePalette(utility, cfg) {
  const side = resolveUtilitySide(utility);
  if (side === 'T') {
    return {
      core: cfg.t_core_color || 'rgba(255,177,66,0.68)',
      outer: cfg.t_outer_color || 'rgba(245,158,11,0.40)',
      edge: cfg.t_edge_color || 'rgba(251,191,36,0.20)',
    };
  }
  if (side === 'CT') {
    return {
      core: cfg.ct_core_color || 'rgba(96,165,250,0.68)',
      outer: cfg.ct_outer_color || 'rgba(59,130,246,0.40)',
      edge: cfg.ct_edge_color || 'rgba(147,197,253,0.20)',
    };
  }
  return {
    core: cfg.core_color || 'rgba(55,55,55,0.62)',
    outer: cfg.outer_color || 'rgba(95,95,95,0.34)',
    edge: cfg.edge_color || 'rgba(120,120,120,0.18)',
  };
}

function resolveUtilitySide(utility) {
  const direct = normalizeSide(utility.thrower_team || utility.thrower_side || utility.team || utility.side);
  if (direct) return direct;
  const steamid = String(utility.thrower_player_id || utility.thrower_steamid || '');
  return steamid ? state.playerSideBySteamid.get(steamid) || null : null;
}

function normalizeSide(value) {
  const text = String(value || '').toUpperCase();
  if (text === 'T' || text === 'TERRORIST' || text === 'TERRORISTS' || text === 'TEAM_T') return 'T';
  if (text === 'CT' || text === 'COUNTERTERRORIST' || text === 'COUNTERTERRORISTS' || text === 'TEAM_CT') return 'CT';
  return null;
}

function utilityPuffs(utility, kind) {
  const key = `${utility.id || 'utility'}:${kind}`;
  if (state.utilityPuffCache.has(key)) return state.utilityPuffCache.get(key);
  let seed = stableHash(key);
  const count = kind === 'he' ? 9 : 18;
  const puffs = [];
  for (let i = 0; i < count; i += 1) {
    seed = (seed * 1664525 + 1013904223) >>> 0;
    const angle = (seed / 4294967295) * Math.PI * 2;
    seed = (seed * 1664525 + 1013904223) >>> 0;
    const dist = Math.sqrt(seed / 4294967295) * 0.82;
    seed = (seed * 1664525 + 1013904223) >>> 0;
    const r = 0.24 + (seed / 4294967295) * 0.34;
    seed = (seed * 1664525 + 1013904223) >>> 0;
    puffs.push({ dx: Math.cos(angle) * dist, dy: Math.sin(angle) * dist, r, a: seed / 4294967295 });
  }
  state.utilityPuffCache.set(key, puffs);
  return puffs;
}

function stableHash(value) {
  let hash = 2166136261;
  for (const ch of String(value || '')) {
    hash ^= ch.charCodeAt(0);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function drawUtilityTrajectory(context, utility, tick, options = {}) {
  const fadeTicks = secondsToTicks(3);
  const throwTick = toFiniteNumber(utility.throw_tick) ?? toFiniteNumber(utility.trajectory?.[0]?.tick);
  const detonateTick = toFiniteNumber(utility.detonate_tick) ?? toFiniteNumber(utility.trajectory?.at(-1)?.tick);
  const forceFull = Boolean(options.forceFull);
  if (!Number.isFinite(throwTick) || !Number.isFinite(detonateTick)) return;
  const fadeEnd = detonateTick + fadeTicks;
  if (!forceFull && (tick < throwTick || tick > fadeEnd)) return;
  const points = forceFull ? (utility.trajectory || []) : visibleTrajectoryPoints(utility, tick);
  if (points.length === 0) return;
  const style = utilityStyle[utility.type] || utilityStyle.flashbang;
  context.save();
  context.strokeStyle = style.color;
  context.fillStyle = style.color;
  context.lineWidth = utility.id === state.selectedUtility?.id ? 4 : 2;
  context.globalAlpha = forceFull ? 0.9 : (tick <= detonateTick ? 0.9 : Math.max(0.2, 1 - ((tick - detonateTick) / fadeTicks)));
  if (utility.approximate_trajectory) context.setLineDash([8, 6]);
  context.beginPath();
  points.forEach((point, idx) => {
    const x = Number(point.radar_pos?.x);
    const y = Number(point.radar_pos?.y);
    if (!Number.isFinite(x) || !Number.isFinite(y)) return;
    if (idx === 0) context.moveTo(x, y);
    else context.lineTo(x, y);
  });
  context.stroke();
  const last = points[points.length - 1];
  if (last?.radar_pos) {
    context.beginPath();
    context.arc(Number(last.radar_pos.x), Number(last.radar_pos.y), 5, 0, Math.PI * 2);
    context.fill();
  }
  context.restore();
}

function visibleTrajectoryPoints(utility, tick) {
  const points = utility.trajectory || [];
  if (points.length <= 1) return points;
  const detonateTick = utility.detonate_tick ?? points[points.length - 1].tick;
  if (tick >= detonateTick) return points;
  const visible = points.filter(point => Number(point.tick) <= tick);
  return visible.length ? visible : [points[0]];
}

function drawTokens(tokens, editable, tick, frame = null, prevFrame = null) {
  const blinded = blindedSteamidsAtTick(tick);
  for (const token of tokens) {
    const display = analysisItemDisplay(token, 'player');
    if (!display.visible) continue;
    const x = Number(token.radar_x);
    const y = Number(token.radar_y);
    if (!Number.isFinite(x) || !Number.isFinite(y)) continue;
    const health = Number(token.health || 0);
    const alive = token.is_alive !== false && health > 0;
    const blindInfo = blinded.get(String(token.steamid));
    ctx.save();
    ctx.globalAlpha = (alive ? 1 : 0.35) * display.alpha;
    if (blindInfo && state.filters.showBlindHalo) drawBlindHalo(x, y, editable ? 13 : 11, blindInfo.intensity);
    ctx.fillStyle = alive ? (token.team === 'T' ? '#fbbf24' : '#60a5fa') : '#6b7280';
    ctx.strokeStyle = display.highlight ? '#ffffff' : blindInfo ? '#ffffff' : '#111827';
    ctx.lineWidth = display.highlight ? 5 : blindInfo ? 3 + 4 * blindInfo.intensity : 3;
    ctx.beginPath();
    ctx.arc(x, y, editable ? 13 : 11, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();

    if (blindInfo && blindInfo.intensity > 0.65 && state.filters.showBlindHalo) {
      ctx.fillStyle = `rgba(255,255,255,${0.18 + 0.16 * blindInfo.intensity})`;
      ctx.beginPath();
      ctx.arc(x, y, editable ? 13 : 11, 0, Math.PI * 2);
      ctx.fill();
    }
    if (state.filters.showYaw && alive) drawYawArrow(token, frame, prevFrame, x, y);
    if (state.filters.showHealthBars) drawHealthBar(x, y + 16, health, alive);
    if (state.filters.showNames) drawTokenLabel(token, x, y);
    ctx.restore();
  }
}

function drawBlindHalo(x, y, tokenRadius, intensity) {
  const safeIntensity = Math.max(0, Math.min(1, Number(intensity) || 0));
  const haloAlpha = 0.25 + 0.65 * safeIntensity;
  const haloRadius = tokenRadius * (1.4 + 1.2 * safeIntensity);
  const haloLineWidth = 2 + 5 * safeIntensity;
  ctx.save();
  ctx.strokeStyle = `rgba(255,255,255,${haloAlpha})`;
  ctx.fillStyle = `rgba(255,255,255,${0.08 * safeIntensity})`;
  ctx.lineWidth = haloLineWidth;
  ctx.beginPath();
  ctx.arc(x, y, haloRadius, 0, Math.PI * 2);
  ctx.fill();
  ctx.stroke();
  ctx.restore();
}

function drawYawArrow(token, frame, prevFrame, x, y) {
  const yaw = resolveTokenYaw(token, frame, prevFrame);
  if (yaw === null) return;
  const vector = yawToRadarVector(yaw);
  ctx.strokeStyle = '#ffffff';
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(x, y);
  ctx.lineTo(x + vector.dx * 22, y + vector.dy * 22);
  ctx.stroke();
  if (state.debugYaw) console.debug('yaw', token.name || token.steamid, token.yaw, yaw, vector);
}

function normalizeYaw(rawYaw) {
  if (rawYaw === null || rawYaw === undefined || rawYaw === '') return null;
  const value = Number.parseFloat(rawYaw);
  if (!Number.isFinite(value)) return null;
  let degrees = state.yawUnit === 'radian' ? value * 180 / Math.PI : value;
  degrees %= 360;
  if (degrees < 0) degrees += 360;
  return degrees;
}

function inferYawUnit(frames) {
  const values = [];
  for (const frame of frames.slice(0, 80)) {
    for (const player of frame.players || []) {
      const value = Number.parseFloat(player.yaw);
      if (Number.isFinite(value) && Math.abs(value) > 0.001) values.push(Math.abs(value));
      if (values.length >= 50) break;
    }
    if (values.length >= 50) break;
  }
  if (!values.length) return 'degree';
  const max = Math.max(...values);
  return max <= Math.PI * 2 + 0.001 ? 'radian' : 'degree';
}

function yawToRadarVector(yawDeg) {
  const rad = yawDeg * Math.PI / 180;
  return { dx: Math.cos(rad), dy: -Math.sin(rad) };
}

function resolveTokenYaw(token, frame, prevFrame) {
  const steamid = String(token.steamid || '');
  const currentYaw = normalizeYaw(token.yaw);
  if (currentYaw !== null) {
    if (steamid) state.yawCacheBySteamid.set(steamid, currentYaw);
    return currentYaw;
  }
  if (steamid && state.yawCacheBySteamid.has(steamid)) return state.yawCacheBySteamid.get(steamid);
  const movementYaw = movementYawFromFrames(token, prevFrame);
  if (movementYaw !== null) {
    if (steamid) state.yawCacheBySteamid.set(steamid, movementYaw);
    return movementYaw;
  }
  return null;
}

function movementYawFromFrames(token, prevFrame) {
  if (!prevFrame) return null;
  const prev = (prevFrame.players || []).find(player => String(player.steamid) === String(token.steamid));
  if (!prev) return null;
  const dx = Number(token.radar_x) - Number(prev.radar_x);
  const dy = Number(token.radar_y) - Number(prev.radar_y);
  if (!Number.isFinite(dx) || !Number.isFinite(dy) || Math.hypot(dx, dy) < 1) return null;
  let degrees = Math.atan2(-dy, dx) * 180 / Math.PI;
  if (degrees < 0) degrees += 360;
  return degrees;
}

function drawHealthBar(x, y, health, alive) {
  const width = 36;
  const height = 5;
  const pct = alive ? Math.max(0, Math.min(1, health / 100)) : 0;
  ctx.fillStyle = 'rgba(0,0,0,0.75)';
  ctx.fillRect(x - width / 2, y, width, height);
  ctx.fillStyle = pct > 0.6 ? '#22c55e' : pct > 0.3 ? '#facc15' : '#ef4444';
  ctx.fillRect(x - width / 2, y, width * pct, height);
  ctx.strokeStyle = '#111827';
  ctx.lineWidth = 1;
  ctx.strokeRect(x - width / 2, y, width, height);
}

function drawTokenLabel(token, x, y) {
  ctx.font = '12px sans-serif';
  ctx.fillStyle = '#fff';
  ctx.strokeStyle = '#000';
  const label = `${token.name || token.steamid} ${token.health ?? '-'}`;
  ctx.lineWidth = 3;
  ctx.strokeText(label, x + 14, y - 10);
  ctx.fillText(label, x + 14, y - 10);
}

function blindedSteamidsAtTick(tick) {
  const blinded = new Map();
  if (tick === null || tick === undefined || !state.filters.showBlindHalo) return blinded;
  const utilities = state.sandbox ? (state.sandbox.planned_utilities || []) : currentUtilities();
  for (const utility of utilities) {
    if (utility.type !== 'flashbang') continue;
    for (const target of utility.effect?.blinded_players || utility.effect?.target_players || []) {
      const startTick = Number(target.tick ?? utility.detonate_tick);
      const endTick = Number(target.end_tick ?? startTick + secondsToTicks(target.duration ?? 1));
      if (!target.steamid || tick < startTick || tick > endTick) continue;
      const intensity = Number(target.intensity ?? Math.min(1, Number(target.duration || 1) / Number(getUtilityConfig('flashbang').max_blind_duration_sec || 5)));
      const current = blinded.get(String(target.steamid));
      if (!current || intensity > current.intensity) blinded.set(String(target.steamid), { ...target, intensity });
    }
  }
  return blinded;
}

async function enterSandbox() {
  if (!state.roundData) return;
  pause();
  const frame = currentFrame();
  if (!frame) return;
  const plannedUtilities = await loadMatchingSandboxUtilities(state.currentRound, frame.tick);
  state.sandbox = {
    schema_version: 1,
    demo_id: state.demoId,
    source_match_id: state.demoId,
    source_round_number: state.currentRound,
    source_tick: frame.tick,
    source_frame_index: state.frameIndex,
    created_at: new Date().toISOString(),
    dirty: false,
    round: state.currentRound,
    currentTick: frame.tick,
    nextUtilityThrowTick: sandboxUtilityPlanningTick({ source_tick: frame.tick, currentTick: frame.tick, planned_utilities: plannedUtilities }),
    playing: false,
    playStartTime: 0,
    playStartTick: frame.tick,
    rafId: null,
    mode: 'idle',
    selectedThrower: null,
    selectedThrowerId: null,
    selectedUtilityType: null,
    menuAnchor: null,
    awaitingUtilityLanding: false,
    tokens: JSON.parse(JSON.stringify(frame.players)),
    annotations: [],
    planned_utilities: plannedUtilities,
  };
  state.activeMapTool = 'move';
  updateSandboxButtons();
  updateNavigationButtons();
  updateMapToolbar();
  renderSideLists();
  draw();
  if (!state.room.suppressBroadcast) {
    sendRoomMessage('enter_sandbox', { sandbox: sandboxPayload() });
  }
}

async function loadMatchingSandboxUtilities(roundNumber, sourceTick) {
  try {
    const latest = await api(`/api/demos/${state.demoId}/sandbox/latest`);
    const saved = latest?.state;
    if (!latest?.exists || !saved) return [];
    if (Number(saved?.source_round_number ?? saved?.round) !== Number(roundNumber)) return [];
    if (Number(saved?.source_tick) !== Number(sourceTick)) return [];
    return (saved?.planned_utilities || []).map(utility => normalizeUtilityEvent(utility, 'sandbox'));
  } catch (err) {
    return [];
  }
}

function drawSandbox() {
  const tick = state.sandbox.currentTick ?? state.sandbox.source_tick;
  drawUtilityEvents(tick, state.sandbox.planned_utilities || []);
  drawTokens(state.sandbox.tokens, true, tick, currentFrame(), previousFrame());
  for (const ann of state.sandbox.annotations) drawAnnotation(ann);
  if (state.arrowDraft) drawArrow(state.arrowDraft.from[0], state.arrowDraft.from[1], state.arrowDraft.to[0], state.arrowDraft.to[1], '#f97316');
  if (state.brushDraft) drawBrushStroke(state.brushDraft, { alpha: 0.9 });
  if (state.laserPoint) drawLaserPoint(state.laserPoint, '你');
  drawRemoteCursors();
}

function drawAnnotation(ann) {
  if (!ann) return;
  if (ann.type === 'arrow') drawArrow(ann.from[0], ann.from[1], ann.to[0], ann.to[1], ann.color || '#22c55e');
  if (ann.type === 'text') drawTextNote(ann.position[0], ann.position[1], ann.text);
  if (ann.type === 'brush') drawBrushStroke(ann);
}

function drawBrushStroke(stroke, options = {}) {
  const points = stroke.points || [];
  if (points.length < 2) return;
  ctx.save();
  ctx.strokeStyle = stroke.color || '#facc15';
  ctx.lineWidth = stroke.width || 4;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  ctx.globalAlpha = options.alpha ?? 0.82;
  ctx.beginPath();
  points.forEach((point, idx) => {
    const x = Number(point.x);
    const y = Number(point.y);
    if (!Number.isFinite(x) || !Number.isFinite(y)) return;
    if (idx === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();
  ctx.restore();
}

function drawArrow(x1, y1, x2, y2, color) {
  ctx.strokeStyle = color;
  ctx.fillStyle = color;
  ctx.lineWidth = 4;
  ctx.beginPath();
  ctx.moveTo(x1, y1);
  ctx.lineTo(x2, y2);
  ctx.stroke();
  const angle = Math.atan2(y2 - y1, x2 - x1);
  ctx.beginPath();
  ctx.moveTo(x2, y2);
  ctx.lineTo(x2 - Math.cos(angle - 0.5) * 16, y2 - Math.sin(angle - 0.5) * 16);
  ctx.lineTo(x2 - Math.cos(angle + 0.5) * 16, y2 - Math.sin(angle + 0.5) * 16);
  ctx.closePath();
  ctx.fill();
}

function drawTextNote(x, y, text) {
  ctx.font = '18px sans-serif';
  ctx.fillStyle = 'rgba(0,0,0,0.65)';
  const width = ctx.measureText(text).width + 14;
  ctx.fillRect(x - 4, y - 22, width, 28);
  ctx.fillStyle = '#ffffff';
  ctx.fillText(text, x + 3, y - 2);
}

function drawLaserPoint(point, label) {
  const x = Number(point.x);
  const y = Number(point.y);
  if (!Number.isFinite(x) || !Number.isFinite(y)) return;
  ctx.save();
  ctx.strokeStyle = 'rgba(248,113,113,0.95)';
  ctx.fillStyle = 'rgba(248,113,113,0.28)';
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.arc(x, y, 16, 0, Math.PI * 2);
  ctx.fill();
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(x - 22, y);
  ctx.lineTo(x + 22, y);
  ctx.moveTo(x, y - 22);
  ctx.lineTo(x, y + 22);
  ctx.stroke();
  if (label) {
    ctx.font = '13px sans-serif';
    ctx.fillStyle = '#fecaca';
    ctx.fillText(label, x + 18, y - 18);
  }
  ctx.restore();
}

function drawRemoteCursors() {
  const now = performance.now();
  for (const [clientId, cursor] of state.remoteCursors.entries()) {
    if (now - cursor.updatedAt > 1800) {
      state.remoteCursors.delete(clientId);
      continue;
    }
    drawLaserPoint(cursor, cursor.displayName);
  }
}

function currentTool() {
  if (state.sandbox) return state.activeMapTool === 'select' ? 'move' : state.activeMapTool;
  return state.activeMapTool || 'select';
}

function makeAnnotation(object) {
  return normalizeAnnotation({ id: annotationId(object.type || 'ann'), ...object });
}

function addAnnotation(annotation) {
  if (!state.sandbox || !annotation) return;
  const normalized = normalizeAnnotation(annotation);
  if (!normalized) return;
  state.sandbox.annotations.push(normalized);
  sendRoomMessage('create_object', { object: normalized });
  markSandboxDirty();
  renderSideLists();
}

function removeAnnotation(annotation) {
  if (!state.sandbox || !annotation?.id) return;
  state.sandbox.annotations = (state.sandbox.annotations || []).filter(item => item.id !== annotation.id);
  sendRoomMessage('delete_object', { object_id: annotation.id });
  markSandboxDirty();
  renderSideLists();
}

function sendLaserCursor(point) {
  const now = performance.now();
  state.laserPoint = { x: round2(point.x), y: round2(point.y) };
  if (now - state.room.lastCursorSentAt > 35) {
    state.room.lastCursorSentAt = now;
    sendRoomMessage('cursor', { tool: 'laser', radar_x: state.laserPoint.x, radar_y: state.laserPoint.y, display_name: state.room.joinProfile?.display_name || 'laser' });
  }
}

function onCanvasDown(evt) {
  const screen = screenPoint(evt);
  const point = screenToRadar(screen.x, screen.y);
  state.pointerDown = { screenX: screen.x, screenY: screen.y, radarX: point.x, radarY: point.y, moved: false };
  const tool = currentTool();
  if (state.sandbox) {
    if (state.sandbox.awaitingUtilityLanding) return;
    if (tool === 'move') {
      const token = hitToken(point.x, point.y);
      if (token) {
        state.drag = { token, dx: Number(token.radar_x) - point.x, dy: Number(token.radar_y) - point.y };
        closeUtilityMenu();
        updateSandboxButtons();
        return;
      }
    }
    if (tool === 'arrow') {
      state.arrowDraft = { from: [point.x, point.y], to: [point.x, point.y] };
      return;
    }
    if (tool === 'brush') {
      state.brushDraft = { type: 'brush', points: [{ x: round2(point.x), y: round2(point.y) }], color: '#facc15', width: 4 };
      return;
    }
    if (tool === 'eraser') {
      const annotation = hitAnnotation(point.x, point.y);
      if (annotation) removeAnnotation(annotation);
      draw();
      return;
    }
    if (tool === 'laser') {
      sendLaserCursor(point);
      draw();
      return;
    }
    if (tool === 'text') return;
  }
  if (tool === 'pan' || !state.sandbox || (state.sandbox && !['arrow', 'text', 'brush', 'eraser', 'laser'].includes(tool))) {
    state.viewportDrag = { screenX: screen.x, screenY: screen.y };
  }
}

function onCanvasMove(evt) {
  const screen = screenPoint(evt);
  const point = screenToRadar(screen.x, screen.y);
  if (state.pointerDown && distance(screen.x, screen.y, state.pointerDown.screenX, state.pointerDown.screenY) > 4) state.pointerDown.moved = true;
  if (state.drag && state.sandbox) {
    state.drag.token.radar_x = round2(point.x + state.drag.dx);
    state.drag.token.radar_y = round2(point.y + state.drag.dy);
    if (state.sandbox.selectedThrower === state.drag.token) {
      state.sandbox.menuAnchor = { radarX: state.drag.token.radar_x, radarY: state.drag.token.radar_y };
      syncSandboxUtilityMenu();
    }
    markSandboxDirty();
    const now = performance.now();
    if (now - state.room.lastMoveSentAt > 45) {
      state.room.lastMoveSentAt = now;
      sendRoomMessage('move_token', roomTokenPayload(state.drag.token));
    }
    draw();
    return;
  }
  if (state.arrowDraft && state.sandbox) {
    state.arrowDraft.to = [point.x, point.y];
    draw();
    return;
  }
  if (state.brushDraft && state.sandbox) {
    const points = state.brushDraft.points;
    const last = points[points.length - 1];
    if (!last || distance(point.x, point.y, last.x, last.y) > 2) points.push({ x: round2(point.x), y: round2(point.y) });
    draw();
    return;
  }
  if (state.sandbox && currentTool() === 'eraser' && state.pointerDown) {
    const annotation = hitAnnotation(point.x, point.y);
    if (annotation) removeAnnotation(annotation);
    draw();
    return;
  }
  if (state.sandbox && currentTool() === 'laser' && state.pointerDown) {
    sendLaserCursor(point);
    draw();
    return;
  }
  if (state.viewportDrag) {
    panViewportBy(screen.x - state.viewportDrag.screenX, screen.y - state.viewportDrag.screenY);
    state.viewportDrag = { screenX: screen.x, screenY: screen.y };
  }
}

function onCanvasUp(evt) {
  if (state.arrowDraft && state.sandbox) {
    const arrow = makeAnnotation({
      type: 'arrow',
      from: [round2(state.arrowDraft.from[0]), round2(state.arrowDraft.from[1])],
      to: [round2(state.arrowDraft.to[0]), round2(state.arrowDraft.to[1])],
    });
    addAnnotation(arrow);
    state.arrowDraft = null;
  }
  if (state.brushDraft && state.sandbox) {
    if ((state.brushDraft.points || []).length > 1) addAnnotation(makeAnnotation(state.brushDraft));
    state.brushDraft = null;
  }
  if (state.laserPoint && currentTool() === 'laser') state.laserPoint = null;
  if (state.drag && state.sandbox) sendRoomMessage('move_token', roomTokenPayload(state.drag.token));
  state.drag = null;
  state.viewportDrag = null;
  draw();
}

function onCanvasClick(evt) {
  if (state.pointerDown?.moved) {
    state.pointerDown = null;
    return;
  }
  const point = canvasRadarPoint(evt);
  state.pointerDown = null;
  if (state.sandbox) {
    handleSandboxClick(point);
    return;
  }
  if (!state.roundData) return;
  const utility = hitUtility(point.x, point.y);
  if (utility) {
    state.selectedUtility = utility;
    state.selectedPlayerId = null;
    renderUtilityDetail();
    draw();
  }
}

function onCanvasDblClick(evt) {
  if (!state.sandbox || state.sandbox.mode === 'select_landing') return;
  const point = canvasRadarPoint(evt);
  const token = hitToken(point.x, point.y);
  if (token && ['move', 'utility'].includes(currentTool())) {
    openUtilityMenu(token);
    draw();
  }
}

function handleSandboxClick(point) {
  if (state.drag || state.arrowDraft || state.viewportDrag) return;
  if (state.sandbox.mode === 'select_landing' && state.sandbox.selectedThrower && state.sandbox.selectedUtilityType) {
    onMapClickForUtilityLanding(point);
    return;
  }
  if (currentTool() === 'text') {
    const text = prompt('备注文本');
    if (text) {
      addAnnotation(makeAnnotation({ type: 'text', position: [round2(point.x), round2(point.y)], text }));
      draw();
    }
    return;
  }
  const utility = hitUtility(point.x, point.y);
  if (utility) {
    cancelSandboxUtilitySelection();
    state.selectedUtility = utility;
    state.selectedPlayerId = null;
    renderUtilityDetail();
    draw();
    return;
  }
  if (state.sandbox.mode !== 'idle') cancelSandboxUtilitySelection();
}

function hitToken(x, y) {
  if (!state.sandbox) return null;
  let best = null;
  let bestDist = Infinity;
  const radius = 18 / Math.max(state.viewport.zoom, 0.001);
  for (const token of state.sandbox.tokens) {
    const dx = Number(token.radar_x) - x;
    const dy = Number(token.radar_y) - y;
    const dist = Math.sqrt(dx * dx + dy * dy);
    if (dist < radius && dist < bestDist) { best = token; bestDist = dist; }
  }
  return best;
}

function hitAnnotation(x, y) {
  if (!state.sandbox) return null;
  const annotations = state.sandbox.annotations || [];
  for (let idx = annotations.length - 1; idx >= 0; idx -= 1) {
    const ann = annotations[idx];
    if (annotationHit(ann, x, y)) return ann;
  }
  return null;
}

function annotationHit(ann, x, y) {
  const threshold = 16 / Math.max(state.viewport.zoom, 0.001);
  if (ann.type === 'brush') return (ann.points || []).some((point, idx, points) => idx > 0 && distanceToSegment(x, y, points[idx - 1], point) <= threshold);
  if (ann.type === 'arrow') return distanceToSegment(x, y, { x: ann.from?.[0], y: ann.from?.[1] }, { x: ann.to?.[0], y: ann.to?.[1] }) <= threshold;
  if (ann.type === 'text') return distance(x, y, Number(ann.position?.[0]), Number(ann.position?.[1])) <= Math.max(24, threshold);
  return false;
}

function distanceToSegment(x, y, a, b) {
  const ax = Number(a?.x ?? a?.[0]);
  const ay = Number(a?.y ?? a?.[1]);
  const bx = Number(b?.x ?? b?.[0]);
  const by = Number(b?.y ?? b?.[1]);
  if (![ax, ay, bx, by].every(Number.isFinite)) return Infinity;
  const dx = bx - ax;
  const dy = by - ay;
  if (dx === 0 && dy === 0) return distance(x, y, ax, ay);
  const t = Math.max(0, Math.min(1, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)));
  return distance(x, y, ax + t * dx, ay + t * dy);
}

function hitUtility(x, y) {
  let best = null;
  let bestDist = Infinity;
  const tick = state.sandbox ? state.sandbox.currentTick : currentTick();
  const utilities = state.sandbox ? (state.sandbox.planned_utilities || []) : currentUtilities({ forOverlay: true });
  for (const utility of utilities) {
    const effect = utility.effect || {};
    const effectPos = effect.radar_pos || utility.radar_detonate_pos;
    if (effectPos && state.filters.showUtilityEffects) {
      const dist = distance(x, y, Number(effectPos.x), Number(effectPos.y));
      const radius = effectRadiusToRadarPixels(effect.radius || effect.outer_radius || 100);
      const opacity = tick === null ? 1 : getUtilityOpacityByTick(utility, tick);
      const active = utility.type === 'flashbang' ? tick >= Number(utility.detonate_tick || 0) && tick <= Number(getUtilityEffectWindow(utility).endTick || utility.detonate_tick || 0) : opacity > 0;
      if (active && dist <= radius && dist < bestDist) { best = utility; bestDist = dist; }
    }
    if (state.filters.showUtilityTrajectories) {
      for (const point of utility.trajectory || []) {
        const pos = point.radar_pos;
        if (!pos) continue;
        const dist = distance(x, y, Number(pos.x), Number(pos.y));
        if (dist < 16 / Math.max(state.viewport.zoom, 0.001) && dist < bestDist) { best = utility; bestDist = dist; }
      }
    }
  }
  return best;
}

function openUtilityMenu(token) {
  if (!state.sandbox || !token) return;
  state.sandbox.selectedThrower = token;
  state.sandbox.selectedThrowerId = String(token.steamid || token.name || '');
  state.sandbox.selectedUtilityType = null;
  state.sandbox.awaitingUtilityLanding = false;
  state.sandbox.mode = 'utility_menu';
  state.sandbox.menuAnchor = { radarX: Number(token.radar_x), radarY: Number(token.radar_y) };
  state.selectedUtility = null;
  renderUtilityDetail();
  updateSandboxButtons();
  syncSandboxUtilityMenu();
}

function syncSandboxUtilityMenu() {
  if (!state.sandbox || state.sandbox.mode !== 'utility_menu' || !state.sandbox.menuAnchor || !els.mapStage || !els.sandboxUtilityMenu) return;
  const menu = els.sandboxUtilityMenu;
  menu.hidden = false;
  const stageRect = els.mapStage.getBoundingClientRect();
  const canvasRect = els.canvas.getBoundingClientRect();
  const screen = radarToScreen(state.sandbox.menuAnchor.radarX, state.sandbox.menuAnchor.radarY);
  const scaleX = canvasRect.width / els.canvas.width;
  const scaleY = canvasRect.height / els.canvas.height;
  const anchorX = canvasRect.left - stageRect.left + screen.x * scaleX;
  const anchorY = canvasRect.top - stageRect.top + screen.y * scaleY;
  const margin = 8;
  const gap = 12;
  const width = menu.offsetWidth || 180;
  const height = menu.offsetHeight || 150;
  let left = anchorX + gap;
  let top = anchorY - height / 2;
  if (left + width + margin > stageRect.width) left = anchorX - width - gap;
  if (top + height + margin > stageRect.height) top = stageRect.height - height - margin;
  if (top < margin) top = margin;
  if (left < margin) left = margin;
  if (left + width + margin > stageRect.width) left = Math.max(margin, stageRect.width - width - margin);
  menu.style.left = `${Math.round(left)}px`;
  menu.style.top = `${Math.round(top)}px`;
}

function closeUtilityMenu() {
  if (els.sandboxUtilityMenu) els.sandboxUtilityMenu.hidden = true;
}

function handleSandboxEscape() {
  if (!state.sandbox) return;
  if (state.sandbox.mode !== 'idle' || state.sandbox.selectedUtilityType || state.sandbox.selectedThrower) cancelSandboxUtilitySelection();
  state.arrowDraft = null;
  state.brushDraft = null;
  state.laserPoint = null;
  draw();
}

function onSandboxUtilityMenuClick(evt) {
  const button = evt.target.closest('button[data-utility]');
  if (!button || !state.sandbox) return;
  const utilityType = button.dataset.utility;
  if (utilityType === 'cancel') {
    cancelSandboxUtilitySelection();
    return;
  }
  selectSandboxUtility(utilityType);
}

function selectSandboxUtility(utilityType) {
  if (!state.sandbox) return;
  state.sandbox.selectedUtilityType = utilityType;
  state.sandbox.awaitingUtilityLanding = true;
  state.sandbox.mode = 'select_landing';
  closeUtilityMenu();
  updateSandboxButtons();
  draw();
}

function cancelUtilityThrow() {
  cancelSandboxUtilitySelection();
}

function cancelSandboxUtilitySelection() {
  if (!state.sandbox) return;
  state.sandbox.selectedUtilityType = null;
  state.sandbox.awaitingUtilityLanding = false;
  state.sandbox.mode = 'idle';
  state.sandbox.selectedThrower = null;
  state.sandbox.selectedThrowerId = null;
  state.sandbox.menuAnchor = null;
  closeUtilityMenu();
  updateSandboxButtons();
  draw();
}

function onMapClickForUtilityLanding(point) {
  addSandboxUtility(point);
}

function clearSandboxUtilities() {
  if (!state.sandbox) return;
  state.sandbox.planned_utilities = [];
  state.sandbox.nextUtilityThrowTick = state.sandbox.source_tick;
  state.selectedUtility = null;
  sendRoomMessage('clear_utilities', {});
  markSandboxDirty();
  renderUtilityDetail();
  renderSideLists();
  draw();
}

function addSandboxUtility(point) {
  const thrower = state.sandbox.selectedThrower;
  const type = state.sandbox.selectedUtilityType;
  if (!thrower || !type) return;
  const throwTick = sandboxUtilityPlanningTick(state.sandbox);
  const detonateTick = throwTick + secondsToTicks(1.2);
  const throwRadar = { x: round2(Number(thrower.radar_x)), y: round2(Number(thrower.radar_y)) };
  const detonateRadar = { x: round2(point.x), y: round2(point.y) };
  const throwGame = radarToGame(throwRadar.x, throwRadar.y);
  const detonateGame = radarToGame(detonateRadar.x, detonateRadar.y);
  const cfg = getUtilityConfig(type);
  const expireTick = sandboxExpireTick(type, detonateTick, cfg);
  const utility = normalizeUtilityEvent({
    id: `sandbox_util_${Date.now()}_${Math.floor(Math.random() * 1000)}`,
    source: 'sandbox',
    round_number: state.currentRound,
    type,
    thrower: thrower.name,
    thrower_player_id: String(thrower.steamid || thrower.name || ''),
    thrower_team: thrower.team || null,
    throw_tick: throwTick,
    detonate_tick: detonateTick,
    expire_tick: expireTick,
    throw_pos: { x: round2(throwGame.x), y: round2(throwGame.y), z: null, game_x: round2(throwGame.x), game_y: round2(throwGame.y), radar_x: throwRadar.x, radar_y: throwRadar.y },
    detonate_pos: { x: round2(detonateGame.x), y: round2(detonateGame.y), z: null, game_x: round2(detonateGame.x), game_y: round2(detonateGame.y), radar_x: detonateRadar.x, radar_y: detonateRadar.y },
    radar_throw_pos: throwRadar,
    radar_detonate_pos: detonateRadar,
    trajectory: approximateTrajectory(throwTick, detonateTick, throwRadar, detonateRadar, throwGame, detonateGame),
    approximate_trajectory: true,
    effect: sandboxUtilityEffect(type, detonateTick, expireTick, detonateRadar, detonateGame, cfg),
    notes: '',
  }, 'sandbox');
  state.sandbox.planned_utilities.push(utility);
  state.sandbox.nextUtilityThrowTick = detonateTick;
  sendRoomMessage('create_utility', { utility, nextUtilityThrowTick: state.sandbox.nextUtilityThrowTick });
  renderSideLists();
  state.sandbox.selectedUtilityType = null;
  state.sandbox.awaitingUtilityLanding = false;
  state.sandbox.mode = 'idle';
  state.sandbox.selectedThrower = null;
  state.sandbox.selectedThrowerId = null;
  state.sandbox.menuAnchor = null;
  closeUtilityMenu();
  state.selectedUtility = utility;
  markSandboxDirty();
  renderUtilityDetail();
  draw();
}

function sandboxExpireTick(type, detonateTick, cfg) {
  if (type === 'flashbang') return detonateTick + secondsToTicks(cfg.flash_visual_duration_sec ?? 0.8);
  if (type === 'hegrenade') return detonateTick + secondsToTicks(Math.max(Number(cfg.blast_visual_duration_sec || 0.7), Number(cfg.smoke_visual_duration_sec || 2.5)));
  return detonateTick + secondsToTicks(cfg.duration_sec ?? 1);
}

function sandboxUtilityEffect(type, detonateTick, expireTick, radarPos, gamePos, cfg) {
  return {
    type,
    radius: type === 'hegrenade' ? cfg.damage_radius : type === 'flashbang' ? cfg.flash_fade_radius : cfg.radius,
    inner_radius: cfg.inner_radius,
    outer_radius: cfg.outer_radius || cfg.damage_radius || cfg.radius,
    damage_radius: cfg.damage_radius,
    flash_core_radius: cfg.flash_core_radius,
    flash_fade_radius: cfg.flash_fade_radius,
    fade_in_ticks: secondsToTicks(cfg.fade_in_sec ?? 0),
    fade_out_ticks: secondsToTicks(cfg.fade_out_sec ?? 0),
    start_tick: detonateTick,
    end_tick: expireTick,
    pos: { x: round2(gamePos.x), y: round2(gamePos.y), z: null },
    radar_pos: radarPos,
    target_players: [],
    blinded_players: [],
    damaged_players: [],
    used_demo_expire_tick: false,
    used_fallback_duration: true,
  };
}

function approximateTrajectory(throwTick, detonateTick, throwRadar, detonateRadar, throwGame, detonateGame) {
  const points = [];
  const steps = 14;
  for (let idx = 0; idx <= steps; idx += 1) {
    const t = idx / steps;
    const arc = Math.sin(t * Math.PI) * 45;
    points.push({
      tick: Math.round(throwTick + (detonateTick - throwTick) * t),
      pos: { x: round2(lerp(throwGame.x, detonateGame.x, t)), y: round2(lerp(throwGame.y, detonateGame.y, t)), z: round2(arc) },
      radar_pos: { x: round2(lerp(throwRadar.x, detonateRadar.x, t)), y: round2(lerp(throwRadar.y, detonateRadar.y, t) - arc * 0.12) },
    });
  }
  return points;
}

function radarToGame(x, y) {
  const scale = Number(state.manifest?.map?.scale) || 1;
  return {
    x: x * scale + Number(state.manifest?.map?.pos_x || 0),
    y: Number(state.manifest?.map?.pos_y || 0) - y * scale,
  };
}

function toggleSandboxPlayback() {
  if (!state.sandbox) return;
  if (state.sandbox.playing) stopSandboxPlayback({ suppressBroadcast: true });
  else playSandbox({ suppressBroadcast: true });
  updateSandboxButtons();
  broadcastSandboxTime();
  draw();
}

function playSandbox(options = {}) {
  if (!state.sandbox) return;
  stopSandboxPlayback({ suppressBroadcast: true });
  state.sandbox.playing = true;
  state.sandbox.playStartTime = performance.now();
  state.sandbox.playStartTick = state.sandbox.currentTick ?? state.sandbox.source_tick;
  state.sandbox.rafId = requestAnimationFrame(sandboxLoop);
  if (!options.suppressBroadcast) broadcastSandboxTime();
}

function stopSandboxPlayback(options = {}) {
  if (!state.sandbox) return;
  const wasPlaying = state.sandbox.playing;
  state.sandbox.playing = false;
  if (state.sandbox.rafId !== null && state.sandbox.rafId !== undefined) {
    cancelAnimationFrame(state.sandbox.rafId);
    state.sandbox.rafId = null;
  }
  if (wasPlaying && !options.suppressBroadcast) broadcastSandboxTime();
}

function sandboxLoop(now) {
  if (!state.sandbox?.playing) return;
  const elapsedSeconds = (now - state.sandbox.playStartTime) / 1000;
  state.sandbox.currentTick = state.sandbox.playStartTick + Math.floor(elapsedSeconds * getTickRate());
  const endTick = sandboxEndTick();
  if (Number.isFinite(endTick) && state.sandbox.currentTick >= endTick) {
    state.sandbox.currentTick = endTick;
    stopSandboxPlayback({ suppressBroadcast: true });
    broadcastSandboxTime();
    updateSandboxButtons();
    draw();
    return;
  }
  updateSandboxButtons();
  draw();
  state.sandbox.rafId = requestAnimationFrame(sandboxLoop);
}

function sandboxEndTick() {
  if (!state.sandbox) return null;
  const utilityEnd = Math.max(...(state.sandbox.planned_utilities || []).map(utility => getUtilityEffectWindow(utility).endTick).filter(Number.isFinite), state.sandbox.source_tick + secondsToTicks(8));
  return utilityEnd;
}

function resetSandboxTime() {
  if (!state.sandbox) return;
  stopSandboxPlayback({ suppressBroadcast: true });
  state.sandbox.currentTick = state.sandbox.source_tick;
  updateSandboxButtons();
  broadcastSandboxTime();
  draw();
}

function renderUtilityDetail() {
  const utility = state.selectedUtility;
  if (!utility) {
    const summary = state.manifest?.utility_summary;
    els.utilityDetail.textContent = summary ? `道具总数 ${summary.total}，精确轨迹 ${summary.precise}，fallback ${summary.approximate}。点击道具查看详情。` : '点击道具轨迹或效果圈查看详情。';
    return;
  }
  const effect = utility.effect || {};
  const blinded = (effect.blinded_players || effect.target_players || []).map(target => `${target.name || target.steamid}${target.duration ? ` ${target.duration}s` : ''}${target.approximate ? ' approx' : ''}`).filter(Boolean);
  const damaged = (effect.damaged_players || []).map(target => `${target.name || target.steamid}${target.damage ? ` -${target.damage}` : ''}`).filter(Boolean);
  const window = getUtilityEffectWindow(utility);
  const duration = Number.isFinite(window.startTick) && Number.isFinite(window.endTick) ? ((window.endTick - window.startTick) / getTickRate()).toFixed(1) : '-';
  els.utilityDetail.innerHTML = `
    <strong>${escapeHtml(utility.type)}</strong> · ${escapeHtml(utility.source || 'demo')} · ${utility.approximate_trajectory ? 'approximate 轨迹' : 'precise projectile 轨迹'}<br />
    投掷者：${escapeHtml(utility.thrower || utility.thrower_steamid || utility.thrower_player_id || '-')}<br />
    回合：R${utility.round_number ?? '-'} · throw ${utility.throw_tick ?? '-'} · detonate ${utility.detonate_tick ?? '-'} · expire ${utility.expire_tick ?? '-'} · ${duration}s<br />
    爆点：${utility.detonate_pos ? `${utility.detonate_pos.x}, ${utility.detonate_pos.y}` : '-'}<br />
    半径：${effect.radius ?? '-'} · demo expire：${effect.used_demo_expire_tick ? '是' : '否'} · fallback：${effect.used_fallback_duration ? '是' : '否'}<br />
    被闪：${escapeHtml(blinded.join(', ') || '-')}<br />
    伤害：${escapeHtml(damaged.join(', ') || '-')}
  `;
}

function resumeDemoPlayback() {
  if (!state.sandbox) return;
  if (!isRoomMode() && state.sandbox.dirty && !confirm('推演方案尚未保存，恢复播放会丢失未保存改动。继续吗？')) return;
  const round = state.sandbox.source_round_number ?? state.currentRound;
  const tick = state.sandbox.source_tick;
  exitSandboxLocal();
  sendRoomMessage('resume_replay', { round_number: round, tick, is_playing: true });
  switchToRound(round, { tick, autoplay: true, suppressBroadcast: isRoomMode() });
}

function resetSandboxToSource() {
  if (!state.sandbox || !state.roundData) return;
  const sourceFrame = state.roundData.frames[state.sandbox.source_frame_index];
  if (!sourceFrame) return;
  state.sandbox.tokens = JSON.parse(JSON.stringify(sourceFrame.players));
  state.sandbox.currentTick = state.sandbox.source_tick;
  state.sandbox.nextUtilityThrowTick = sandboxUtilityPlanningTick(state.sandbox);
  cancelSandboxUtilitySelection();
  sendRoomMessage('reset_sandbox_to_source', { tokens: state.sandbox.tokens, currentTick: state.sandbox.currentTick });
  markSandboxDirty();
  draw();
}

async function saveSandbox() {
  if (!state.sandbox) return;
  try {
    const payload = sandboxPayload();
    const result = await api(`/api/demos/${state.demoId}/sandbox`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    state.sandbox.dirty = false;
    updateSandboxButtons();
    setStatus(`推演方案已保存：${result.path}`);
  } catch (err) {
    console.error(err);
    setStatus(`保存失败：${err.message}`);
  }
}

function sandboxPayload() {
  const annotations = state.sandbox.annotations || [];
  return {
    schema_version: 1,
    demo_id: state.demoId,
    source_match_id: state.sandbox.source_match_id,
    source_round_number: state.sandbox.source_round_number,
    source_tick: state.sandbox.source_tick,
    source_frame_index: state.sandbox.source_frame_index,
    created_at: state.sandbox.created_at,
    objects: [...state.sandbox.tokens, ...annotations],
    notes: annotations.filter(ann => ann.type === 'text'),
    token_positions: state.sandbox.tokens,
    arrows: annotations.filter(ann => ann.type === 'arrow'),
    brush_strokes: annotations.filter(ann => ann.type === 'brush'),
    planned_utilities: state.sandbox.planned_utilities || [],
    nextUtilityThrowTick: state.sandbox.nextUtilityThrowTick ?? sandboxUtilityPlanningTick(state.sandbox),
    tokens: state.sandbox.tokens,
    annotations,
  };
}

function markSandboxDirty() {
  if (!state.sandbox) return;
  state.sandbox.dirty = true;
  updateSandboxButtons();
}

function updateSandboxButtons() {
  const inSandbox = Boolean(state.sandbox);
  els.resumeDemoBtn.disabled = !inSandbox;
  els.resetSandboxBtn.disabled = !inSandbox;
  els.saveSandboxBtn.disabled = !inSandbox;
  els.cancelUtilityThrowBtn.disabled = !inSandbox || state.sandbox?.mode === 'idle';
  els.clearSandboxUtilitiesBtn.disabled = !inSandbox || !(state.sandbox?.planned_utilities || []).length;
  els.playSandboxBtn.disabled = !inSandbox;
  els.resetSandboxTimeBtn.disabled = !inSandbox;
  els.playSandboxBtn.textContent = state.sandbox?.playing ? '暂停效果' : '播放效果';
  if (!inSandbox || state.sandbox?.mode !== 'utility_menu') closeUtilityMenu();
  else syncSandboxUtilityMenu();
  updateMapToolbar();
  els.sandboxSelectedPlayer.textContent = state.sandbox?.selectedThrower ? (state.sandbox.selectedThrower.name || state.sandbox.selectedThrower.steamid || '-') : '-';
  els.sandboxSelectedUtility.textContent = state.sandbox?.selectedUtilityType ? utilityLabel(state.sandbox.selectedUtilityType) : '-';
  if (!inSandbox) {
    els.sandboxStatus.textContent = '未进入推演模式。';
  } else if (state.sandbox.mode === 'select_landing') {
    els.sandboxStatus.textContent = '已选道具：点击地图选择落点，Esc 可取消。';
  } else if (state.sandbox.mode === 'utility_menu') {
    els.sandboxStatus.textContent = '已选人物：在地图旁菜单选择道具，Esc 可取消。';
  } else {
    els.sandboxStatus.textContent = '未选人：点击人物 token 选择投掷者。';
  }
}

function utilityLabel(type) {
  return { smoke: '烟雾弹', flashbang: '闪光弹', hegrenade: 'HE手雷', molotov: '燃烧弹', decoy: 'Decoy' }[type] || type || '-';
}

function updateNavigationButtons() {
  const loaded = Boolean(state.roundData && state.replayIndex && state.currentRound !== null);
  const inSandbox = Boolean(state.sandbox);
  const pos = loaded ? state.replayIndex.roundPositionByNumber.get(state.currentRound) : undefined;
  els.prevRoundBtn.disabled = !loaded || inSandbox || pos === undefined || pos <= 0;
  els.nextRoundBtn.disabled = !loaded || inSandbox || pos === undefined || pos >= state.replayIndex.roundNumbers.length - 1;
  els.back5Btn.disabled = !loaded || inSandbox;
  els.forward5Btn.disabled = !loaded || inSandbox;
  els.playBtn.disabled = !loaded || inSandbox || state.playing;
  els.pauseBtn.disabled = !loaded || inSandbox || !state.playing;
  els.roundSelect.disabled = !loaded || inSandbox;
  els.timeline.disabled = !loaded || inSandbox;
}

function clampTick(tick, roundNumber) {
  const range = getRoundRange(roundNumber);
  let result = Number(tick);
  if (!Number.isFinite(result)) result = range.startTick ?? 0;
  if (Number.isFinite(range.startTick)) result = Math.max(range.startTick, result);
  if (Number.isFinite(range.endTick)) result = Math.min(range.endTick, result);
  return result;
}

function toFiniteNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function ticksToSeconds(ticks) {
  return Math.max(0, ticks / getTickRate());
}

function formatSeconds(seconds) {
  const total = Math.max(0, Math.floor(seconds));
  const minutes = Math.floor(total / 60);
  const secs = String(total % 60).padStart(2, '0');
  return `${minutes}:${secs}`;
}

function distance(x1, y1, x2, y2) {
  const dx = x1 - x2;
  const dy = y1 - y2;
  return Math.sqrt(dx * dx + dy * dy);
}

function lerp(a, b, t) { return a + (b - a) * t; }
function round2(value) { return Math.round(value * 100) / 100; }
function escapeHtml(str) {
  return String(str).replace(/[&<>'"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[ch]));
}

init().catch(err => {
  console.error(err);
  setStatus(`初始化失败：${err.message}`);
});
