# Dialog Migration Next Steps - Strategic Plan

## Executive Summary

This plan outlines the next steps to complete the dialog migration from DialogBase to composition architecture. We'll address critical issues first, then complete remaining migrations, and finally optimize and clean up.

## Phase 1: Fix Critical Issues in Foundation (Week 1)
**Priority: 🔴 CRITICAL**  
**Goal: Stabilize the composed implementation before propagating patterns**

### 1.1 Replace Dynamic Class Creation
**File:** `ui/dialogs/manual_offset/manual_offset_dialog_adapter.py`
**Agent:** python-implementation-specialist
**Task:**
```python
# Current (UNSAFE):
ManualOffsetDialogAdapter = type('ManualOffsetDialogAdapter', (_get_base_class(),), {...})

# Target (SAFE):
class ManualOffsetDialogAdapter:
    def __new__(cls, *args, **kwargs):
        implementation_class = _get_implementation_class()
        instance = implementation_class(*args, **kwargs)
        return instance
```

### 1.2 Implement Consistent Thread Safety
**Files:** All component files in `ui/dialogs/manual_offset/components/`
**Agent:** qt-concurrency-architect
**Tasks:**
- Add QMutexLocker to all shared state access
- Protect component initialization/cleanup
- Ensure signal disconnection is thread-safe
- Add thread annotations

### 1.3 Fix Error Handling
**Agent:** python-code-reviewer + python-implementation-specialist
**Tasks:**
```python
# Replace all bare except:
try:
    signal.disconnect()
except:  # BAD
    pass

# With specific handling:
try:
    signal.disconnect()
except (RuntimeError, TypeError) as e:  # GOOD
    logger.debug(f"Signal already disconnected: {e}")
```

### 1.4 Add Type Annotations
**Agent:** type-system-expert
**Priority Components:**
- ComponentFactory: Full typing for create/wire methods
- Signal parameters: Proper Signal[int], Signal[str] declarations  
- Component interfaces: Create formal protocols
- Return types: Add to all methods

### Parallel Execution Plan - Phase 1:
```yaml
parallel_group_1:
  - agent: python-implementation-specialist
    task: Replace dynamic class creation
    duration: 2 hours
    
  - agent: type-system-expert  
    task: Add type annotations
    duration: 3 hours
    
parallel_group_2: # After group 1
  - agent: qt-concurrency-architect
    task: Implement thread safety
    duration: 4 hours
    
  - agent: python-code-reviewer
    task: Fix error handling patterns
    duration: 2 hours
```

## Phase 2: Complete Dialog Migration (Week 2)
**Priority: 🟡 HIGH**
**Goal: Migrate remaining 4 dialogs using fixed patterns**

### 2.1 Dialog Analysis (Day 1)
**Parallel Analysis Tasks:**
```yaml
parallel_analysis:
  - agent: python-code-reviewer
    task: Analyze advanced_search_dialog.py
    output: Component breakdown document
    
  - agent: python-code-reviewer
    task: Analyze similarity_results_dialog.py
    output: Component breakdown document
    
  - agent: python-code-reviewer
    task: Analyze grid_arrangement_dialog.py
    output: Component breakdown document
    
  - agent: python-code-reviewer
    task: Analyze row_arrangement_dialog.py
    output: Component breakdown document
```

### 2.2 Dialog Implementation (Days 2-3)
**Expected component structure for each:**

#### AdvancedSearchDialog → 3 components:
- SearchEngineComponent (search logic)
- ResultsViewComponent (display results)
- FilterManagerComponent (search filters)

#### SimilarityResultsDialog → 2 components:
- SimilarityEngineComponent (comparison logic)
- ResultsDisplayComponent (show matches)

#### GridArrangementDialog → 3 components:
- GridManagerComponent (grid logic)
- PreviewComponent (visual preview)
- ArrangementControlsComponent (UI controls)

#### RowArrangementDialog → 2 components:
- RowManagerComponent (row logic)
- ArrangementUIComponent (controls)

**Parallel Implementation:**
```yaml
parallel_implementation:
  - agent: python-implementation-specialist
    task: Migrate advanced_search_dialog
    
  - agent: python-implementation-specialist
    task: Migrate similarity_results_dialog
    
  - agent: qt-modelview-painter
    task: Migrate grid_arrangement_dialog (has custom painting)
    
  - agent: python-implementation-specialist
    task: Migrate row_arrangement_dialog
```

### 2.3 Testing (Day 4)
**Agent:** test-development-master
**Tasks:**
- Create test suite for each migrated dialog
- Test both implementations with feature flag
- Verify API compatibility
- Check signal/slot connections

## Phase 3: Validation & Optimization (Week 3)
**Priority: 🟢 MEDIUM**
**Goal: Ensure production readiness**

### 3.1 Performance Validation
**Agent:** performance-profiler
**Tasks:**
```python
# Benchmark both implementations
- Dialog creation time
- Memory usage
- Signal propagation latency
- Component initialization overhead
- Resource cleanup efficiency
```

### 3.2 Memory Leak Testing
**Agent:** deep-debugger
**Tasks:**
- Test dialog creation/destruction cycles
- Monitor QObject parent-child relationships
- Check signal disconnection
- Verify worker thread cleanup
- Validate cache cleanup

### 3.3 Integration Testing
**Agent:** test-development-master
**Tasks:**
- Full application workflow tests
- Cross-dialog communication
- State persistence
- Error recovery scenarios

### 3.4 Documentation Updates
**Agent:** api-documentation-specialist
**Tasks:**
- Update API documentation
- Create migration guide
- Document component patterns
- Add code examples

## Phase 4: Cleanup & Polish (Week 4)
**Priority: 🔵 LOW**
**Goal: Prepare for deprecation**

### 4.1 Code Cleanup
- Update all test imports
- Remove temporary compatibility code
- Standardize logging
- Extract magic numbers to constants

### 4.2 Final Review
**Parallel Review:**
```yaml
parallel_final_review:
  - agent: python-code-reviewer
    task: Final code quality review
    
  - agent: type-system-expert
    task: Type safety validation
    
  - agent: qt-concurrency-architect
    task: Thread safety audit
    
  - agent: performance-profiler
    task: Performance regression check
```

## Success Metrics

### Phase 1 Success Criteria:
- ✅ No dynamic type() usage
- ✅ All shared state protected by mutexes
- ✅ Zero bare except clauses
- ✅ 100% type annotation coverage

### Phase 2 Success Criteria:
- ✅ All 4 dialogs migrated
- ✅ Feature flag works for all dialogs
- ✅ All tests passing
- ✅ API compatibility maintained

### Phase 3 Success Criteria:
- ✅ Performance within 5% of legacy
- ✅ Zero memory leaks detected
- ✅ All integration tests passing
- ✅ Documentation complete

### Phase 4 Success Criteria:
- ✅ Code review approval
- ✅ Type checker reports no errors
- ✅ Ready for deprecation warnings
- ✅ Team sign-off

## Risk Mitigation

### Risk: Breaking Production
**Mitigation:** Feature flags allow instant rollback

### Risk: Performance Regression  
**Mitigation:** Benchmark before committing changes

### Risk: Incomplete Migration
**Mitigation:** Each dialog independently toggleable

### Risk: Type Safety Issues
**Mitigation:** Run type checker in CI pipeline

## Timeline Summary

```
Week 1: Fix critical issues (Phase 1)
Week 2: Migrate remaining dialogs (Phase 2)  
Week 3: Validation & optimization (Phase 3)
Week 4: Cleanup & polish (Phase 4)

Total Duration: 4 weeks
Confidence Level: High (85%)
```

## Immediate Next Actions

1. **Fix dynamic class creation** (2 hours)
2. **Add type annotations** (3 hours)
3. **Implement thread safety** (4 hours)
4. **Fix error handling** (2 hours)

These can run in parallel pairs as outlined above.

## Command Sequences

```bash
# Start Phase 1 fixes
SPRITEPAL_USE_COMPOSED_DIALOGS=true python tests/test_unified_dialog_quick_validation.py

# After Phase 1, run type checker
python -m pyright ui/dialogs/manual_offset/ --strict

# Test thread safety
python tests/test_thread_safety_validation.py

# After Phase 2, test all dialogs
pytest tests/test_all_dialog_migration.py -v

# Performance benchmarking
python scripts/benchmark_dialog_performance.py

# Memory leak detection
python scripts/test_memory_leaks.py --cycles=1000
```

## Conclusion

This plan provides a systematic approach to completing the dialog migration with clear phases, parallel execution opportunities, and success metrics. The critical foundation fixes in Phase 1 are essential before propagating the pattern to remaining dialogs. The 4-week timeline is realistic with proper parallelization and agent coordination.