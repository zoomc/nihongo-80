(function () {
  'use strict';
  const route = /^\/(?:index\.html|day-(?:00[1-9]|0[1-9]\d|1[0-4]\d|150)\.html|review\.html|flashcards\.html)?$/;
  const main = () => document.querySelector('main');
  let active;
  let request;
  let studyScript;
  let displayed = new URL(location.href);

  function home(root, signal) {
    const resume = root.querySelector('#resume');
    if (!resume) return;
    const dayLabel = day => 'Day ' + String(day).padStart(3, '0');
    const next = NHCourse.next();
    const last = NHCourse.last();
    resume.hidden = !next;
    root.querySelector('#courseDone').hidden = !!next;
    if (next) {
      resume.href = '/day-' + dayLabel(next).slice(4) + '.html';
      resume.textContent = (next === 1 ? '开始 ' : '开始下一课 · ') + dayLabel(next);
    }
    const previous = root.querySelector('#previousLesson');
    previous.hidden = !last;
    if (!previous.hidden) {
      previous.href = '/day-' + dayLabel(last).slice(4) + '.html';
      previous.textContent = (NHCourse.done(last) ? '回看 ' : '继续 ') + dayLabel(last);
    }
    root.querySelectorAll('.home-weeks details').forEach(group => {
      const day = next || last || 150;
      group.open = day >= Number(group.dataset.start) && day <= Number(group.dataset.end);
    });
    const form = root.querySelector('#progressImport');
    form.elements.code.value = NHCourse.code();
    form.addEventListener('submit', event => {
      event.preventDefault();
      const status = root.querySelector('#progressStatus');
      if (!NHCourse.merge(form.elements.code.value)) {
        status.textContent = '进度码格式有误，请从原设备重新复制。';
        return;
      }
      mount();
      root.querySelector('#progressStatus').textContent = '已合并本机进度。';
    }, {signal});
  }

  function mount() {
    active?.abort();
    active = new AbortController();
    const {signal} = active;
    const root = main();
    const day = Number(document.body.dataset.day) || 0;
    const path = location.pathname;
    const current = path === '/flashcards.html' ? 'flash' : path === '/review.html' ? 'review' : 'course';
    document.querySelectorAll('.app-nav [data-tab]').forEach(link => {
      if (link.dataset.tab === current) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
    });
    if (day) NHCourse.open(day);
    home(root, signal);
    window.mountLesson(root, day, window.__PAGE__ || {}, signal);
    if (current === 'review') {
      studyScript ||= import('/assets/study.js').catch(error => { studyScript = null; throw error; });
      studyScript.then(() => {
        if (!signal.aborted) window.mountStudy();
      }).catch(() => {
        const review = root.querySelector('#scheduledReview');
        if (!signal.aborted) review.querySelector('p').textContent = '暂时无法加载复习，请联网后重新打开。';
      });
    }
    if (current === 'flash') window.mountFlashcards(root, signal);
  }

  function position(url, focus) {
    const target = url.hash && document.getElementById(url.hash.slice(1));
    if (target) target.scrollIntoView();
    else window.scrollTo(0, 0);
    if (focus) (target || main().querySelector('h1'))?.focus({preventScroll:true});
  }

  async function navigate(url, historyMode, focus = true) {
    request?.abort();
    request = null;
    const status = document.getElementById('appStatus');
    if (url.pathname === displayed.pathname) {
      status.textContent = '';
      if (historyMode === 'push' && url.href !== location.href) history.pushState(null, '', url);
      displayed = url;
      position(url, focus);
      return;
    }
    const controller = new AbortController();
    request = controller;
    status.textContent = '正在打开…';
    try {
      const response = await fetch(url.pathname, {signal:controller.signal});
      if (!response.ok) throw Error('页面不可用');
      const next = new DOMParser().parseFromString(await response.text(), 'text/html');
      if (window.NHVersion.checkPage(next)) return;
      const content = next.querySelector('main');
      if (!content) throw Error('页面内容不可用');
      const meta = next.querySelector('#lessonMeta');
      const page = meta ? JSON.parse(meta.textContent) : {};
      if (controller.signal.aborted) return;
      const day = next.body.dataset.day || '0';
      if (historyMode === 'push') history.pushState(null, '', url);
      if (historyMode === 'replace') history.replaceState(null, '', url);
      displayed = url;
      document.title = next.title;
      document.body.dataset.day = day;
      window.__PAGE__ = page;
      main().replaceWith(content);
      mount();
      position(url, focus);
    } catch {
      if (!controller.signal.aborted) {
        status.textContent = '暂时打不开该页面，请联网后重试。';
        if (historyMode === 'pop') history.replaceState(null, '', displayed);
      }
    } finally {
      if (!controller.signal.aborted && status.textContent === '正在打开…') status.textContent = '';
    }
  }

  document.addEventListener('click', event => {
    const link = event.target.closest('a[href]');
    if (!link || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey ||
        event.shiftKey || event.altKey || link.target || link.hasAttribute('download')) return;
    const url = new URL(link.href);
    if (url.origin !== location.origin || !route.test(url.pathname) || (url.hash && url.pathname === location.pathname)) return;
    event.preventDefault();
    navigate(url, 'push');
  });
  window.addEventListener('popstate', () => navigate(new URL(location.href), 'pop'));
  if ('serviceWorker' in navigator) {
    if (!navigator.serviceWorker.controller) {
      navigator.serviceWorker.addEventListener('controllerchange', () => {
        if (document.body.dataset.day !== '0') fetch(location.pathname).catch(() => {});
      }, {once:true});
    }
    navigator.serviceWorker.register('/sw.js').catch(() => {});
  }

  const meta = document.querySelector('#lessonMeta');
  if (meta) window.__PAGE__ = JSON.parse(meta.textContent);
  mount();

  window.addEventListener('nh80-cloud-change', () => {
    if (main().querySelector('#resume,#flashDeck')) mount();
  });
  function resume() {
    const last = NHCourse.last();
    if (main().querySelector('#resume') && last && !NHCourse.done(last)) {
      const url = new URL('/day-' + String(last).padStart(3, '0') + '.html', location.origin);
      navigate(url, 'replace', false);
    }
  }
  window.NHSync.start().finally(resume);
})();
