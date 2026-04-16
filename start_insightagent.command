#!/bin/zsh
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE_FILE="$PROJECT_DIR/compose.full.yml"
LOG_DIR="$PROJECT_DIR/logs"
BACKEND_VENV_PY="$PROJECT_DIR/backend/.venv/bin/python"

kill_port_listeners() {
  local sig="$1"
  local port="$2"
  local pids
  pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null | sort -u || true)"
  if [[ -n "${pids:-}" ]]; then
    kill -"$sig" $pids 2>/dev/null || true
  fi
}

echo "[1/6] 释放本地端口 8000/3001..."
for port in 8000 3001; do
  kill_port_listeners TERM "$port"
done
pkill -f "uvicorn app.main:app" 2>/dev/null || true
pkill -f "next dev -p 3001 --hostname 127.0.0.1 --port 3001" 2>/dev/null || true
sleep 1
for port in 8000 3001; do
  kill_port_listeners KILL "$port"
done
pkill -f "uvicorn app.main:app" 2>/dev/null || true
pkill -f "next dev -p 3001 --hostname 127.0.0.1 --port 3001" 2>/dev/null || true

echo "[2/6] 启动 Docker 依赖服务 postgres/chroma..."
if ! docker info >/dev/null 2>&1; then
  echo "错误：Docker 未运行，请先启动 Docker Desktop。"
  exit 1
fi

docker compose -f "$COMPOSE_FILE" up -d postgres chroma

echo "[3/6] 等待 postgres 就绪..."
POSTGRES_CONTAINER_ID="$(docker compose -f "$COMPOSE_FILE" ps -q postgres)"
if [[ -z "${POSTGRES_CONTAINER_ID:-}" ]]; then
  echo "错误：未找到 postgres 容器实例。"
  exit 1
fi
for i in {1..60}; do
  if docker exec "$POSTGRES_CONTAINER_ID" pg_isready -U insight -d insightagent >/dev/null 2>&1; then
    break
  fi
  if [[ "$i" == "60" ]]; then
    echo "错误：PostgreSQL 60 秒内未就绪。"
    exit 1
  fi
  sleep 1
done

echo "[4/6] 等待 chroma 就绪..."
for i in {1..60}; do
  if curl -fsS "http://127.0.0.1:8001/api/v2/heartbeat" >/dev/null 2>&1; then
    break
  fi
  if [[ "$i" == "60" ]]; then
    echo "错误：Chroma 60 秒内未就绪。"
    exit 1
  fi
  sleep 1
done

mkdir -p "$LOG_DIR"

echo "[5/6] 启动 backend/frontend..."
if [[ -x "$BACKEND_VENV_PY" ]]; then
  BACKEND_PY="$BACKEND_VENV_PY"
else
  BACKEND_PY="python3"
  echo "提示：未发现 backend/.venv/bin/python，回退使用 python3。"
fi

nohup zsh -lc "cd '$PROJECT_DIR/backend' && '$BACKEND_PY' -m uvicorn app.main:app --host 127.0.0.1 --port 8000" > "$LOG_DIR/backend.log" 2>&1 &
nohup zsh -lc "cd '$PROJECT_DIR/frontend' && npm run dev -- --hostname 127.0.0.1 --port 3001" > "$LOG_DIR/frontend.log" 2>&1 &
disown

sleep 2

echo "[6/6] 启动状态检查..."
docker compose -f "$COMPOSE_FILE" ps

backend_ok=false
for i in {1..30}; do
  if curl -fsS "http://127.0.0.1:8000/health" >/dev/null 2>&1; then
    backend_ok=true
    break
  fi
  sleep 1
done
if [[ "$backend_ok" == true ]]; then
  echo "backend 健康检查通过: http://127.0.0.1:8000/health"
else
  echo "警告：backend 健康检查未通过，请查看 $LOG_DIR/backend.log"
fi

frontend_ok=false
for i in {1..30}; do
  if curl -fsSI "http://127.0.0.1:3001" >/dev/null 2>&1; then
    frontend_ok=true
    break
  fi
  sleep 1
done
if [[ "$frontend_ok" == true ]]; then
  echo "frontend 已可访问: http://127.0.0.1:3001"
else
  echo "警告：frontend 尚未就绪，请查看 $LOG_DIR/frontend.log"
fi

echo "完成。日志路径：$LOG_DIR"
