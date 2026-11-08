#!/usr/bin/env bash
# Give the running app (bash dev.sh) a public https link, e.g. https://random-words.trycloudflare.com
# Free Cloudflare quick tunnel: no account, works while this laptop is awake. Ctrl-C to stop sharing.
set -euo pipefail
cd "$(dirname "$0")"

if ! curl -s -o /dev/null http://localhost:5173; then
  echo "Start the app first in another terminal: bash dev.sh"; exit 1
fi

CF=$(command -v cloudflared || true)
if [ -z "$CF" ]; then
  CF=.bin/cloudflared
  if [ ! -x "$CF" ]; then
    case "$(uname -s)-$(uname -m)" in
      Darwin-arm64)  asset=cloudflared-darwin-arm64.tgz ;;
      Darwin-x86_64) asset=cloudflared-darwin-amd64.tgz ;;
      Linux-x86_64)  asset=cloudflared-linux-amd64 ;;
      Linux-aarch64) asset=cloudflared-linux-arm64 ;;
      *) echo "Install cloudflared first: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"; exit 1 ;;
    esac
    echo "Downloading cloudflared (one time)…"
    mkdir -p .bin
    url="https://github.com/cloudflare/cloudflared/releases/latest/download/$asset"
    if [[ $asset == *.tgz ]]; then curl -fsSL "$url" | tar -xz -C .bin; else curl -fsSL -o "$CF" "$url"; fi
    chmod +x "$CF"
  fi
fi

echo
echo "  Your public link appears below as https://….trycloudflare.com"
echo "  Share it with judges. Demo mode works there; use the Renter / Landlord switch."
echo
exec "$CF" tunnel --no-autoupdate --url http://localhost:5173
