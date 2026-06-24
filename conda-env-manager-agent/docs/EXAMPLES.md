# Usage Examples

This document provides practical examples of using the Conda Environment Manager Agent.

## Quick Start Examples

### 1. Data Science Task
```bash
conda-agent "I need to analyze sales data with pandas and create visualizations with matplotlib"
```

**Expected Agent Response**:
```
🎯 **Recommended Environment:** `anaconda-2025.06-py3.11`

This environment is well-suited for data analysis tasks and has Python 3.11.

**Current Packages Check:**
- Checking if pandas and matplotlib are installed...

**Next Steps:**
1. ✅ Use existing environment
2. 📦 Install missing packages: pandas, matplotlib
3. 🚀 Start your analysis

Would you like me to proceed with installing the missing packages?
```

### 2. Machine Learning Project
```bash
conda-agent "Set up machine learning environment for TensorFlow with GPU support"
```

**Expected Agent Response**:
```
🤖 **Recommended Environment:** `pytorch-test`

While this environment is optimized for PyTorch, it has ML infrastructure. However, I recommend creating a specialized TensorFlow environment.

**Proposed Action:**
1. 🆕 Create new environment: `python-tensorflow`
2. 📦 Install: tensorflow, pandas, numpy, jupyter
3. 🚀 Ready for ML development

Proceed with creating the new environment?
```

### 3. Web Development Setup
```bash
conda-agent "I need to develop a Django web application with PostgreSQL support"
```

**Expected Agent Response**:
```
🌐 **Recommended Environment:** `anaconda-toolbox`

This is your general-purpose environment suitable for web development.

**Package Plan:**
- Check for Django installation
- Add psycopg2 for PostgreSQL support
- Install additional web dev packages if needed

Would you like me to install Django and PostgreSQL adapter?
```

## Advanced Usage Examples

### 4. Interactive Session
```bash
conda-agent
```

Then in OpenCode:
```
I want to work on a data science project that involves:
- Time series analysis with pandas
- Machine learning with scikit-learn  
- Interactive visualization with plotly
- Jupyter notebook development

Please set up the best environment for this workflow.
```

### 5. Environment Migration
```bash
conda-agent "I have packages installed in base environment but want to move to a dedicated data science environment"
```

**Expected Agent Response**:
```
📋 **Migration Plan:**

1. 📦 Scan base environment for data science packages
2. 🆕 Create dedicated environment: `python-datascience-migrated`
3. 📋 Recreate package list in new environment
4. ✅ Verify installation
5. 🧹 Clean up base environment if confirmed

**Packages to migrate:**
- pandas, numpy, matplotlib, seaborn
- scikit-learn, jupyter, ipython

Proceed with migration?
```

### 6. Testing Environment Setup
```bash
conda-agent "Set up testing environment for my Django project with pytest and coverage"
```

**Expected Agent Response**:
```
🧪 **Recommended Environment:** `testing`

Perfect! You already have a dedicated testing environment.

**Enhancement Plan:**
- Check current testing packages
- Add Django-specific testing tools if missing
- Configure coverage reporting
- Set up pytest-django if needed

Current environment ready for enhancement. Proceed?
```

## Environment-Specific Examples

### Data Science Workflows
```bash
# Pandas data manipulation
conda-agent "I need pandas, numpy, and openpyxl for Excel file processing"

# Statistical analysis  
conda-agent "Set up environment for statistical analysis with scipy and statsmodels"

# Data visualization
conda-agent "Create environment for visualization with seaborn, plotly, and bokeh"
```

### Machine Learning Workflows
```bash
# Classical ML
conda-agent "Scikit-learn environment with pandas, numpy, and jupyter"

# Deep Learning
conda-agent "PyTorch environment with torchvision and torchaudio for computer vision"

# NLP
conda-agent "Set up NLP environment with transformers, spacy, and nltk"
```

### Web Development Workflows
```bash
# Django
conda-agent "Django environment with gunicorn, postgresql, and redis"

# Flask
conda-agent "Flask environment with SQLAlchemy, pytest, and coverage"

# FastAPI
conda-agent "FastAPI environment with uvicorn, pydantic, and pytest"
```

### Development Tools
```bash
# Code Quality
conda-agent "Set up environment with black, flake8, mypy, and pre-commit"

# Documentation
conda-agent "Sphinx environment for generating project documentation"

# Performance
conda-agent "Environment with line_profiler, memory_profiler, and py-spy"
```

## Troubleshooting Examples

### Package Conflicts
```bash
conda-agent "I'm getting package conflicts when trying to install both tensorflow and pytorch"
```

**Agent Response**:
```
⚠️ **Conflict Resolution:**

TensorFlow and PyTorch have conflicting dependencies. Recommended approach:

1. 🆕 Create separate environments:
   - `python-tensorflow` - For TF projects
   - `python-pytorch` - For PyTorch projects

2. 📦 Install domain-specific packages separately

3. 🔄 Switch between environments based on project needs

Would you like me to create both environments?
```

### Environment Cleanup
```bash
conda-agent "I have too many environments, help me organize and clean up"
```

**Agent Response**:
```
🧹 **Environment Audit:**

**Current Environments:**
- python-old-project (6 months unused)
- test-webapp-temp (3 months unused)  
- dev-experiment (last used yesterday)
- anaconda-toolbox (active)

**Recommendations:**
1. 🗑️ Remove unused environments (with confirmation)
2. 📦 Consolidate similar environments
3. 🏷️ Rename environments for clarity
4. 📋 Create environment inventory

Proceed with cleanup?
```

## Batch Operations

### Multiple Project Setup
```bash
conda-agent "Set up environments for 3 projects: data analysis, web API, and ML model"
```

### Team Environment Sharing
```bash
conda-agent "Create reproducible environment file for team collaboration"
```

These examples demonstrate the agent's flexibility in handling various Python development scenarios while maintaining intelligent environment management principles.