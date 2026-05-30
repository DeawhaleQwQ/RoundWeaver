// Demo analysis page: read-only over existing replay.json export.
// Renders player stats + findings with side/team/finding-type filters.
const api = async (path, options = {}) => {
  const res = await fetch(path, options);
  if (!res.ok) throw new Error(`${res.status} ${await res.text().catch(() => '')}`);
  return res.json();
};
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

const els = {
  demoSelect: document.getElementById('analysisDemoSelect'),
  side: document.getElementById('analysisSide'),
  team: document.getElementById('analysisTeam'),
  status: document.getElementById('analysisStatus'),
  openReplay: document.getElementById('openReplayBtn'),
  statsTable: document.getElementById('playerStatsTable'),
  findings: document.getElementById('findingsList'),
  ft: Array.from(document.querySelectorAll('.ft')),
};

const state = { demoId: null, manifest: null, teams: [], memberIdentities: null };

function ftEnabled(type) {
  const t = String(type || '').toLowerCase();
  const on = (key) => els.ft.find(c => c.dataset.ft === key)?.checked !== false;
  if (t.includes('trade')) return on('trade');
  if (t.includes('entry')) return on('entry');
  if (t.includes('stall')) return on('stall');
  if (t.includes('postplant') || t.includes('post_plant')) return on('postplant');
  return true;
}

function normName(s) { return String(s ?? '').trim().toLowerCase(); }

function selectedIdentitySet() {
  // Returns {steamids:Set, names:Set} for the selected team, or null for 'all'.
  if (els.team.value === 'all') return null;
  const team = state.teams.find(t => t.team_id === els.team.value);
  if (!team) return null;
  const steamids = new Set();
  const names = new Set();
  for (const m of team.members || []) {
    if (m.steamid) steamids.add(String(m.steamid));
    names.add(normName(m.display_name));
    for (const a of m.aliases || []) names.add(normName(a));
  }
  return { steamids, names };
}

function matchesIdentity(steamid, name, idset) {
  if (!idset) return true;
  if (steamid && idset.steamids.has(String(steamid))) return true;
  return idset.names.has(normName(name));
}

function renderPlayerStats() {
  const stats = state.manifest?.match?.player_stats || [];
  const side = els.side.value;
  const idset = selectedIdentitySet();
  const rows = stats.filter(p =>
    (side === 'all' || String(p.team).toUpperCase() === side) &&
    matchesIdentity(p.steamid, p.name, idset)
  );
  if (!rows.length) { els.statsTable.innerHTML = '<div class="hint">无匹配玩家。</div>'; return; }
  els.statsTable.innerHTML = `
    <table class="stats">
      <thead><tr><th>玩家</th><th>队</th><th>K</th><th>D</th><th>A</th><th>ADR</th><th>HS%</th><th>首杀</th><th>首死</th></tr></thead>
      <tbody>
        ${rows.map(p => `<tr>
          <td>${esc(p.name)}</td><td>${esc(p.team)}</td>
          <td>${p.kills ?? 0}</td><td>${p.deaths ?? 0}</td><td>${p.assists ?? 0}</td>
          <td>${p.adr ?? 0}</td><td>${p.hs_percent ?? 0}</td>
          <td>${p.first_kills ?? 0}</td><td>${p.first_deaths ?? 0}</td>
        </tr>`).join('')}
      </tbody>
    </table>`;
}

function findingMatchesIdentity(finding, idset) {
  if (!idset) return true;
  for (const p of finding.players || []) {
    const sid = typeof p === 'object' ? p.steamid : null;
    const nm = typeof p === 'object' ? p.name : p;
    if (matchesIdentity(sid, nm, idset)) return true;
  }
  return false;
}

function renderFindings() {
  const findings = state.manifest?.findings || [];
  const side = els.side.value;
  const idset = selectedIdentitySet();
  const rows = findings.filter(f =>
    (side === 'all' || String(f.team).toUpperCase() === side) &&
    ftEnabled(f.finding_type) &&
    findingMatchesIdentity(f, idset)
  );
  if (!rows.length) { els.findings.innerHTML = '<div class="hint">无匹配 finding。</div>'; return; }
  els.findings.innerHTML = rows.map(f => `
    <div class="finding-card ${esc(f.sentiment || '')}">
      <div class="finding-title">${esc(f.title || f.finding_type)}</div>
      <div class="finding-meta">R${f.round_number} · ${esc(f.team || '-')}</div>
      <div class="finding-message">${esc(f.message || '')}</div>
    </div>`).join('');
}

function renderAll() { renderPlayerStats(); renderFindings(); }

async function loadDemo(demoId) {
  els.status.textContent = '加载中…';
  try {
    await api(`/api/demos/${encodeURIComponent(demoId)}/prepare`, { method: 'POST' });
    state.manifest = await api(`/api/demos/${encodeURIComponent(demoId)}/replay.json`);
    state.demoId = demoId;
    els.status.textContent = `${demoId} · ${(state.manifest.rounds || []).length} 回合`;
    renderAll();
  } catch (err) {
    console.error(err);
    els.status.textContent = '加载失败';
  }
}

async function loadTeams() {
  try {
    const payload = await api('/api/teams');
    // fetch full members for identity sets
    state.teams = await Promise.all((payload.teams || []).map(async t => (await api(`/api/teams/${encodeURIComponent(t.team_id)}`)).team));
    els.team.innerHTML = '<option value="all">全部</option>' +
      state.teams.map(t => `<option value="${esc(t.team_id)}">${esc(t.name)}</option>`).join('');
  } catch (err) {
    console.error(err);
  }
}

els.demoSelect.addEventListener('change', () => loadDemo(els.demoSelect.value));
els.side.addEventListener('change', renderAll);
els.team.addEventListener('change', renderAll);
els.ft.forEach(c => c.addEventListener('change', renderFindings));
els.openReplay.addEventListener('click', () => { if (state.demoId) window.location.href = '/replay'; });

(async () => {
  renderTopNav('analysis');
  await loadTeams();
  const payload = await api('/api/demos');
  const demos = payload.demos || [];
  els.demoSelect.innerHTML = demos.map(d => `<option value="${esc(d.demo_id)}">${esc(d.filename)}</option>`).join('');
  const defaultDemo = payload.default_demo_id || demos[0]?.demo_id;
  if (defaultDemo) { els.demoSelect.value = defaultDemo; await loadDemo(defaultDemo); }
})();
