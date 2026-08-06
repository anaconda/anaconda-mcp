# Conda Environment Manager Agent

An intelligent OpenCode agent that provides adaptive conda environment management for Python development tasks through dynamic analysis and smart selection algorithms.

## 🎯 Purpose

This agent implements sophisticated conda environment management by:

- **Dynamic Environment Discovery**: Automatically analyzes and clusters existing environments based on naming patterns, package content, and purpose
- **Intelligent Task Analysis**: Extracts keywords from user requests to match against environment characteristics
- **Scoring-Based Selection**: Uses a multi-factor scoring algorithm to rank environments by relevance
- **Environment Reuse Strategy**: Prioritizes modifying existing environments over creating new ones
- **Channel-Aware Management**: Respects user's .condarc configuration and channel preferences
- **Conda-Only Policy**: Strictly uses conda/mamba tools, never pip, for package management

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

## 📁 Architecture & Components

```
conda-env-manager-agent/
├── agent-config/
│   ├── prompt.md              # Core agent logic and responsibilities
│   ├── environment-mapping.md  # Advanced selection algorithms
│   └── usage-guide.md         # Detailed usage instructions
├── scripts/
│   ├── setup.sh              # Automated installation and configuration
│   └── test-agent.sh         # Comprehensive testing suite
├── docs/
│   ├── README.md             # This comprehensive documentation
│   ├── AGENT_DESIGN.md       # Architecture and design decisions
│   └── EXAMPLES.md          # Real-world usage scenarios
└── .opencode/
    └── conda-manager.md     # OpenCode integration configuration
```

### Core Components Breakdown

**agent-config/prompt.md**: Defines the agent's core responsibilities, including:
- Task analysis and keyword extraction
- Environment discovery and analysis procedures  
- Multi-factor scoring algorithm implementation
- Channel management and conda-only policies
- Communication and decision-making protocols

**agent-config/environment-mapping.md**: Contains advanced selection logic:
- Dynamic environment clustering algorithms
- Pattern recognition and scoring systems
- Package compatibility analysis methods
- Environment naming conventions and creation rules

**Testing & Validation**: The agent includes comprehensive testing to ensure:
- Proper environment selection across different setups
- Correct package installation using conda-only methods
- Channel configuration respect and management
- Integration with various conda configurations

## 🧠 Intelligent Environment Selection Algorithm

### Multi-Factor Scoring System
The agent uses a sophisticated scoring algorithm that evaluates environments based on:

1. **Name Pattern Matching** (10 points per keyword match)
   - Environment names containing task-relevant keywords
   - Shared prefixes/suffixes indicating domain (e.g., "ml-", "web-", "test-")
   - Purpose indicators ("dev", "prod", "experimental")

2. **Package Compatibility Analysis** (5 points per matching package)
   - Environments with relevant packages already installed
   - Complementary package sets for the task domain
   - Package content clustering for environment grouping

3. **Python Version Preference** (2 points bonus)
   - Python 3.11+ environments preferred
   - Version compatibility with task requirements

4. **Environment Specificity**
   - More specific matches preferred over general ones
   - Recent activity/usage patterns considered

### Dynamic Discovery Process
The agent automatically discovers and clusters environments by:

- **Natural Grouping**: Analyzes naming conventions to identify domain clusters
- **Pattern Recognition**: Identifies common patterns (torch, tensorflow, jupyter, api, etc.)
- **Content Analysis**: Examines installed packages to determine environment purpose
- **Adaptive Categorization**: Lets discovered environments dictate categories rather than prescribing them

### Selection Workflow
1. **Task Analysis**: Extract keywords from user request (packages, technologies, purposes)
2. **Environment Discovery**: List and analyze all available conda environments
3. **Pattern Matching**: Find environments with relevant name patterns and packages
4. **Scoring & Ranking**: Apply multi-factor scoring algorithm
5. **Channel Analysis**: Read .condarc to understand available channels
6. **Recommendation**: Present best match with reasoning
7. **Execution**: Install missing packages or create new environment if needed

## 📋 Intelligent Task Domain Detection

The agent automatically identifies task domains and matches them to appropriate environments:

### Automatic Domain Recognition
- **Data Science & Analysis**: Keywords like "analysis", "data", "pandas", "numpy", "visualization"
- **Machine Learning**: Terms like "ml", "model", "training", "tensorflow", "pytorch", "scikit-learn"
- **Web Development**: Keywords like "api", "server", "django", "flask", "fastapi", "web"
- **Notebook Work**: Terms like "jupyter", "notebook", "marimo", "interactive"
- **Testing & Validation**: Keywords like "test", "pytest", "unittest", "validation"
- **Development Tools**: General Python development and utility tasks

### Dynamic Environment Examples
Based on discovered environments, the agent creates intelligent groupings:

**ML-Focused Systems** (environments like `ml-pytorch`, `ml-tensorflow`):
- Directs ML tasks to specialized ML environments
- Considers framework-specific environments (PyTorch vs TensorFlow)
- Prioritizes environments with relevant ML packages

**Web Development Systems** (environments like `web-api`, `dev-django`):
- Routes web development tasks to appropriate environments
- Matches framework-specific environments (Django, Flask, FastAPI)
- Considers testing environments for web projects

**General Development Systems** (environments like `python-general`, `base-env`):
- Uses for general Python tasks
- Suitable for utility scripts and simple projects
- Falls back when no specialized environment exists

## 🔧 Installation & Setup

### Quick Start
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

### Agent Configuration
The agent reads your conda configuration automatically:
- **.condarc Analysis**: Scans your .condarc file for channel preferences
- **Channel Respect**: Uses only configured channels, never adds new ones without permission
- **Environment Discovery**: Automatically detects and categorizes your existing environments
- **Python Version Preference**: Prioritizes Python 3.11+ environments when available

### Integration with anaconda-mcp
This agent works seamlessly with the anaconda-mcp project by:
- Using the `anaconda-mcp_conda_environments_list_environments` tool for discovery
- Leveraging `anaconda-mcp_conda_environments_install_packages` for package management
- Utilizing `anaconda-mcp_conda_environments_create_environment` for new environments
- Supporting streamable-http transport for real-time environment management

## 🧪 Testing & Validation

### Automated Testing
Run the comprehensive test suite to verify the agent works correctly:

```bash
chmod +x scripts/test-agent.sh
./scripts/test-agent.sh
```

The test suite validates:
- **Environment Discovery**: Proper detection and categorization of existing environments
- **Selection Algorithm**: Correct scoring and ranking of environments based on task requirements
- **Package Management**: Proper use of conda tools for package installation
- **Channel Management**: Respect for .condarc configuration and channel preferences
- **Integration**: Seamless operation with anaconda-mcp tools and transport layers

### Manual Testing Examples
Test the agent with various scenarios:

```bash
# Test ML environment selection
opencode --prompt "$(cat agent-config/prompt.md)" --request "Create a machine learning model with scikit-learn"

# Test web development routing  
opencode --prompt "$(cat agent-config/prompt.md)" --request "Build a FastAPI REST server"

# Test environment reuse
opencode --prompt "$(cat agent-config/prompt.md)" --request "Add matplotlib to existing data analysis environment"
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

## 🔧 Advanced Configuration

### Channel Management Policy
The agent implements strict channel management to ensure consistency:

1. **Read .condarc First**: Always analyzes user's channel configuration before any operations
2. **Respect Channel Order**: Uses channels in the exact order specified in .condarc
3. **No Channel Overrides**: Never adds or modifies channels without explicit user permission
4. **Fallback Strategy**: If packages unavailable, asks user before suggesting channel changes

### Environment Creation Rules
When creating new environments, the agent follows these principles:

- **Descriptive Naming**: Uses patterns like `python-{domain}`, `test-{project}`, `dev-{project}`
- **Python 3.11+ Preference**: Prioritizes modern Python versions when available
- **Minimal Base Packages**: Includes only essential development tools initially
- **Domain-Specific Packages**: Adds packages based on task analysis and discovered patterns
- **Future-Proof Design**: Creates environments suitable for ongoing development

### Integration Benefits

**For Developers**:
- Automatic environment selection reduces cognitive overhead
- Intelligent reuse prevents environment proliferation
- Consistent conda-only policy ensures reproducibility

**For Teams**:
- Standardized environment management across team members
- Channel configuration respect maintains organizational policies
- Documented environment purposes aid knowledge transfer

**For Operations**:
- Streamlined environment lifecycle management
- Reduced storage overhead through intelligent reuse
- Consistent deployment environments through standardized creation

---

🤖 **Intelligent by Design**: This agent represents a new approach to environment management - one that adapts to your existing setup rather than forcing you to adapt to it.

Created with ❤️ for adaptive Python environment management