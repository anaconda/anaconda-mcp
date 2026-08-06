#!/bin/bash

# Conda Environment Manager Agent Setup Script

set -e

echo "🔧 Setting up Conda Environment Manager Agent..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if opencode is installed
if ! command -v opencode &> /dev/null; then
    echo -e "${RED}❌ OpenCode is not installed. Please install it first:${NC}"
    echo "curl -fsSL https://opencode.ai/install | bash"
    exit 1
fi

# Check if conda is installed
if ! command -v conda &> /dev/null; then
    echo -e "${RED}❌ Conda is not installed. Please install Anaconda or Miniconda first.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Dependencies found: OpenCode and Conda${NC}"

# Create opencode config directory if it doesn't exist
OPENCODE_DIR="$HOME/.opencode"
if [ ! -d "$OPENCODE_DIR" ]; then
    mkdir -p "$OPENCODE_DIR"
    echo -e "${GREEN}✅ Created OpenCode config directory${NC}"
fi

# Copy agent configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cp "$PROJECT_ROOT/agent-config/prompt.md" "$OPENCODE_DIR/conda-manager.md"
echo -e "${GREEN}✅ Installed agent prompt to $OPENCODE_DIR/conda-manager.md${NC}"

# Create convenience script
cat > "$HOME/.local/bin/conda-agent" << 'EOF'
#!/bin/bash

# Conda Environment Manager Agent Launcher
# Usage: conda-agent [your-task-description]

if [ $# -eq 0 ]; then
    echo "🤖 Conda Environment Manager Agent"
    echo ""
    echo "Usage: conda-agent [your-task-description]"
    echo ""
    echo "Examples:"
    echo "  conda-agent 'I need to do data analysis with pandas'"
    echo "  conda-agent 'Set up machine learning environment with scikit-learn'"
    echo "  conda-agent 'Create web development environment for Django'"
    echo ""
    echo "Starting OpenCode with conda environment manager..."
    exec opencode --prompt "$(cat $HOME/.opencode/conda-manager.md)"
else
    TASK="$*"
    echo "🐍 Starting conda environment manager for: $TASK"
    exec opencode --prompt "$(cat $HOME/.opencode/conda-manager.md)

Your task: $TASK" 
fi
EOF

# Make script executable
mkdir -p "$HOME/.local/bin"
chmod +x "$HOME/.local/bin/conda-agent"

# Add to PATH if not already there
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.zshrc"
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bash_profile" 2>/dev/null || true
    echo -e "${YELLOW}⚠️  Added $HOME/.local/bin to PATH. Please restart your shell or run:${NC}"
    echo "export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

echo -e "${GREEN}✅ Created conda-agent launcher script${NC}"

# Test conda environments
echo -e "${YELLOW}🔍 Checking available conda environments...${NC}"
conda env list --json 2>/dev/null | jq -r '.envs[] | split("/") | .[-1]' 2>/dev/null || conda env list

echo ""
echo -e "${GREEN}🎉 Setup complete!${NC}"
echo ""
echo -e "${YELLOW}Usage options:${NC}"
echo "1. Direct: conda-agent 'your task description'"
echo "2. Interactive: conda-agent"
echo "3. Manual: opencode --prompt \"\$(cat ~/.opencode/conda-manager.md)\""
echo ""
echo -e "${YELLOW}Examples:${NC}"
echo "  conda-agent 'Set up data science environment with pandas and numpy'"
echo "  conda-agent 'Create machine learning environment for TensorFlow'"
echo "  conda-agent 'I need to work on a Django web project'"
echo ""
echo -e "${GREEN}🚀 Your conda environment manager is ready to use!${NC}"