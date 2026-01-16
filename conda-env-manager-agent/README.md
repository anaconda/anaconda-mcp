# Conda Environment Manager Agent

An intelligent OpenCode agent that manages conda environments for Python development tasks.

## 🎯 Purpose

This agent specializes in smart conda environment management by:
- Analyzing existing conda environments
- Selecting the best environment for specific Python tasks
- Reusing environments when possible to avoid duplication
- Installing missing packages intelligently
- Creating new environments only when necessary

## 🚀 Usage

### With OpenCode
```bash
cd your-project-directory
opencode --prompt "$(cat agent-config/prompt.md)"
```

### Direct usage
1. Start OpenCode normally
2. Use the agent prompt for Python-related tasks
3. The agent will automatically analyze your conda environments and make recommendations

## 📁 Structure

```
conda-env-manager-agent/
├── agent-config/
│   ├── prompt.md              # Main agent prompt
│   ├── environment-mapping.md  # Environment selection logic
│   └── usage-guide.md         # Detailed usage instructions
├── scripts/
│   ├── setup.sh              # Installation script
│   └── test-agent.sh         # Test script
├── docs/
│   ├── README.md             # This file
│   ├── AGENT_DESIGN.md       # Design decisions
│   └── EXAMPLES.md          # Usage examples
└── .opencode/
    └── conda-manager.md     # OpenCode configuration
```

## 🎛️ Environment Selection Logic

The agent follows this hierarchy:

1. **Domain-specific environments**:
   - Data Science/ML: `pytorch-test`, `bayesian`
   - Notebooks: `Jupyter`, `marimo`
   - Web Development: `anaconda-toolbox`, `claude_env`
   - Testing: `test`, `testing`, `mcp-test`

2. **General purpose environments**:
   - `anaconda-2025.06-py3.11` (Python 3.11)
   - `anaconda-202512-py312` (Python 3.12)

3. **Create new environment** (last resort)

## 📋 Supported Tasks

- **Data Analysis**: pandas, numpy, matplotlib environments
- **Machine Learning**: scikit-learn, tensorflow, pytorch environments  
- **Web Development**: Django, Flask, FastAPI environments
- **Notebook Work**: Jupyter, marimo environments
- **Testing**: pytest, unittest environments
- **Development**: General Python development environments

## 🔧 Installation

1. Clone this repository:
```bash
git clone <repo-url>
cd conda-env-manager-agent
```

2. Run setup script:
```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

3. Start using with OpenCode:
```bash
opencode --prompt "$(cat agent-config/prompt.md)"
```

## 🧪 Testing

Run the test script to verify the agent works correctly:

```bash
chmod +x scripts/test-agent.sh
./scripts/test-agent.sh
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add your improvements
4. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

## 🔗 Related Projects

- [OpenCode](https://opencode.ai) - The AI coding agent
- [Conda](https://conda.io) - Package and environment manager

---

Created with ❤️ for intelligent Python environment management