/* Nihongo 80 Service Worker — 由 build_site.py 生成，勿手改。
 * 约束：只缓存同源静态文件；fetch 阶段绝不调用网络请求；不缓存任何学习状态；
 *       不向任何地址发送学习数据；版本化缓存，activate 清理旧版本。 */
var CACHE = 'nh80-149f331bcea7';
var ASSETS = ["index.html", "404.html", "manifest.webmanifest", "icon.svg", "assets/app.css", "assets/app.js", "day-001.html", "day-002.html", "day-003.html", "day-004.html", "day-005.html", "day-006.html", "day-007.html", "day-008.html", "day-009.html", "day-010.html", "day-011.html", "day-012.html", "day-013.html", "day-014.html", "day-015.html", "day-016.html", "day-017.html", "day-018.html", "day-019.html", "day-020.html", "day-021.html", "day-022.html", "day-023.html", "day-024.html", "day-025.html", "day-026.html", "day-027.html", "day-028.html", "day-029.html", "day-030.html", "day-031.html", "day-032.html", "day-033.html", "day-034.html", "day-035.html", "day-036.html", "day-037.html", "day-038.html", "day-039.html", "day-040.html", "day-041.html", "day-042.html", "day-043.html", "day-044.html", "day-045.html", "day-046.html", "day-047.html", "day-048.html", "day-049.html", "day-050.html", "day-051.html", "day-052.html", "day-053.html", "day-054.html", "day-055.html", "day-056.html", "day-057.html", "day-058.html", "day-059.html", "day-060.html", "day-061.html", "day-062.html", "day-063.html", "day-064.html", "day-065.html", "day-066.html", "day-067.html", "day-068.html", "day-069.html", "day-070.html", "day-071.html", "day-072.html", "day-073.html", "day-074.html", "day-075.html", "day-076.html", "day-077.html", "day-078.html", "day-079.html", "day-080.html", "data/day-001.json", "data/day-002.json", "data/day-003.json", "data/day-004.json", "data/day-005.json", "data/day-006.json", "data/day-007.json", "data/day-008.json", "data/day-009.json", "data/day-010.json", "data/day-011.json", "data/day-012.json", "data/day-013.json", "data/day-014.json", "data/day-015.json", "data/day-016.json", "data/day-017.json", "data/day-018.json", "data/day-019.json", "data/day-020.json", "data/day-021.json", "data/day-022.json", "data/day-023.json", "data/day-024.json", "data/day-025.json", "data/day-026.json", "data/day-027.json", "data/day-028.json", "data/day-029.json", "data/day-030.json", "data/day-031.json", "data/day-032.json", "data/day-033.json", "data/day-034.json", "data/day-035.json", "data/day-036.json", "data/day-037.json", "data/day-038.json", "data/day-039.json", "data/day-040.json", "data/day-041.json", "data/day-042.json", "data/day-043.json", "data/day-044.json", "data/day-045.json", "data/day-046.json", "data/day-047.json", "data/day-048.json", "data/day-049.json", "data/day-050.json", "data/day-051.json", "data/day-052.json", "data/day-053.json", "data/day-054.json", "data/day-055.json", "data/day-056.json", "data/day-057.json", "data/day-058.json", "data/day-059.json", "data/day-060.json", "data/day-061.json", "data/day-062.json", "data/day-063.json", "data/day-064.json", "data/day-065.json", "data/day-066.json", "data/day-067.json", "data/day-068.json", "data/day-069.json", "data/day-070.json", "data/day-071.json", "data/day-072.json", "data/day-073.json", "data/day-074.json", "data/day-075.json", "data/day-076.json", "data/day-077.json", "data/day-078.json", "data/day-079.json", "data/day-080.json", "n3-mock.html"];

self.addEventListener('install', function (e) {
  e.waitUntil(
    caches.open(CACHE).then(function (c) {
      /* 逐个缓存并吞掉个别缺失资源，避免因单文件缺失导致整个 install 失败。 */
      return Promise.all(ASSETS.map(function (u) {
        return c.add(new Request(u, { cache: 'reload' })).catch(function () {});
      }));
    }).then(function () { return self.skipWaiting(); })
  );
});

self.addEventListener('activate', function (e) {
  e.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.map(function (k) {
        if (k.indexOf('nh80-') === 0 && k !== CACHE) return caches.delete(k);
      }));
    }).then(function () { return self.clients.claim(); })
  );
});

self.addEventListener('fetch', function (e) {
  var req = e.request;
  if (req.method !== 'GET') return;
  var url;
  try { url = new URL(req.url); } catch (err) { return; }
  if (url.origin !== self.location.origin) return;
  /* /api/* 与 /health 交给 Worker（健康检查需在线），SW 不介入、不回传任何数据。 */
  if (url.pathname.indexOf('/api/') === 0 || url.pathname === '/health') return;
  e.respondWith(
    caches.match(req).then(function (hit) {
      if (hit) return hit;
      if (req.mode === 'navigate' && (url.pathname === '/' || /\/$/.test(url.pathname))) {
        return caches.match(new Request('index.html'));
      }
      /* 缓存未命中时先走网络，成功后补进缓存；真的断网才回 503。 */
      return fetch(req).then(function (res) {
        if (res && res.ok && res.type === 'basic') {
          var copy = res.clone();
          caches.open(CACHE).then(function (c) { c.put(req, copy); }).catch(function () {});
        }
        return res;
      }).catch(function () {
        return new Response('离线：该资源未缓存', {
          status: 503, statusText: 'Offline',
          headers: { 'content-type': 'text/plain; charset=utf-8' }
        });
      });
    })
  );
});
