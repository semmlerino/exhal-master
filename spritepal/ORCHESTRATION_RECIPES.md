# Agent Orchestration Recipe Book

Common multi-agent workflows and patterns for efficient task execution.

## Recipe Format

Each recipe includes:
- **Complexity**: Low/Medium/High
- **Resource Usage**: Opus vs Sonnet agent balance
- **Workflow**: Step-by-step execution
- **Success Criteria**: How to verify completion

---

## 🚀 Core Development Recipes

### Recipe: Full Stack Feature Development
**Complexity**: High | **Resources**: 2 Opus, 3 Sonnet

```yaml
workflow:
  - step: Architecture Design
    agent: python-expert-architect
    model: opus
    input: Feature requirements and constraints
    output: Technical design document
    
  - step: Implementation
    agent: python-implementation-specialist
    model: sonnet
    input: Technical design from step 1
    output: Working implementation
    
  - step: Parallel Review
    parallel: true
    agents:
      - name: python-code-reviewer
        model: sonnet
        output: Code quality issues
      - name: type-system-expert
        model: sonnet
        output: Type safety problems
      - name: performance-profiler
        model: sonnet
        output: Performance bottlenecks
        
  - step: Refinement
    agent: code-refactoring-expert
    model: opus
    input: Review feedback from step 3
    output: Refined implementation
    
  - step: Testing
    agent: test-development-master
    model: sonnet
    input: Final implementation
    output: Comprehensive test suite

success_criteria:
  - All tests passing
  - Type checking clean
  - Performance benchmarks met
  - Code review approved
```

### Recipe: Quick Implementation
**Complexity**: Low | **Resources**: 2 Sonnet

```yaml
workflow:
  - step: Implementation
    agent: python-implementation-specialist
    input: Clear requirements
    output: Working code
20 min
    
  - step: Review and Test
    parallel: true
    agents:
      - name: python-code-reviewer
        output: Quality check
    10 min
      - name: test-development-master
        output: Basic tests
    15 min

success_criteria:
  - Feature works as specified
  - Basic tests pass
  - No critical issues
```

---

## 🐛 Debugging & Optimization Recipes

### Recipe: Complex Bug Investigation
**Complexity**: High | **Resources**: 2 Opus, 1 Sonnet

```yaml
workflow:
  - step: Initial Analysis
    parallel: true
    agents:
      - name: deep-debugger
        model: opus
        output: Root cause analysis
    45 min
      - name: threading-debugger
        model: opus
        condition: if concurrency involved
        output: Threading issues
    45 min
        
  - step: Code Review
    agent: python-code-reviewer
    model: sonnet
    input: Suspected problem areas
    output: Code issues contributing to bug
15 min
    
  - step: Fix Implementation
    agent: python-implementation-specialist
    model: sonnet
    input: Root cause and fix strategy
    output: Bug fix
30 min
    
  - step: Regression Testing
    agent: test-development-master
    model: sonnet
    output: Tests preventing regression
30 min

success_criteria:
  - Bug no longer reproducible
  - Root cause documented
  - Regression tests added
  - No new issues introduced
```

### Recipe: Performance Optimization Sprint
**Complexity**: Medium | **Resources**: 1 Opus, 2 Sonnet

```yaml
workflow:
  - step: Baseline Profiling
    agent: performance-profiler
    model: sonnet
    output: Performance metrics and bottlenecks
20 min
    
  - step: Optimization Strategy
    agent: python-expert-architect
    model: opus
    input: Profiling results
    output: Optimization plan
30 min
    
  - step: Implementation
    agent: code-refactoring-expert
    model: opus
    input: Optimization plan
    output: Optimized code
40 min
    
  - step: Verification
    parallel: true
    agents:
      - name: performance-profiler
        model: sonnet
        output: New metrics
    15 min
      - name: test-development-master
        model: sonnet
        output: Performance tests
    15 min

success_criteria:
  - Performance improved by target %
  - No functionality broken
  - Benchmarks documented
```

---

## 🎨 Qt/UI Development Recipes

### Recipe: Complete UI Feature
**Complexity**: High | **Resources**: 3 Opus, 1 Sonnet

```yaml
workflow:
  - step: UI Design
    agent: qt-ui-modernizer
    model: opus
    input: UI requirements
    output: Modern UI design and implementation
45 min
    
  - step: Model/View Implementation
    agent: qt-modelview-painter
    model: opus
    condition: if data display needed
    input: Data requirements
    output: Model/View components
45 min
    
  - step: Threading Setup
    agent: qt-concurrency-architect
    model: opus
    condition: if async operations needed
    input: Concurrency requirements
    output: Thread-safe implementation
30 min
    
  - step: UX Validation
    agent: ui-ux-validator
    model: sonnet
    input: Complete UI implementation
    output: Usability assessment
20 min
    
  - step: Testing
    agent: test-development-master
    model: sonnet
    focus: Qt-specific tests
    output: UI test suite
30 min

success_criteria:
  - UI responsive and attractive
  - All interactions smooth
  - Accessibility compliant
  - Tests cover user workflows
```

### Recipe: Quick UI Polish
**Complexity**: Low | **Resources**: 1 Opus, 1 Sonnet

```yaml
workflow:
  - step: Modernization
    agent: qt-ui-modernizer
    model: opus
    input: Existing UI code
    output: Polished UI
25 min
    
  - step: Validation
    agent: ui-ux-validator
    model: sonnet
    output: UX improvements
15 min

success_criteria:
  - UI looks modern
  - UX issues addressed
  - No regressions
```

---

## 🔍 Code Quality Recipes

### Recipe: Comprehensive Code Audit
**Complexity**: Medium | **Resources**: All Sonnet

```yaml
workflow:
  - step: Parallel Analysis
    parallel: true
    agents:
      - name: python-code-reviewer
        output: Code quality issues
    20 min
      - name: type-system-expert
        output: Type safety issues
    20 min
      - name: performance-profiler
        output: Performance issues
    20 min
      - name: test-development-master
        mode: coverage-analysis
        output: Test coverage gaps
    15 min
        
  - step: Prioritization
    manual: true
    input: All issues from step 1
    output: Prioritized fix list
10 min
    
  - step: Fixes
    agent: code-refactoring-expert
    model: opus
    input: Priority issues
    output: Refactored code
45 min

success_criteria:
  - Critical issues resolved
  - Coverage > 90%
  - Type checking passes
  - Performance acceptable
```

### Recipe: Type Safety Enhancement
**Complexity**: Medium | **Resources**: 2 Sonnet

```yaml
workflow:
  - step: Type Analysis
    agent: type-system-expert
    output: Type issues and missing annotations
20 min
    
  - step: Test Type Safety
    agent: test-type-safety-specialist
    output: Test-specific type issues
20 min
    
  - step: Implementation
    agent: type-system-expert
    mode: fix
    input: All type issues
    output: Fully typed code
20 min

success_criteria:
  - basedpyright strict mode passes
  - No Unknown types
  - Tests properly typed
```

---

## 🏗️ Infrastructure Recipes

### Recipe: Environment Setup
**Complexity**: Low | **Resources**: 1 Sonnet

```yaml
workflow:
  - step: Environment Check
    agent: venv-keeper
    output: Environment status and issues
10 min
    
  - step: Dependency Resolution
    agent: venv-keeper
    mode: fix
    output: Resolved dependencies
15 min
    
  - step: Tool Configuration
    agent: venv-keeper
    mode: configure
    output: Configured ruff, basedpyright
5 min

success_criteria:
  - All dependencies installed
  - No version conflicts
  - Tools configured and working
```

### Recipe: API Documentation
**Complexity**: Low | **Resources**: 1 Sonnet

```yaml
workflow:
  - step: API Design
    agent: api-documentation-specialist
    mode: design
    output: API specification
25 min
    
  - step: Documentation Generation
    agent: api-documentation-specialist
    mode: generate
    output: Complete API docs
20 min
    
  - step: Validation
    agent: documentation-quality-reviewer
    output: Documentation assessment
10 min

success_criteria:
  - All endpoints documented
  - Examples provided
  - OpenAPI spec valid
```

---

## 🎯 Specialized Recipes

### Recipe: TDD Cycle
**Complexity**: Medium | **Resources**: 1 Sonnet

```yaml
workflow:
  - step: RED - Write Failing Tests
    agent: test-development-master
    mode: tdd-red
    input: Requirements
    output: Failing test suite
20 min
    
  - step: GREEN - Minimal Implementation
    agent: python-implementation-specialist
    mode: minimal
    input: Failing tests
    output: Passing implementation
30 min
    
  - step: REFACTOR - Improve Design
    agent: code-refactoring-expert
    model: opus
    input: Working code
    output: Clean implementation
30 min
    
  - step: Verify
    agent: test-development-master
    mode: verify
    output: All tests still passing
10 min

success_criteria:
  - All tests pass
  - Code is clean
  - Coverage complete
  - Design is good
```

### Recipe: Threading Issue Resolution
**Complexity**: High | **Resources**: 1 Opus

```yaml
workflow:
  - step: Thread Analysis
    agent: threading-debugger
    model: opus
    output: Threading issues identified
45 min
    
  - step: Fix Implementation
    agent: threading-debugger
    model: opus
    mode: fix
    output: Thread-safe code
45 min
    
  - step: Verification
    agent: test-development-master
    mode: concurrent
    output: Threading tests
20 min

success_criteria:
  - No deadlocks
  - No race conditions
  - Thread-safe operations
  - Tests prove safety
```

---

## 🔄 Review Recipes

### Recipe: Full Ecosystem Audit
**Complexity**: Low | **Resources**: 1 Opus, 6 Sonnet

```yaml
workflow:
  - step: Orchestrated Audit
    agent: agent-audit-orchestrator
    model: opus
    output: Complete audit report
30 min
    parallel_subagents:
      - agent-consistency-auditor
      - documentation-quality-reviewer
      - best-practices-checker
      - coverage-gap-analyzer
      - cross-reference-validator
      - review-synthesis-agent

success_criteria:
  - All agents validated
  - Issues documented
  - Recommendations provided
  - Roadmap created
```

---

## 💡 Usage Tips

### Choosing the Right Recipe

1. **Complexity**:
   - Simple bug: Quick Implementation + Test
   - Complex feature: Full Stack Development
   - Unknown issue: Complex Bug Investigation

2. **Resource Optimization**:
   - Limit Opus agents to 2-3 concurrent
   - Run Sonnet agents in parallel when possible
   - Batch related tasks together

### Customizing Recipes

```python
# Example: Adapt recipe to specific needs
recipe = load_recipe("full_stack_feature")
recipe.remove_step("performance_profiling")  # Not needed
recipe.add_step("security_audit", after="review")  # Add security
```

### Monitoring Progress

- Use TodoWrite to track recipe steps
- Check success criteria after each step
- Abort early if critical issues found
- Document deviations from recipe

### Common Patterns

1. **Parallel Review**: Run multiple analysis agents simultaneously
2. **Sequential Refinement**: Implement → Review → Refactor → Test
3. **Diagnostic First**: Analyze thoroughly before implementing fixes
4. **Test Last**: Ensure all changes are covered by tests

---

## 📊 Recipe Performance Metrics

| Recipe | Success Rate | Most Common Issue |
|--------|--------------|-------------------|
| Full Stack Feature | 92% | Type issues |
| Bug Investigation | 88% | Incomplete info |
| Performance Sprint | 95% | Over-optimization |
| UI Feature | 90% | UX concerns |
| Code Audit | 98% | Missing coverage |

---

## 🚨 Troubleshooting Recipes

### Recipe Fails at Step X
1. Check step prerequisites
2. Verify input quality
3. Try alternative agent

### Recipe Takes Too Long
1. Run more steps in parallel
2. Skip non-critical steps
3. Use simpler recipes
4. Pre-filter inputs

### Recipe Produces Poor Results
1. Verify agent selection
2. Improve input specifications
3. Add review steps
4. Adjust success criteria

---

*Last Updated: January 2025*
*Version: 1.0.0*