const C = 'nh80-v19-__REVISION__';
const shell = ['/index.html', '/assets/app.css', '/assets/course_progress.js',
  '/assets/review_schedule.js', '/assets/app.js', '/assets/study.js',
  '/assets/flashcards.js', '/assets/course_sync.js', '/assets/course_version.js', '/assets/course_app.js', '/flashcards.html', '/data/flashcards.json'];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(C).then(cache => cache.addAll(shell)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(
    keys.filter(key => key.startsWith('nh80-') && key !== C).map(key => caches.delete(key))
  )).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== self.location.origin ||
      url.pathname.startsWith('/api/') || request.headers.has('range') || url.pathname.startsWith('/audio/')) return;

  const key = url.pathname === '/' ? '/index.html' : request;
  event.respondWith((async () => {
    const cache = await caches.open(C);
    try {
      const response = await fetch(request, {cache:'no-cache'});
      if (response.ok) {
        try { await cache.put(key, response.clone()); } catch {}
      }
      return response;
    } catch {
      return (await cache.match(key)) || new Response('此页面尚未下载，请联网后重试。', {
        status: 503, headers: {'Content-Type': 'text/plain;charset=utf-8'}
      });
    }
  })());
});
