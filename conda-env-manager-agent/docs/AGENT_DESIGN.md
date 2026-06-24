# Agent Design Decisions

This document explains the design decisions behind the Conda Environment Manager Agent.

## Core Philosophy

### 1. Environment Reuse Over Creation
**Decision**: Prioritize reusing existing environments over creating new ones.

**Rationale**: 
- Reduces disk space usage
- Avoids environment sprawl
- Maintains consistency across projects
- Leverages existing package installations

### 2. Dynamic Environment Discovery
**Decision**: Analyze existing environments dynamically rather than using hardcoded mappings.

**Rationale**:
- Works on any machine with conda environments
- Adapts to user's existing setup
- No assumptions about specific environment names
- Flexible and portable across systems

### 3. Strict Conda-Only Policy
**Decision**: Use only conda for package management, never pip.

**Rationale**:
- Better dependency resolution
- Cross-platform compatibility
- Consistent package sources
- Reduced conflicts
- Avoids mixing conda/pip environments

### 4. Channel Configuration Respect
**Decision**: Always respect user's .condarc channel configuration.

**Rationale**:
- Maintains user's established preferences
- Avoids unexpected channel changes
- Works with enterprise/custom channel setups
- Preserves security and compliance requirements

## Architecture Decisions

### Prompt-Based Agent
**Decision**: Use OpenCode's prompt system rather than custom code.

**Rationale**:
- Leverages OpenCode's existing capabilities
- Easy to maintain and update
- No complex deployment needed
- Works with existing MCP tools

### File-Based Configuration
**Decision**: Store agent configuration in markdown files.

**Rationale**:
- Human-readable and editable
- Version control friendly
- Easy to customize per user
- Documentation embedded in configuration

## Environment Selection Algorithm

### Dynamic Analysis Approach
```
1. List all available environments
2. Analyze environment names to identify natural groupings
3. Check installed packages when possible
4. Let discovered environments dictate categories
5. Match task requirements to environment characteristics
6. Prioritize by Python version (3.11+ preferred)
7. Create new environment only as last resort
```

### Dynamic Environment Discovery
The agent discovers environment groupings by analyzing:
- **Name Patterns**: Clusters environments with similar naming conventions
- **Package Content**: Groups environments with similar installed packages  
- **Purpose Indicators**: Identifies likely use cases from environment characteristics
- **User Task Keywords**: Matches task requirements to available environments

### Pattern Recognition Strategy
Instead of prescribing categories, the agent:
- Identifies naming patterns in existing environments
- Looks for clusters of similar environments (e.g., multiple "ml-*" environments)
- Analyzes package similarities to understand groupings
- Adapts categorization based on what's actually present

## Channel Management Strategy

### .condarc-First Policy
1. **Read Configuration**: Always examine .condarc file before any package operations
2. **Respect Priority**: Use channels in the exact order specified in .condarc
3. **No Overrides**: Never add override_channels without explicit user request
4. **Ask First**: Only change channels if absolutely essential and user approves

### Fallback Strategy
If a package cannot be found in any configured channel:
1. Inform user about the missing package
2. Explain which channels were checked
3. Ask for permission to modify channel configuration
4. Never make unilateral changes to channel setup

## Naming Conventions

### Environment Names
- `python-{domain}` - Domain-specific environments
- `test-{project}` - Testing environments
- `dev-{project}` - Development environments

### Examples
- `python-datascience` - General data science work
- `test-webapp` - Testing a web application
- `dev-ml-project` - Development for ML project

## Error Handling Strategy

### Graceful Degradation
1. If preferred environment not found, try alternatives
2. If conda tools fail, provide manual instructions
3. If environment creation fails, suggest troubleshooting
4. If channels don't have packages, ask before changing

### User Confirmation
Always ask for confirmation before:
- Creating new environments
- Installing packages
- Modifying existing environments
- Changing channel configuration

## Performance Considerations

### Environment Caching
- Cache environment lists to reduce conda command overhead
- Store package lists for quick lookup
- Remember user preferences for environment selection

### Fast Startup
- Minimal prompt loading
- Lazy evaluation of environment information
- Background package checking

## Security Considerations

### Channel Configuration Respect
- Never override user's .condarc settings
- Respect enterprise security policies
- Maintain compliance with organizational requirements
- Ask before any channel modifications

### Environment Isolation
- Never modify system Python
- Keep environments isolated
- Use consistent naming to avoid conflicts

## Extensibility

### Universal Design
- Works with any conda environment setup
- Adapts to user's existing conventions
- No hardcoded environment dependencies
- Configurable keyword patterns

### User Customization
- Editable prompt files
- Custom environment mappings
- Personal preference settings
- Channel configuration preservation

## Future Enhancements

### Planned Features
1. **Package Usage Analytics**: Track which packages/environments are used most
2. **Automatic Cleanup**: Remove unused environments after configurable time
3. **Environment Templates**: Pre-configured environments for common tasks
4. **Integration Testing**: Test environment compatibility before use
5. **Channel Optimization**: Suggest channel improvements based on usage patterns

### Integration Opportunities
- VS Code extension for environment switching
- Jupyter kernel auto-detection
- Docker environment export
- CI/CD pipeline integration

## Success Metrics

### User Experience
- Reduced time to set up Python environments
- Fewer duplicate environments
- Higher satisfaction with environment selections
- Better respect for existing configurations

### System Performance
- Less disk space usage through environment reuse
- Faster package installation through intelligent caching
- Reduced conda command overhead
- Fewer channel conflicts

### Portability
- Works on any machine with conda
- No assumptions about specific environments
- Adapts to user preferences
- Maintains existing configurations

This design prioritizes user experience, system efficiency, and portability while providing powerful conda environment management capabilities that work anywhere conda is installed.