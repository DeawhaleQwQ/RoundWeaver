// Shared top navigation for RoundWeaver multi-page shell.
// Vanilla JS, no framework. Each page calls renderTopNav(active) on load.
(function () {
  const NAV_ITEMS = [
    { key: 'home', label: '首页', href: '/' },
    { key: 'replay', label: '回放', href: '/replay' },
    { key: 'analysis', label: 'Demo 分析', href: '/analysis' },
    { key: 'teams', label: '战队', href: '/teams' },
  ];

  function renderTopNav(active) {
    const mount = document.getElementById('topNav');
    if (!mount) return;
    mount.innerHTML = '';
    const brand = document.createElement('a');
    brand.className = 'topnav-brand';
    brand.href = '/';
    brand.textContent = 'RoundWeaver';
    mount.appendChild(brand);
    const links = document.createElement('nav');
    links.className = 'topnav-links';
    for (const item of NAV_ITEMS) {
      const a = document.createElement('a');
      a.className = `topnav-link ${item.key === active ? 'active' : ''}`;
      a.href = item.href;
      a.textContent = item.label;
      links.appendChild(a);
    }
    mount.appendChild(links);
  }

  window.renderTopNav = renderTopNav;
})();
