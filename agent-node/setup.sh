#!/usr/bin/env bash
# Sets up a team member's agent on macOS or Linux: Ollama (localhost only) + the member's
# model, Tailscale, Python and the agent service. Messages are Turkish; see agent-node/README.md.
#
# NOTE: this script could not be tested on a real Mac/Linux machine (the team's test machine
# runs Windows). The first member who runs it should report any problem to the team.
#
# Usage (from the repo folder):
#   ./agent-node/setup.sh uye2 [--master-url http://<master>:8000] [--skip-tailscale]
set -euo pipefail

usage() {
  echo "Kullanim: ./agent-node/setup.sh <uye1..uye6> [--master-url URL] [--skip-tailscale]"
  exit 1
}

[ $# -ge 1 ] || usage
AGENT_ID="$1"; shift
MASTER_URL=""
SKIP_TAILSCALE=0
while [ $# -gt 0 ]; do
  case "$1" in
    --master-url) MASTER_URL="${2:-}"; shift 2 ;;
    --skip-tailscale) SKIP_TAILSCALE=1; shift ;;
    *) usage ;;
  esac
done

case "$AGENT_ID" in
  uye1) MEMBER_NAME="İshak Bostan"; MODEL="qwen3.5:4b" ;;
  uye2) MEMBER_NAME="Zeynep Duru Küçük"; MODEL="phi4-mini" ;;
  uye3) MEMBER_NAME="Furkan Kaan Özbeyli"; MODEL="llama3.2:3b" ;;
  uye4) MEMBER_NAME="Semih Sarıca"; MODEL="gemma4:e4b" ;;
  uye5) MEMBER_NAME="Işıl Karademir"; MODEL="qwen2.5-coder:7b" ;;
  uye6) MEMBER_NAME="Berfin Yiğit"; MODEL="qwen3:1.7b" ;;
  *) usage ;;
esac

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
AGENT_DIR="$REPO_ROOT/agent"
AGENT_ENV="$AGENT_DIR/.env"
OLLAMA_API="http://127.0.0.1:11434"
OS="$(uname -s)"

step() { echo ""; echo "== $1/7: $2 =="; }

env_value() {  # env_value <file> <key>
  [ -f "$1" ] || return 0
  grep -E "^$2=" "$1" | head -n1 | cut -d= -f2- || true
}

wait_ollama() {
  for _ in $(seq 1 30); do
    curl -fsS "$OLLAMA_API/api/version" >/dev/null 2>&1 && return 0
    sleep 1
  done
  echo "Ollama 30 saniye icinde yanit vermedi. Ollama'yi acip scripti tekrar calistirin."
  exit 1
}

echo "Ajan kurulumu: $AGENT_ID - $MEMBER_NAME - model $MODEL"

# --- 1. Ollama ---------------------------------------------------------------------------
step 1 "Ollama"
if ! command -v ollama >/dev/null 2>&1; then
  if [ "$OS" = "Darwin" ]; then
    if command -v brew >/dev/null 2>&1; then
      brew install ollama
    else
      echo "Ollama kurulu degil ve Homebrew yok. https://ollama.com/download/mac adresinden kurun."
      exit 1
    fi
  else
    curl -fsSL https://ollama.com/install.sh | sh
  fi
fi

# The old setup script opened Ollama to the whole network (OLLAMA_HOST=0.0.0.0). With the
# pull-based agent only this computer needs Ollama, so that setting is removed.
OVERRIDE=/etc/systemd/system/ollama.service.d/override.conf
if [ "$OS" = "Darwin" ]; then
  if [ -n "$(launchctl getenv OLLAMA_HOST 2>/dev/null || true)" ]; then
    launchctl unsetenv OLLAMA_HOST || true
    pkill -x ollama 2>/dev/null || true
    sleep 1
    echo "Eski OLLAMA_HOST ayari kaldirildi."
  fi
  if ! curl -fsS "$OLLAMA_API/api/version" >/dev/null 2>&1; then
    nohup ollama serve >/tmp/ollama-serve.log 2>&1 &
  fi
elif [ -f "$OVERRIDE" ] && grep -q "OLLAMA_HOST" "$OVERRIDE"; then
  sudo rm -f "$OVERRIDE"
  sudo systemctl daemon-reload
  sudo systemctl restart ollama
  echo "Eski OLLAMA_HOST ayari kaldirildi: Ollama artik yalnizca bu bilgisayardan erisilebilir."
elif ! curl -fsS "$OLLAMA_API/api/version" >/dev/null 2>&1; then
  nohup ollama serve >/tmp/ollama-serve.log 2>&1 &
fi
wait_ollama
echo "Ollama hazir: $(command -v ollama)"

# --- 2. Model -----------------------------------------------------------------------------
step 2 "Model indiriliyor: $MODEL"
ollama pull "$MODEL"
if [ "$OS" = "Darwin" ]; then
  RAM_GB=$(( $(sysctl -n hw.memsize) / 1024 / 1024 / 1024 ))
else
  RAM_GB=$(( $(awk '/MemTotal/ {print $2}' /proc/meminfo) / 1024 / 1024 ))
fi
echo "Bilgisayarin RAM'i: ${RAM_GB} GB (model boyutu + yaklasik 4 GB onerilir)"

# --- 3. Model test ------------------------------------------------------------------------
step 3 "Model test ediliyor"
RESPONSE=$(curl -s "$OLLAMA_API/api/chat" -d "{\"model\": \"$MODEL\", \"messages\": [{\"role\":\"user\",\"content\":\"Tek kelimeyle cevap ver: hazir misin?\"}], \"think\": false, \"stream\": false}")
echo "$RESPONSE" | python3 -c "import sys,json; print('Model yaniti:', json.load(sys.stdin)['message']['content'])" 2>/dev/null || echo "Ham yanit: $RESPONSE"

# --- 4. Tailscale -------------------------------------------------------------------------
step 4 "Tailscale (ekip agi)"
if [ "$SKIP_TAILSCALE" = "1" ]; then
  echo "Atlandi."
else
  if ! command -v tailscale >/dev/null 2>&1; then
    if [ "$OS" = "Darwin" ]; then
      echo "Tailscale'i https://tailscale.com/download/mac adresinden (veya App Store'dan) kurup"
      echo "uygulamayi acin, sonra bu scripti tekrar calistirin."
      exit 1
    fi
    curl -fsSL https://tailscale.com/install.sh | sh
  fi
  if tailscale status >/dev/null 2>&1; then
    echo "Bu bilgisayar zaten ekip agina bagli."
  else
    read -r -s -p "Ishak'in ozelden gonderdigi Tailscale anahtari (tskey-auth-...): " TS_KEY; echo
    sudo tailscale up --auth-key="$TS_KEY"
    echo "Ekip agina baglanildi."
  fi
fi

# --- 5. Python and the agent ----------------------------------------------------------------
step 5 "Python ve ajan paketleri"
if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
  echo "Python 3.10 veya ustu gerekli. macOS: 'brew install python@3.12', Ubuntu: 'sudo apt install python3 python3-venv'"
  exit 1
fi
[ -x "$AGENT_DIR/.venv/bin/python" ] || python3 -m venv "$AGENT_DIR/.venv"
"$AGENT_DIR/.venv/bin/python" -m pip install --quiet --disable-pip-version-check -r "$AGENT_DIR/requirements.txt"
echo "Ajan hazir: $AGENT_DIR/.venv/bin/python"

# --- 6. Agent settings --------------------------------------------------------------------
step 6 "Ajan ayarlari (agent/.env)"
[ -n "$MASTER_URL" ] || MASTER_URL="$(env_value "$AGENT_ENV" MASTER_URL)"
if [ -z "$MASTER_URL" ]; then
  read -r -p "Master adresi (Ishak'tan alin, or. http://ishak-pc:8000): " MASTER_URL
fi
MASTER_URL="${MASTER_URL%/}"
TOKEN="$(env_value "$AGENT_ENV" AGENT_TOKEN)"
if [ -z "$TOKEN" ]; then
  read -r -s -p "AGENT_TOKEN (Ishak'in ozelden gonderdigi anahtar): " TOKEN; echo
fi
[ -n "$TOKEN" ] || { echo "AGENT_TOKEN bos olamaz."; exit 1; }

umask 077
cat > "$AGENT_ENV" <<EOF
# Created by agent-node/setup.sh. Contains a secret (AGENT_TOKEN): never commit or share this file.
AGENT_ID=$AGENT_ID
MEMBER_NAME=$MEMBER_NAME
MODEL=$MODEL
MASTER_URL=$MASTER_URL
AGENT_TOKEN=$TOKEN
OLLAMA_URL=$OLLAMA_API
AGENT_MODE=node
EOF
echo "Ayarlar kaydedildi: $AGENT_ENV"

# --- 7. Master connection -----------------------------------------------------------------
step 7 "Master baglantisi"
if curl -fsS --max-time 10 "$MASTER_URL/health" >/dev/null 2>&1; then
  echo "Master'a ulasilabiliyor: $MASTER_URL"
else
  echo "UYARI: Master'a su an ulasilamiyor ($MASTER_URL). Ajan baslatildiginda baglanana kadar tekrar dener."
fi

echo ""
echo "Kurulum tamamlandi."
echo "Ajani baslatmak icin:  ./agent-node/start-agent.sh"
