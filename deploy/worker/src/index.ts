// 极简 Worker：只处理健康检查，其余请求全部交给 ASSETS 静态资源。
// 无任何账号 ID / 密钥 / 数据库 / 外部依赖。
interface Env {
  ASSETS: { fetch: (request: Request) => Promise<Response> };
}

export default {
  fetch(request: Request, env: Env): Response | Promise<Response> {
    const url = new URL(request.url);
    if (url.pathname === "/api/health" || url.pathname === "/health") {
      return new Response(JSON.stringify({ status: "ok" }), {
        status: 200,
        headers: { "content-type": "application/json; charset=utf-8" },
      });
    }
    // html_handling: "none" 下 assets 不会把 / 映射到 index.html，
    // 这里显式转发，保证首页与 /day-NNN.html 都能用同一套真实路径。
    if (url.pathname === "/") {
      const indexUrl = new URL("/index.html", url.origin).toString();
      return env.ASSETS.fetch(new Request(indexUrl, request));
    }
    return env.ASSETS.fetch(request);
  },
};
