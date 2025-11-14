#!/bin/bash
# Install systemd timer for automated portfolio rebalancing

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🚀 Installing portfolio rebalance scheduler..."
echo "Project root: $PROJECT_ROOT"

# Copy service and timer files
echo "📄 Copying systemd files..."
sudo cp "$SCRIPT_DIR/portfolio-rebalance.service" /etc/systemd/system/
sudo cp "$SCRIPT_DIR/portfolio-rebalance.timer" /etc/systemd/system/

# Update WorkingDirectory in service file
echo "🔧 Updating paths..."
sudo sed -i "s|/home/brad/cursor_code/metagross_projects/stock_portfolio|$PROJECT_ROOT|g" \
    /etc/systemd/system/portfolio-rebalance.service

# Update User in service file
CURRENT_USER=$(whoami)
sudo sed -i "s|User=brad|User=$CURRENT_USER|g" /etc/systemd/system/portfolio-rebalance.service
sudo sed -i "s|Group=brad|Group=$CURRENT_USER|g" /etc/systemd/system/portfolio-rebalance.service

# Create log files with proper permissions
echo "📝 Creating log files..."
sudo touch /var/log/portfolio-rebalance.log
sudo touch /var/log/portfolio-rebalance-error.log
sudo chown "$CURRENT_USER:$CURRENT_USER" /var/log/portfolio-rebalance.log
sudo chown "$CURRENT_USER:$CURRENT_USER" /var/log/portfolio-rebalance-error.log

# Reload systemd
echo "🔄 Reloading systemd..."
sudo systemctl daemon-reload

# Enable and start timer
echo "✅ Enabling timer..."
sudo systemctl enable portfolio-rebalance.timer
sudo systemctl start portfolio-rebalance.timer

# Show status
echo ""
echo "✅ Scheduler installed successfully!"
echo ""
echo "📊 Timer Status:"
sudo systemctl status portfolio-rebalance.timer --no-pager
echo ""
echo "📅 Next scheduled run:"
systemctl list-timers portfolio-rebalance.timer --no-pager
echo ""
echo "💡 Useful commands:"
echo "  View timer status:  sudo systemctl status portfolio-rebalance.timer"
echo "  View logs:         tail -f /var/log/portfolio-rebalance.log"
echo "  View errors:       tail -f /var/log/portfolio-rebalance-error.log"
echo "  Stop timer:        sudo systemctl stop portfolio-rebalance.timer"
echo "  Disable timer:     sudo systemctl disable portfolio-rebalance.timer"
echo "  Run manually:      sudo systemctl start portfolio-rebalance.service"

