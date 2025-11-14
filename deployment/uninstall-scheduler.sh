#!/bin/bash
# Uninstall scheduler (emergency stop)

set -e

echo "🛑 Uninstalling portfolio rebalance scheduler..."

# Stop and disable timer
echo "Stopping timer..."
sudo systemctl stop portfolio-rebalance.timer 2>/dev/null || true
sudo systemctl disable portfolio-rebalance.timer 2>/dev/null || true

# Remove systemd files
echo "Removing systemd files..."
sudo rm -f /etc/systemd/system/portfolio-rebalance.service
sudo rm -f /etc/systemd/system/portfolio-rebalance.timer

# Reload systemd
echo "Reloading systemd..."
sudo systemctl daemon-reload

echo "✅ Scheduler removed successfully"
echo ""
echo "ℹ️  Log files preserved at:"
echo "  /var/log/portfolio-rebalance.log"
echo "  /var/log/portfolio-rebalance-error.log"

