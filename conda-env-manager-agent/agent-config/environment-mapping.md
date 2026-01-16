# Environment Selection Mappings

This document defines the logic for selecting conda environments based on task requirements.

## Environment Analysis Strategy

### Environment Discovery
- List all available conda environments on the system
- Analyze environment names to identify natural groupings
- Check installed packages when possible
- Identify Python versions
- Let the discovered environments dictate the categories

### Dynamic Group Discovery
The agent analyzes environments to identify natural groupings:
- **Cluster by Name Patterns**: Group environments with similar naming conventions
- **Cluster by Package Content**: Group environments with similar installed packages
- **Cluster by Purpose**: Identify likely use cases based on environment characteristics

### Environment Name Pattern Analysis
Look for these common patterns to identify groupings:
- Shared prefixes or suffixes (e.g., "ml-", "web-", "test-")
- Common terms (e.g., "torch", "tensorflow", "jupyter", "api")
- Version patterns (e.g., "py38", "py39", "311")
- Purpose indicators (e.g., "dev", "prod", "experimental")

### Task Domain to Environment Matching

#### Keyword-Based Matching
For any user task, extract relevant keywords:
- Package names mentioned (pandas, flask, pytest, etc.)
- Technology terms (tensorflow, django, fastapi, etc.)
- Purpose descriptions (analysis, server, testing, etc.)
- Framework references (jupyter, notebook, api, etc.)

#### Environment Selection Strategy
1. **Extract Task Keywords**: Identify key terms from user request
2. **Environment Keyword Match**: Find environments whose names contain matching keywords
3. **Package Content Analysis**: Check if environments have relevant packages installed
4. **Name Pattern Recognition**: Look for environments with naming patterns matching the task
5. **Python Version Preference**: Prefer Python 3.11+ when multiple options exist

## Environment Selection Algorithm

```python
def select_environment(task_keywords, available_envs):
    # Step 1: Extract keywords from task
    keywords = extract_task_keywords(task_keywords)
    
    # Step 2: Find environments with matching name patterns
    name_matches = find_environments_by_name_patterns(available_envs, keywords)
    
    # Step 3: Analyze package compatibility if possible
    package_matches = analyze_package_compatibility(available_envs, keywords)
    
    # Step 4: Score and rank environments
    scored_envs = score_environments(name_matches, package_matches, keywords)
    
    # Step 5: Sort by Python version preference (3.11+ preferred)
    preferred_envs = sort_by_python_version(scored_envs)
    
    # Step 6: Return best match or create new
    if preferred_envs:
        return preferred_envs[0], "existing"
    
    new_env_name = generate_env_name(keywords)
    return new_env_name, "create"
```

## Dynamic Environment Scoring

### Scoring Factors
1. **Name Pattern Match**: Environment name contains task-relevant keywords
2. **Package Compatibility**: Environment has relevant packages installed
3. **Python Version**: Newer Python versions preferred (3.11+)
4. **Specificity**: More specific matches preferred over general ones
5. **Recent Activity**: More recently used/updated environments preferred

### Example Scoring Logic
```python
def score_environment(env_name, packages, keywords):
    score = 0
    
    # Name pattern matching
    for keyword in keywords:
        if keyword.lower() in env_name.lower():
            score += 10
    
    # Package compatibility
    for keyword in keywords:
        if any(keyword.lower() in pkg.lower() for pkg in packages):
            score += 5
    
    # Python version preference
    if env_has_python_311_plus(env_name):
        score += 2
    
    return score
```

## Environment Group Discovery Examples

### Example 1: ML-Focused Setup
If the agent finds:
- `ml-pytorch`, `ml-tensorflow`, `ml-general`
- `test-ml`, `dev-ml-pipeline`

It will create a "Machine Learning" grouping and direct ML tasks to these environments.

### Example 2: Web Development Setup
If the agent finds:
- `web-api`, `web-frontend`, `web-fullstack`
- `dev-django`, `test-flask`

It will create a "Web Development" grouping and direct web tasks to these environments.

### Example 3: General Purpose Setup
If the agent finds:
- `python-general`, `base-env`, `tools`
- `dev-setup`, `analysis-env`

It will create a "General Development" grouping and direct general tasks to these environments.

## New Environment Creation Rules

### Naming Convention
- `python-{domain}` - Domain specific (e.g., python-datascience, python-web)
- `test-{project}` - Project testing (e.g., test-webapp, test-mlproject)
- `dev-{project}` - Project development (e.g., dev-microservice, dev-datapipe)

### Base Environment Selection
- Python 3.11+ preferred when available
- Use channels from .condarc file - NEVER override unless explicitly requested
- Include essential development tools (setuptools, wheel)
- Add domain-specific packages based on detected needs

### Channel Management
- ALWAYS read .condarc file first to understand available channels
- Use channels in the order specified in .condarc
- NEVER add new channels without explicit user permission
- ONLY change channels if absolutely essential and user approves

### Specialized Base Packages
Package selection should be based on:
- **User's task requirements**: Install packages specifically mentioned or implied by the task
- **Discovered patterns**: Look at what similar environments on the system have
- **Common domain packages**: Use judgment to add typical packages for the task domain

## Package Installation Rules

### Conda-Only Policy
- NEVER use pip for package installation
- ONLY use conda or mamba for package management
- If package not available via conda, inform user and ask for guidance

### Channel Priority
1. Use channels from .condarc file as configured
2. Respect channel priority order in .condarc
3. Do not add override_channels parameter unless necessary
4. Ask user permission before modifying channel configuration

This mapping ensures the agent adapts to any conda setup while providing intelligent environment selection based on what's actually available on the system.