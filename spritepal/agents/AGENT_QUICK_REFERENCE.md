# Agent Quick Reference

Quick lookup guide for all agents in the ecosystem. Use this to rapidly identify which agent to use for specific tasks.

## Agent Summary Table

| Agent | Model | Category | Primary Use Case | Key Capabilities |
|-------|-------|----------|------------------|------------------|
| **python-code-reviewer** | Sonnet | Core Dev | Code review and quality analysis | Bug detection, design issues, style violations, test coverage |
| **python-implementation-specialist** | Sonnet | Core Dev | Straightforward implementation | Translate requirements to code, build utilities, standard features |
| **python-expert-architect** | Opus | Architecture | Complex architectural decisions | Async/concurrent, decorators, metaclasses, framework design |
| **code-refactoring-expert** | Opus | Architecture | Improve code structure | Safe refactoring, pattern application, technical debt reduction |
| **test-development-master** | Sonnet | Testing | TDD and test creation | Red-green-refactor, pytest, coverage analysis, Qt testing |
| **test-type-safety-specialist** | Sonnet | Testing | Type-safe test code | Test type annotations, mock typing, fixture type safety |
| **type-system-expert** | Sonnet | Testing | Type system and protocols | Type inference, protocol conformance, complex type relationships |
| **qt-ui-modernizer** | Opus | Qt | UI/UX redesign | Modern widget design, animations, QSS styling, usability |
| **qt-modelview-painter** | Opus | Qt | Model/View and painting | QAbstractItemModel, custom delegates, QPainter optimization |
| **qt-concurrency-architect** | Opus | Qt | Qt threading issues | Signal-slot threading, event loops, Qt thread safety |
| **ui-ux-validator** | Sonnet | Qt | UI validation | Accessibility, keyboard navigation, responsiveness, UX best practices |
| **deep-debugger** | Opus | Debugging | Complex bug analysis | Root cause analysis, hard-to-reproduce issues, state tracking |
| **threading-debugger** | Opus | Debugging | Threading issues | Deadlocks, race conditions, thread dumps, concurrency bugs |
| **performance-profiler** | Sonnet | Debugging | Performance optimization | CPU/memory profiling, bottleneck identification, optimization |
| **venv-keeper** | Sonnet | Support | Virtual environment management | Dependencies, environment integrity, code quality tools |
| **api-documentation-specialist** | Sonnet | Support | API design and docs | API contracts, documentation generation, interface design |

## Audit Agents (Read-Only)

| Agent | Model | Purpose | Outputs |
|-------|-------|---------|---------|
| **agent-consistency-auditor** | Sonnet | Check agent format compliance | Consistency report, validation errors |
| **documentation-quality-reviewer** | Sonnet | Review documentation quality | Documentation assessment, gaps identified |
| **best-practices-checker** | Sonnet | Verify modern practices | Practice compliance, security issues |
| **coverage-gap-analyzer** | Sonnet | Identify capability gaps | Missing capabilities, overlaps |
| **cross-reference-validator** | Sonnet | Validate agent references | Reference integrity, delegation accuracy |
| **review-synthesis-agent** | Sonnet | Synthesize review findings | Prioritized recommendations, roadmap |
| **agent-audit-orchestrator** | Sonnet | Coordinate comprehensive audits | Unified audit report |

---

## Decision Guide: Which Agent to Use?

### "I need to implement..."
- **Simple feature from specs** → `python-implementation-specialist`
- **Complex async/concurrent code** → `python-expert-architect`
- **Qt Model/View component** → `qt-modelview-painter`
- **Modern UI interface** → `qt-ui-modernizer`

### "I need to fix..."
- **A bug I can't reproduce** → `deep-debugger`
- **Deadlock or race condition** → `threading-debugger`
- **Performance problems** → `performance-profiler`
- **Code structure issues** → `code-refactoring-expert`

### "I need to review..."
- **Code quality** → `python-code-reviewer`
- **Type safety** → `type-system-expert`
- **UI usability** → `ui-ux-validator`
- **Test coverage** → `test-development-master`

### "I need to create..."
- **Test suite** → `test-development-master`
- **Type-safe tests** → `test-type-safety-specialist`
- **API documentation** → `api-documentation-specialist`
- **Architecture design** → `python-expert-architect`

---

## Common Agent Combinations

### New Feature Development
```
python-expert-architect → python-implementation-specialist → python-code-reviewer + type-system-expert → test-development-master
```

### Bug Investigation
```
deep-debugger + threading-debugger → python-code-reviewer → python-implementation-specialist → test-development-master
```

### Performance Optimization
```
performance-profiler → python-expert-architect → code-refactoring-expert → performance-profiler (verify)
```

### Qt Application Development
```
qt-ui-modernizer + qt-modelview-painter → qt-concurrency-architect → ui-ux-validator → test-development-master
```

### Code Quality Improvement
```
python-code-reviewer + type-system-expert + performance-profiler → code-refactoring-expert → test-development-master
```

---

## Model Usage Guidelines

### Opus Agents (Complex Tasks)
Use for:
- Architectural decisions
- Complex debugging
- Major refactoring
- UI/UX redesign
- Threading issues

Resource consideration: Limit to 2-3 parallel Opus agents

### Sonnet Agents (Standard Tasks)
Use for:
- Code review
- Implementation
- Testing
- Type checking
- Validation

Resource consideration: Can run 4-5 in parallel

---

## Parallel Execution Matrix

### Can Run in Parallel ✅
- All analysis agents (reviewers, profilers, validators)
- Read-only audit agents
- Different category agents (e.g., testing + documentation)

### Must Run Sequentially ⛔
- Agents modifying same files
- Implementation → Testing chain
- Analysis → Fix → Validation chain

---

## Agent Color Coding

- 🔵 **Blue** (Core Dev): python-code-reviewer, python-implementation-specialist
- 🟣 **Purple** (Architecture): python-expert-architect, code-refactoring-expert
- 🟢 **Green** (Testing): test-development-master, test-type-safety-specialist, type-system-expert
- 🟠 **Orange** (Qt): qt-ui-modernizer, qt-modelview-painter, qt-concurrency-architect, ui-ux-validator
- 🔴 **Red** (Debugging): deep-debugger, threading-debugger, performance-profiler
- 🟡 **Yellow** (Support): venv-keeper, api-documentation-specialist

---

## Quick Command Reference

To use an agent, the main Claude instance should:

1. Identify the task category
2. Select appropriate agent(s) from this reference
3. Check workflow patterns in ORCHESTRATION_WORKFLOWS.md
4. Execute with proper sequencing/parallelization
5. Synthesize results if multiple agents used

---

## Notes

- Agents cannot delegate to other agents - only main Claude orchestrates
- Always prefer the simplest agent that can accomplish the task
- Use Opus agents judiciously for complex tasks
- Combine agent outputs for comprehensive solutions
- Refer to individual agent files for detailed capabilities