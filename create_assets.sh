#!/bin/bash
# Create missing assets for EZREC backend

echo "🎨 Creating missing assets..."

# Create assets directory if it doesn't exist
sudo mkdir -p /opt/ezrec-backend/assets

# Create sponsor.png placeholder
echo "📝 Creating sponsor.png placeholder..."
sudo tee /opt/ezrec-backend/assets/sponsor.png > /dev/null << 'EOF'
iVBORw0KGgoAAAANSUhEUgAAAMgAAADICAYAAACtWK6eAAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAALEwAACxMBAJqcGAAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAA==
EOF

# Create company.png placeholder
echo "📝 Creating company.png placeholder..."
sudo tee /opt/ezrec-backend/assets/company.png > /dev/null << 'EOF'
iVBORw0KGgoAAAANSUhEUgAAAMgAAADICAYAAACtWK6eAAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAALEwAACxMBAJqcGAAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAA==
EOF

# Set proper permissions
sudo chown ezrec:ezrec /opt/ezrec-backend/assets/sponsor.png
sudo chown ezrec:ezrec /opt/ezrec-backend/assets/company.png
sudo chmod 644 /opt/ezrec-backend/assets/sponsor.png
sudo chmod 644 /opt/ezrec-backend/assets/company.png

echo "✅ Assets created successfully"
echo "📁 Assets location: /opt/ezrec-backend/assets/" 