// Teams page: list / create / edit teams and their members.
// Vanilla JS, talks to /api/teams. Member profile editing (notebook) is Batch 5.
const api = async (path, options = {}) => {
  const res = await fetch(path, options);
  if (!res.ok) throw new Error(`${res.status} ${await res.text().catch(() => '')}`);
  return res.status === 204 ? null : res.json();
};
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

const els = {
  teamList: document.getElementById('teamList'),
  newTeamBtn: document.getElementById('newTeamBtn'),
  editor: document.getElementById('teamEditor'),
  editorTitle: document.getElementById('teamEditorTitle'),
  editorStatus: document.getElementById('teamEditorStatus'),
  nameInput: document.getElementById('teamNameInput'),
  memberRows: document.getElementById('memberRows'),
  addMemberBtn: document.getElementById('addMemberBtn'),
  saveBtn: document.getElementById('saveTeamBtn'),
  deleteBtn: document.getElementById('deleteTeamBtn'),
  profile: document.getElementById('memberProfile'),
  profileTitle: document.getElementById('memberProfileTitle'),
  profileStatus: document.getElementById('memberProfileStatus'),
  profileMeta: document.getElementById('memberProfileMeta'),
  profileNbTitle: document.getElementById('profileNotebookTitle'),
  profileNbBody: document.getElementById('profileNotebookBody'),
  saveProfileBtn: document.getElementById('saveProfileBtn'),
  closeProfileBtn: document.getElementById('closeProfileBtn'),
};

const state = { teams: [], current: null, profileMember: null, profileNotebookId: null };

function teamIdFromUrl() {
  const m = window.location.pathname.match(/^\/teams\/([^/]+)\/?$/);
  return m ? decodeURIComponent(m[1]) : null;
}

async function loadTeams() {
  const payload = await api('/api/teams');
  state.teams = payload.teams || [];
  renderTeamList();
}

function renderTeamList() {
  els.teamList.innerHTML = '';
  if (!state.teams.length) {
    els.teamList.innerHTML = '<div class="hint">还没有战队，点“新建战队”创建一个。</div>';
    return;
  }
  for (const team of state.teams) {
    const card = document.createElement('div');
    card.className = `team-card ${team.team_id === state.current?.team_id ? 'active' : ''}`;
    card.innerHTML = `
      <div class="team-card-name">${esc(team.name)}</div>
      <div class="team-card-meta">${team.member_count} 名成员</div>`;
    card.addEventListener('click', () => openTeam(team.team_id));
    els.teamList.appendChild(card);
  }
}

function memberRow(member = {}) {
  const row = document.createElement('div');
  row.className = 'member-row';
  row.dataset.memberId = member.member_id || '';
  row.innerHTML = `
    <input class="m-name" type="text" maxlength="60" placeholder="昵称" value="${esc(member.display_name || '')}" />
    <input class="m-steamid" type="text" placeholder="SteamID64（可选）" value="${esc(member.steamid || '')}" />
    <input class="m-aliases" type="text" placeholder="别名，逗号分隔（可选）" value="${esc((member.aliases || []).join(', '))}" />
    <button class="m-profile" type="button" title="编辑画像">档案</button>
    <button class="m-remove" type="button" title="移除">✕</button>`;
  row.querySelector('.m-remove').addEventListener('click', () => row.remove());
  row.querySelector('.m-profile').addEventListener('click', () => openMemberProfile(member.member_id));
  return row;
}

function collectMembers() {
  return Array.from(els.memberRows.querySelectorAll('.member-row')).map(row => ({
    member_id: row.dataset.memberId || undefined,
    display_name: row.querySelector('.m-name').value.trim(),
    steamid: row.querySelector('.m-steamid').value.trim() || null,
    aliases: row.querySelector('.m-aliases').value.split(',').map(s => s.trim()).filter(Boolean),
  })).filter(m => m.display_name || m.steamid);
}

function showEditor(team) {
  state.current = team;
  els.editor.hidden = false;
  els.editorTitle.textContent = team.team_id ? '编辑战队' : '新建战队';
  els.editorStatus.textContent = '';
  els.nameInput.value = team.name || '';
  els.memberRows.innerHTML = '';
  for (const m of team.members || []) els.memberRows.appendChild(memberRow(m));
  if (!(team.members || []).length) els.memberRows.appendChild(memberRow());
  renderTeamList();
}

async function openTeam(teamId) {
  try {
    const payload = await api(`/api/teams/${encodeURIComponent(teamId)}`);
    history.replaceState(null, '', `/teams/${encodeURIComponent(teamId)}`);
    showEditor(payload.team);
  } catch (err) {
    console.error(err);
  }
}

function newTeam() {
  history.replaceState(null, '', '/teams');
  showEditor({ name: '', members: [] });
}

async function saveTeam() {
  const body = { name: els.nameInput.value.trim() || '未命名战队', members: collectMembers() };
  try {
    let team;
    if (state.current?.team_id) {
      team = (await api(`/api/teams/${encodeURIComponent(state.current.team_id)}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
      })).team;
    } else {
      team = (await api('/api/teams', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
      })).team;
      history.replaceState(null, '', `/teams/${encodeURIComponent(team.team_id)}`);
    }
    state.current = team;
    await loadTeams();
    showEditor(team);
    els.editorStatus.textContent = '已保存';
  } catch (err) {
    console.error(err);
    els.editorStatus.textContent = '保存失败';
  }
}

async function deleteTeam() {
  if (!state.current?.team_id) { els.editor.hidden = true; return; }
  if (!confirm('删除这个战队？此操作不可撤销。')) return;
  try {
    await api(`/api/teams/${encodeURIComponent(state.current.team_id)}`, { method: 'DELETE' });
    state.current = null;
    els.editor.hidden = true;
    history.replaceState(null, '', '/teams');
    await loadTeams();
  } catch (err) {
    console.error(err);
    els.editorStatus.textContent = '删除失败';
  }
}

async function openMemberProfile(memberId) {
  if (!state.current?.team_id || !memberId) {
    alert('请先保存战队，再编辑成员画像。');
    return;
  }
  // reload team to get authoritative member + profile_notebook_id
  const team = (await api(`/api/teams/${encodeURIComponent(state.current.team_id)}`)).team;
  state.current = team;
  const member = (team.members || []).find(m => m.member_id === memberId);
  if (!member) { alert('未找到该成员，请先保存战队。'); return; }
  state.profileMember = member;
  els.profile.hidden = false;
  els.profileTitle.textContent = `成员画像 · ${member.display_name}`;
  els.profileStatus.textContent = '';
  els.profileMeta.innerHTML = `SteamID：${esc(member.steamid || '—')}　别名：${esc((member.aliases || []).join(', ') || '—')}`;
  try {
    let notebookId = member.profile_notebook_id;
    if (notebookId) {
      const nb = (await api(`/api/notebooks/${encodeURIComponent(notebookId)}`)).notebook;
      els.profileNbTitle.value = nb.title || '';
      els.profileNbBody.value = nb.body || '';
    } else {
      // create a profile notebook bound to this member
      const nb = (await api('/api/notebooks', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: `${member.display_name} 画像`, body: '', owner_member_id: member.member_id }),
      })).notebook;
      notebookId = nb.notebook_id;
      member.profile_notebook_id = notebookId;
      // persist the pointer on the team
      await api(`/api/teams/${encodeURIComponent(team.team_id)}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ members: team.members }),
      });
      els.profileNbTitle.value = nb.title || '';
      els.profileNbBody.value = nb.body || '';
    }
    state.profileNotebookId = notebookId;
  } catch (err) {
    console.error(err);
    els.profileStatus.textContent = '画像加载失败';
  }
}

async function saveMemberProfile() {
  if (!state.profileNotebookId) return;
  try {
    await api(`/api/notebooks/${encodeURIComponent(state.profileNotebookId)}`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: els.profileNbTitle.value.trim() || `${state.profileMember?.display_name || '成员'} 画像`, body: els.profileNbBody.value }),
    });
    els.profileStatus.textContent = '已保存';
  } catch (err) {
    console.error(err);
    els.profileStatus.textContent = '保存失败';
  }
}

function closeMemberProfile() {
  els.profile.hidden = true;
  state.profileMember = null;
  state.profileNotebookId = null;
}

els.newTeamBtn.addEventListener('click', newTeam);
els.addMemberBtn.addEventListener('click', () => els.memberRows.appendChild(memberRow()));
els.saveBtn.addEventListener('click', saveTeam);
els.deleteBtn.addEventListener('click', deleteTeam);
els.saveProfileBtn.addEventListener('click', saveMemberProfile);
els.closeProfileBtn.addEventListener('click', closeMemberProfile);

(async () => {
  renderTopNav('teams');
  await loadTeams();
  const tid = teamIdFromUrl();
  if (tid) await openTeam(tid);
})();
