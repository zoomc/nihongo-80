(function () {
  'use strict';
  const release = document.querySelector('meta[name="nh80-version"]').content;
  let checking = false;
  let updating = false;
  function replace(version) {
    if (!/^[0-9a-f]{12}$/.test(version) || version === release) return false;
    if (new URL(location.href).searchParams.get('release') === version) return false;
    if (!updating) {
      updating = true;
      function reload() {
        if (document.documentElement.dataset.savingLesson) { setTimeout(reload, 400); return; }
        const url = new URL(location.href);
        url.searchParams.set('release', version);
        location.replace(url);
      }
      reload();
    }
    return true;
  }
  async function check() {
    if (checking || updating || !navigator.onLine) return;
    checking = true;
    try {
      const response = await fetch('/api/app-version', {cache:'no-store', signal:AbortSignal.timeout(5000)});
      if (response.ok) replace((await response.json()).version);
    } catch {} finally { checking = false; }
  }
  const url = new URL(location.href);
  if (url.searchParams.get('release') === release) {
    url.searchParams.delete('release');
    history.replaceState(history.state, '', url);
  }
  window.NHVersion = {checkPage(page) {
    const version = page.querySelector('meta[name="nh80-version"]')?.content;
    if (version && version !== release) { check(); return true; }
    return false;
  }};
  window.addEventListener('pageshow', check);
  window.addEventListener('online', check);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) check(); });
  setInterval(() => { if (!document.hidden) check(); }, 60000);
  check();
})();
