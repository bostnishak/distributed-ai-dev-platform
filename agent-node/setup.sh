#!/usr/bin/env bash
# Ekip uyeleri icin Ollama + atanan model kurulum script'i (Mac / Linux).
# Kullanim: ./setup.sh phi4-mini
# Hangi uyeye hangi model tag'i atandigi icin README.md'ye bakin.
set -euo pipefail

if [ -z "${1:-}" ]; then
  echo "Kullanim: ./setup.sh <model-tag>   (orn: ./setup.sh phi4-mini)"
  exit 1
fi
MODEL="$1"

echo "== 1/4: Ollama kontrol ediliyor =="
if ! command -v ollama >/dev/null 2>&1; then
  OS="$(uname -s)"
  if [ "$OS" = "Darwin" ]; then
    if command -v brew >/dev/null 2>&1; then
      echo "Ollama kurulu degil, Homebrew ile kuruluyor..."
      brew install ollama
    else
      echo "Ollama kurulu degil ve Homebrew bulunamadi."
      echo "Lutfen https://ollama.com/download/mac adresinden Ollama'yi kurup bu script'i tekrar calistirin."
      exit 1
    fi
  else
    echo "Ollama kurulu degil, resmi kurulum script'i ile kuruluyor..."
    curl -fsSL https://ollama.com/install.sh | sh
  fi
fi
echo "Ollama hazir: $(command -v ollama)"

echo ""
echo "== 2/5: LAN erisimi acik hale getiriliyor =="
# ONEMLI: Ollama varsayilan olarak sadece localhost'u dinler -- bu haliyle gateway (baska bir
# bilgisayar) buraya asla ulasamaz. OLLAMA_HOST=0.0.0.0 ile tum ag arayuzlerinden erisilebilir
# hale getiriyoruz. Bu, ayni LAN'daki herkesin (kimlik dogrulamasiz) bu modeli sorgulayabilecegi
# anlamina gelir -- ekip bunu kabul etti (guvenilir ev/okul agi varsayimiyla).
#
# NOT: Bu kisim Windows'taki kadar test edilmedi. Calismazsa (gateway'den erisim basarisiz
# olursa) elle "OLLAMA_HOST=0.0.0.0 ollama serve" ile deneyin ve grupla paylasin.
OS="$(uname -s)"
if [ "$OS" = "Darwin" ]; then
  launchctl setenv OLLAMA_HOST "0.0.0.0" 2>/dev/null || true
  pkill -x ollama 2>/dev/null || true
  sleep 1
  OLLAMA_HOST=0.0.0.0 nohup ollama serve >/tmp/ollama-serve.log 2>&1 &
  sleep 2
elif command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files | grep -q ollama.service; then
  sudo mkdir -p /etc/systemd/system/ollama.service.d
  printf '[Service]\nEnvironment="OLLAMA_HOST=0.0.0.0"\n' | sudo tee /etc/systemd/system/ollama.service.d/override.conf >/dev/null
  sudo systemctl daemon-reload
  sudo systemctl restart ollama
  sleep 2
else
  pkill -x ollama 2>/dev/null || true
  sleep 1
  OLLAMA_HOST=0.0.0.0 nohup ollama serve >/tmp/ollama-serve.log 2>&1 &
  sleep 2
fi
echo "Ollama artik butun ag arayuzlerinden erisilebilir olmali (0.0.0.0:11434)."

echo ""
echo "== 3/5: Model cekiliyor: $MODEL =="
ollama pull "$MODEL"

echo ""
echo "== 4/5: Model test ediliyor =="
RESPONSE=$(curl -s http://localhost:11434/api/chat -d "{\"model\": \"$MODEL\", \"messages\": [{\"role\":\"user\",\"content\":\"Tek kelimeyle cevap ver: hazir misin?\"}], \"think\": false, \"stream\": false}")
echo "$RESPONSE" | python3 -c "import sys,json; print('Model yaniti:', json.load(sys.stdin)['message']['content'])" 2>/dev/null || echo "Ham yanit: $RESPONSE"

echo ""
echo "== 5/5: LAN IP adresi =="
if [ "$(uname -s)" = "Darwin" ]; then
  IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "bulunamadi")
else
  IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "bulunamadi")
fi

echo ""
echo "Kurulum tamamlandi."
echo "Bu bilgisayarin LAN IP adresi: $IP"
echo "Bu IP'yi ve model adini ($MODEL) gateway'i kuran arkadasa iletin."
