#!/usr/bin/env bash
# Nihongo 80 本机部署脚本（仿 zoomlab-web/scripts/deploy.sh）。
#
# 模式：本机脚本优先、push 不自动部署、先 preview 后 production、部署后 health check。
# 默认【不执行部署】：必须显式传 preview|production。
# 前置：本机 wrangler OAuth 登录态有效（wrangler whoami 可确认；首次需人工 login 一次）。
# 本脚本不含、也不需要任何账号 ID / 域名 / 密钥（workers.dev 地址从 wrangler 输出推断）。
# 2026-11-06 已用本机登录态完成 preview + production 上线，见 docs/CLOUDFLARE.md 第 4 节。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ "$#" -lt 1 ]; then
  echo "用法: $0 preview|production" >&2
  echo "  默认不执行部署。首次上线请先人工: npx wrangler login" >&2
  echo "  顺序建议: 先 $0 preview，再 $0 production" >&2
  exit 2
fi

ENVIRONMENT="$1"
case "$ENVIRONMENT" in
  preview)
    WRANGLER_ENV=(--env preview)
    ;;
  production)
    WRANGLER_ENV=()
    ;;
  *)
    echo "用法: $0 preview|production (收到: ${ENVIRONMENT})" >&2
    exit 2
    ;;
esac

# 1) 本地构建 / 校验：缺 curriculum 或 seeds 会立即失败，绝不发布空页。
echo "==> [1/3] 本地构建 web/ (build_site.py)"
python3 "$ROOT/scripts/build_site.py" --root "$ROOT"

# 2) 部署：Worker + assets.directory 一起由 wrangler deploy 发布。
echo "==> [2/3] wrangler deploy ($ENVIRONMENT)"
cd "$ROOT/deploy"
if [ ! -d node_modules ]; then
  # 部署依赖按需安装：项目本身保持轻量（node_modules 约 223M，不随项目长期保留）。
  echo "未找到 deploy/node_modules，自动安装 wrangler（约 1 分钟）..."
  npm install --no-audit --no-fund
fi
# 兼容 macOS 自带 bash 3.2 + set -u 的空数组展开写法（同 zoomlab）。
DEPLOY_OUTPUT="$(npx wrangler deploy --config wrangler.jsonc ${WRANGLER_ENV[@]+"${WRANGLER_ENV[@]}"} 2>&1)" || {
  printf '%s\n' "$DEPLOY_OUTPUT" >&2
  echo "wrangler deploy 失败" >&2
  exit 1
}
printf '%s\n' "$DEPLOY_OUTPUT"

# 3) 部署后 health check：/api/health 应返回 {"status":"ok"}。
#    不硬编码账号/域名：优先用 NH80_BASE_URL，其次从本次 wrangler 输出推断 workers.dev 地址。
echo "==> [3/3] health check"
BASE="${NH80_BASE_URL:-}"
if [ -z "$BASE" ]; then
  BASE="$(printf '%s\n' "$DEPLOY_OUTPUT" | grep -Eo 'https://[A-Za-z0-9._-]+\.workers\.dev' | head -n1 || true)"
fi
if [ -z "$BASE" ]; then
  echo "未能推断访问地址，跳过 health check。" >&2
  echo "请部署后手动核对: curl -fsS <你的 workers.dev 地址>/api/health" >&2
  echo "或设置 NH80_BASE_URL 后重跑本脚本。" >&2
else
  ok=0
  for i in 1 2 3 4 5; do
    if curl -fsS "$BASE/api/health" | grep -q '"status":"ok"'; then ok=1; break; fi
    echo "health 未就绪，重试 $i"; sleep 5
  done
  if [ "$ok" -ne 1 ]; then
    echo "health check 失败: $BASE/api/health" >&2
    exit 1
  fi
  echo "deployed $ENVIRONMENT: $BASE"
fi
