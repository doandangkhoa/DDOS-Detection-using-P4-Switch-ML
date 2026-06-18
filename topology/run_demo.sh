#!/bin/bash

# Exit immediately if any command fails
set -e

# ============================================================
# Determine project root directory
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "============================================================"
echo "   P4-Based ML-Driven DDoS Detection & Mitigation Demo"
echo "============================================================"

# ============================================================
# [1/4] Compile P4 Program
# ============================================================

echo -e "\n🚀 [1/4] COMPILING P4 SOURCE CODE..."

cd "$PROJECT_ROOT/data_plane/p4src"

rm -f "$PROJECT_ROOT/topology/p4_compiled.json"

p4c-bm2-ss \
    --p4v 16 \
    -o "$PROJECT_ROOT/topology/p4_compiled.json" \
    main.p4

echo "✅ Successfully generated p4_compiled.json!"

# ============================================================
# [2/4] Clean Previous Environment
# ============================================================

echo -e "\n🧹 [2/4] CLEANING UP PREVIOUS ENVIRONMENT..."

sudo mn -c >/dev/null 2>&1 || true
sudo pkill -f simple_switch >/dev/null 2>&1 || true
sudo pkill -f simple_switch_grpc >/dev/null 2>&1 || true
sudo fuser -k 9090/tcp >/dev/null 2>&1 || true

echo "✅ Environment cleaned successfully!"

# ============================================================
# [3/4] Schedule Forwarding Rule Installation
# ============================================================

echo -e "\n⚙️ [3/4] SCHEDULING ROUTING TABLE INSTALLATION..."

(
    echo "[SYSTEM] Waiting for BMv2 switch to become available..."

    while ! nc -z localhost 9090 2>/dev/null; do
        sleep 1
    done

    simple_switch_CLI \
        --thrift-port 9090 \
        < "$PROJECT_ROOT/topology/s1-commands.txt" \
        > /dev/null 2>&1

    echo -e "\n🎯 [SYSTEM] Successfully loaded s1-commands.txt into switch s1!"
) &

# ============================================================
# [4/4] Start Mininet
# ============================================================

echo -e "\n🌐 [4/4] STARTING MININET TESTBED..."

echo "================================================================="
echo " AFTER THE 'mininet>' PROMPT APPEARS:"
echo ""
echo " 1. Open host terminals:"
echo "      xterm h5 h2"
echo ""
echo " 2. On h5 (Controller Host):"
echo "      cd ~/DDOS-Detection-using-P4-Switch-ML/control_plane"
echo "      python3 sdn_controller.py"
echo ""
echo " 3. On h2 (Attack Host):"
echo "      hping3 -S -p 80 -i u100 10.0.0.3"
echo ""
echo " Expected behavior:"
echo "   • P4 switch exports traffic statistics"
echo "   • Controller performs ML inference"
echo "   • DDoS attack is detected"
echo "   • Mitigation rules are dynamically installed"
echo "================================================================="

sleep 2

sudo -E python3 "$PROJECT_ROOT/topology/network_topo.py"