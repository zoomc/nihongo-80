(function () {
  'use strict';
  const ownerKey = 'nh80.sync.owner';
  const pendingKey = 'nh80.sync.pending';
  const codeKey = 'nh80.sync.code';
  const read = key => { try { return localStorage.getItem(key); } catch { return null; } };
  const write = (key, value) => { try { localStorage.setItem(key, value); } catch {} };
  const drop = key => { try { localStorage.removeItem(key); } catch {} };

  // 同步链接把凭证放在 #s= 片段里：fragment 不会发送给服务器，也不进 Referer。
  // 读到后立刻从地址栏抹掉，再存本机；之后这台设备自动登录，无需再输入。
  function takeLinkCode() {
    const raw = location.hash.replace(/^#/, '');
    if (!raw) return '';
    const value = (new URLSearchParams(raw).get('s') || '').trim().toLowerCase();
    if (!/^[0-9a-f]{64}$/.test(value)) return '';
    history.replaceState(null, '', location.pathname + location.search);
    return value;
  }

  let owner = read(ownerKey);
  let code = read(codeKey) || '';
  let session = false;
  let running;
  let changed = false;
  let switching = false;
  let authFailedAt = 0;
  let linkCode = takeLinkCode() || read(pendingKey) || '';
  if (linkCode) write(pendingKey, linkCode);

  const status = document.getElementById('accountStatus');
  const form = document.getElementById('accountLogin');
  const logout = document.getElementById('accountLogout');
  const create = document.getElementById('accountCreate');
  const copy = document.getElementById('accountCopy');
  const copyLink = document.getElementById('accountCopyLink');

  async function call(action, body) {
    const options = body === undefined ? {} : {
      method: 'POST', headers: {'content-type': 'application/json'}, body: JSON.stringify(body)
    };
    const response = await fetch('/api/account/' + action, {...options, cache:'no-store', signal:AbortSignal.timeout(9000)});
    if (!response.ok) {
      const result = await response.json().catch(() => ({}));
      throw Error(result.reason === 'different_account' ? result.reason : String(response.status));
    }
    return response.json();
  }

  function display(message) {
    if (status) status.textContent = message;
    if (logout) logout.hidden = !session;
    if (create) create.hidden = session || Boolean(owner);
    if (form) form.hidden = session;
    if (copyLink) copyLink.hidden = !(session && code);
  }

  async function authenticate(value, createAccount = false) {
    const expected = read(ownerKey) || owner;
    const fields = {code: value, ...(expected ? {expected} : {})};
    let account;
    try {
      account = (await call('login', {...fields, ...(createAccount ? {create: true} : {})})).account;
    } catch (error) {
      if (!createAccount || error.message !== '409') throw error;
      account = (await call('login', fields)).account;
    }
    write(ownerKey, account);
    write(codeKey, value);
    owner = account;
    code = value;
    session = true;
    authFailedAt = 0;
    return account;
  }

  async function sync() {
    if (switching || running) return running;
    if (!session && !code) return;
    running = (async () => {
      for (let attempt = 0; attempt < 2; attempt++) {
        try {
          const remote = await call('state');
          if (switching) return;
          if (!owner) { write(ownerKey, remote.account); owner = remote.account; }
          if (owner !== remote.account) throw Error('different_account');
          session = true;
          changed = false;
          const state = NHCourse.snapshot();
          const remoteDays = new Set(remote.days);
          const upload = state.opened > remote.opened || state.days.some(day => !remoteDays.has(day));
          const merged = upload ? await call('state', {...state, account:owner}) : remote;
          if (merged.account !== owner) throw Error('different_account');
          NHCourse.applyCloud(merged);
          display('已绑定 · 进度已同步');
          return;
        } catch (error) {
          // Cookie 过期自动恢复：本机存着凭证就重新换一次会话。
          if (attempt === 0 && error.message === '401' && code && Date.now() - authFailedAt > 300000) {
            try { await authenticate(code, false); continue; }
            catch (retry) { error = retry; authFailedAt = Date.now(); }
          }
          if (error.message === '401' || error.message === 'different_account') {
            session = false;
            display('未绑定 · 进度只保存在此设备');
          } else {
            display('暂时无法同步，进度已保存在此设备');
          }
          return;
        }
      }
    })().finally(() => {
      running = null;
      if (changed && session && !switching) { changed = false; sync(); }
    });
    return running;
  }

  async function login(value, isNew) {
    if (switching) return;
    switching = true;
    try { await running; } catch {}
    form && (form.querySelector('button').disabled = create.disabled = true);
    try {
      await authenticate(value, isNew);
      linkCode = '';
      drop(pendingKey);
      if (isNew) {
        if (copy) { copy.hidden = false; copy.value = value; copy.select(); }
      }
      if (form) form.reset();
      display('已绑定 · 正在同步…');
    } catch (error) {
      const messages = {'401':'登录码无效。', '429':'创建次数已达上限，请明天再试。',
        different_account:'此浏览器的学习记录属于另一个同步账号。请用原同步链接，或在独立浏览器中绑定。'};
      display(messages[error.message] || '暂时无法登录，请重试。');
    } finally {
      switching = false;
      if (form) form.querySelector('button').disabled = create.disabled = false;
    }
    if (session) sync();
  }

  async function start() {
    if (switching) return;
    const incoming = takeLinkCode();
    if (incoming) { linkCode = incoming; write(pendingKey, incoming); }
    if (!linkCode) return sync();
    switching = true;
    try {
      await running;
      await authenticate(linkCode);
      linkCode = '';
      drop(pendingKey);
      display('已绑定 · 正在同步…');
    } catch (error) {
      if (error.message === '401' || error.message === '400' || error.message === 'different_account') {
        linkCode = '';
        drop(pendingKey);
        display(error.message === 'different_account'
          ? '此浏览器的学习记录属于另一个同步账号。请在独立浏览器中打开此链接。'
          : '同步链接已失效，请从已绑定设备重新复制。');
      } else {
        display('暂时无法绑定，将在重新联网后重试。');
      }
      return;
    } finally {
      switching = false;
    }
    return sync();
  }

  if (form) form.addEventListener('submit', event => {
    event.preventDefault();
    login(form.elements.loginCode.value.trim().toLowerCase(), false);
  });
  if (create) create.onclick = () => login([...crypto.getRandomValues(new Uint8Array(32))]
    .map(byte => byte.toString(16).padStart(2, '0')).join(''), true);
  if (copyLink) copyLink.onclick = async () => {
    if (!code) return;
    const url = location.origin + '/#s=' + code;
    try {
      await navigator.clipboard.writeText(url);
      display('已复制同步链接 · 在另一台设备打开一次即可');
    } catch {
      if (copy) { copy.hidden = false; copy.value = url; copy.select(); }
      display('请手动复制下面这段链接');
    }
  };
  if (logout) logout.onclick = async () => {
    if (switching) return;
    switching = true;
    try {
      await running;
      await call('logout', {});
      session = false;
      code = '';
      linkCode = '';
      drop(pendingKey);
      drop(codeKey);
      if (copy) { copy.value = ''; copy.hidden = true; }
      display('已退出 · 进度只保存在此设备');
    } catch { display('退出失败，请联网后重试。'); }
    finally { switching = false; }
  };

  display(owner && !code ? '已退出 · 进度只保存在此设备' : '进度保存在此设备');
  window.NHSync = {start};
  window.addEventListener('hashchange', start);
  window.addEventListener('nh80-course-change', () => {
    if (!session) return;
    changed = true;
    sync();
  });
  window.addEventListener('online', start);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) start(); });
  setInterval(() => { if (!document.hidden) start(); }, 30000);
})();
