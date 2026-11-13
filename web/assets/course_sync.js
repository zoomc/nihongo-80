(function () {
  'use strict';
  const ownerKey = 'nh80.sync.owner';
  let owner;
  try { owner = localStorage.getItem(ownerKey); } catch {}
  let session = false;
  let running;
  let changed = false;
  let switching = false;
  const status = document.getElementById('accountStatus');
  const form = document.getElementById('accountLogin');
  const logout = document.getElementById('accountLogout');
  const create = document.getElementById('accountCreate');
  const copy = document.getElementById('accountCopy');

  async function call(action, body) {
    const options = body === undefined ? {} : {
      method: 'POST', headers: {'content-type': 'application/json'}, body: JSON.stringify(body)
    };
    const response = await fetch('/api/account/' + action, {...options, cache:'no-store', signal:AbortSignal.timeout(9000)});
    if (!response.ok) throw Error(String(response.status));
    return response.json();
  }

  function remember(id) {
    if (owner && owner !== id) throw Error('different_account');
    localStorage.setItem(ownerKey, id);
    owner = id;
  }

  function display(message) {
    status.textContent = message;
    logout.hidden = !session;
    create.hidden = session || !!owner;
    form.hidden = session;
  }

  async function sync() {
    if (switching || running) return running;
    running = (async () => {
      try {
        const remote = await call('state');
        if (switching) return;
        if (!owner) remember(remote.account);
        if (owner !== remote.account) throw Error('different_account');
        session = true;
        changed = false;
        const state = NHCourse.snapshot();
        const remoteDays = new Set(remote.days);
        const upload = state.opened > remote.opened || state.days.some(day => !remoteDays.has(day));
        const merged = upload ? await call('state', {...state, account:owner}) : remote;
        if (merged.account !== owner) throw Error('different_account');
        NHCourse.applyCloud(merged);
        display('已登录 · 进度已同步');
      } catch (error) {
        if (error.message === '401' || error.message === 'different_account') {
          session = false;
          display('未登录 · 进度保存在此设备');
        } else {
          display('暂时无法同步，进度已保存在此设备');
        }
      }
    })().finally(() => {
      running = null;
      if (changed && session && !switching) { changed = false; sync(); }
    });
    return running;
  }

  async function login(code, isNew) {
    if (switching) return;
    switching = true;
    form.querySelector('button').disabled = create.disabled = true;
    try {
      await running;
      const id = [...new Uint8Array(await crypto.subtle.digest('SHA-256',
        new TextEncoder().encode('nh80-account:' + code)))].map(byte => byte.toString(16).padStart(2, '0')).join('');
      if (owner && owner !== id) throw Error('different_account');
      const result = await call('login', {code, create:isNew});
      remember(result.account);
      session = true;
      if (isNew) {
        copy.hidden = false;
        copy.value = code;
        copy.select();
      }
      form.reset();
    } catch (error) {
      const messages = {'401':'登录码无效。', '429':'创建次数已达上限，请明天再试。',
        different_account:'此浏览器已关联另一个同步账号。请在独立浏览器或浏览器配置中使用其他账号。'};
      display(messages[error.message] || '暂时无法登录，请重试。');
    } finally {
      switching = false;
      form.querySelector('button').disabled = create.disabled = false;
    }
    if (session) sync();
  }

  form.addEventListener('submit', event => {
    event.preventDefault();
    login(form.elements.loginCode.value.trim().toLowerCase(), false);
  });
  create.onclick = () => login([...crypto.getRandomValues(new Uint8Array(32))]
    .map(byte => byte.toString(16).padStart(2, '0')).join(''), true);
  logout.onclick = async () => {
    if (switching) return;
    switching = true;
    try {
      await running;
      await call('logout', {});
      session = false;
      copy.value = '';
      copy.hidden = true;
      display('已退出 · 进度保存在此设备');
    } catch { display('退出失败，请联网后重试。'); }
    finally { switching = false; }
  };

  window.NHSync = {start:sync};
  window.addEventListener('nh80-course-change', () => {
    if (!session) return;
    changed = true;
    sync();
  });
  window.addEventListener('online', sync);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) sync(); });
  setInterval(() => { if (!document.hidden) sync(); }, 30000);
})();
