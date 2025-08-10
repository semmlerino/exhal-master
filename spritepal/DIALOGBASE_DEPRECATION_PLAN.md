# DialogBase Deprecation Plan

## Executive Summary

This document outlines the plan to deprecate and remove the legacy `DialogBase` class in favor of the new composition-based dialog architecture. The migration is designed to be gradual and safe, with multiple checkpoints and rollback capabilities.

## Current State

### Migrated Dialogs
- ✅ **SettingsDialog** - Using feature flag selector
- ✅ **UserErrorDialog** - Using feature flag selector  
- ✅ **ResumeScanDialog** - Using feature flag selector
- ✅ **TabbedDialog** - Framework dialog migrated
- ✅ **SplitterDialog** - Framework dialog migrated
- ✅ **UnifiedManualOffsetDialog** - Complex dialog migrated with components

### Legacy Dependencies
Dialogs still using DialogBase directly:
- `ui/dialogs/advanced_search_dialog.py`
- `ui/dialogs/similarity_results_dialog.py`
- `ui/grid_arrangement_dialog.py`
- `ui/row_arrangement_dialog.py`

## Deprecation Timeline

### Phase 1: Current State (Completed)
**Duration**: Completed
**Status**: ✅ Done

- Feature flag system implemented
- Core dialogs migrated with backward compatibility
- Testing infrastructure in place
- Documentation created

### Phase 2: Complete Migration (Q1 2025)
**Duration**: 4 weeks
**Status**: 🔄 In Progress

**Week 1-2**: Migrate remaining dialogs
- [ ] Migrate advanced_search_dialog
- [ ] Migrate similarity_results_dialog  
- [ ] Migrate grid_arrangement_dialog
- [ ] Migrate row_arrangement_dialog

**Week 3**: Testing and validation
- [ ] Run full regression test suite
- [ ] Performance benchmarking
- [ ] Memory leak testing
- [ ] User acceptance testing

**Week 4**: Documentation and training
- [ ] Update all documentation
- [ ] Create migration guide for external plugins
- [ ] Team training on new architecture

### Phase 3: Deprecation Warning (Q2 2025)
**Duration**: 8 weeks
**Status**: ⏳ Planned

**Actions**:
1. Add deprecation warnings to DialogBase
2. Default feature flag to composed implementation
3. Monitor for issues in production
4. Maintain dual implementation support

```python
# Add to DialogBase.__init__
import warnings
warnings.warn(
    "DialogBase is deprecated and will be removed in v3.0. "
    "Use DialogBaseMigrationAdapter or ComposedDialog instead.",
    DeprecationWarning,
    stacklevel=2
)
```

### Phase 4: Legacy Removal (Q3 2025)
**Duration**: 2 weeks
**Status**: ⏳ Planned

**Actions**:
1. Remove feature flags
2. Delete DialogBase class
3. Remove legacy implementations
4. Clean up test infrastructure
5. Update all imports

## Migration Strategy

### For Each Remaining Dialog

1. **Analysis** (1 day)
   - Document current functionality
   - Identify dependencies
   - Plan component structure

2. **Implementation** (2-3 days)
   - Create composed implementation
   - Add feature flag selector
   - Maintain API compatibility

3. **Testing** (1 day)
   - Unit tests for both implementations
   - Integration tests
   - API compatibility tests

4. **Documentation** (0.5 day)
   - Update dialog documentation
   - Add migration notes

### Risk Mitigation

**Risk 1**: Breaking changes in production
- **Mitigation**: Feature flags allow instant rollback
- **Monitoring**: Log feature flag usage and errors

**Risk 2**: Performance regression
- **Mitigation**: Benchmark before/after migration
- **Threshold**: No more than 10% performance degradation

**Risk 3**: Memory leaks
- **Mitigation**: Comprehensive cleanup testing
- **Tools**: Use memory profilers, weak references

**Risk 4**: Third-party plugin compatibility
- **Mitigation**: Maintain adapter layer for 2 release cycles
- **Communication**: Early warning to plugin developers

## Technical Tasks

### Immediate Tasks
1. Fix issues identified in code review:
   - Replace dynamic class creation with factory pattern
   - Add comprehensive error handling
   - Implement proper thread safety
   - Add missing type annotations

### Pre-removal Tasks
1. Create automated migration tool for external code
2. Build compatibility checker script
3. Set up monitoring for legacy usage
4. Create rollback procedure

### Post-removal Tasks
1. Remove feature flag infrastructure
2. Clean up test utilities
3. Update CI/CD pipelines
4. Archive legacy code for reference

## Success Criteria

### Phase 2 Success
- [ ] All dialogs migrated
- [ ] Zero regression test failures
- [ ] Performance within 10% of legacy
- [ ] No memory leaks detected

### Phase 3 Success  
- [ ] Less than 1% of sessions use legacy implementation
- [ ] No critical bugs reported
- [ ] All plugins updated or compatibility layer working

### Phase 4 Success
- [ ] Clean removal with no runtime errors
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Team trained on new architecture

## Rollback Plan

At any phase, if critical issues arise:

1. **Immediate**: Revert feature flag default
2. **24 hours**: Deploy hotfix with legacy default
3. **48 hours**: Root cause analysis
4. **1 week**: Fix issues and retry migration

## Code Cleanup Checklist

### Files to Remove
- [ ] `ui/components/base/dialog_base.py`
- [ ] Legacy dialog implementations
- [ ] Feature flag checking code
- [ ] Compatibility test infrastructure

### Files to Update
- [ ] `ui/components/base/__init__.py` - Remove DialogBase export
- [ ] All dialog imports to use new structure
- [ ] Documentation to remove legacy references
- [ ] Example code and tutorials

### Dependencies to Update
- [ ] Remove backward compatibility code
- [ ] Update type stubs
- [ ] Clean up migration adapters
- [ ] Simplify test fixtures

## Communication Plan

### Internal Communication
- **Week -4**: Team briefing on deprecation plan
- **Week -2**: Final review of migration status
- **Week 0**: Deprecation warning activated
- **Week +4**: Progress review
- **Week +8**: Go/no-go decision for removal

### External Communication
- **Week -8**: Blog post announcing deprecation
- **Week -4**: Email to registered developers
- **Week 0**: Deprecation warnings in code
- **Week +4**: Reminder about timeline
- **Week +8**: Final warning before removal

## Monitoring

### Metrics to Track
1. Feature flag usage ratio (composed vs legacy)
2. Error rates by implementation type
3. Performance metrics (response time, memory)
4. User feedback and bug reports

### Alert Thresholds
- Error rate > 0.1% - investigate
- Performance degradation > 10% - rollback
- Memory leak detected - immediate fix
- Critical bug reported - emergency response

## Final Notes

The deprecation of DialogBase represents a significant architectural improvement, moving from inheritance to composition. This plan ensures a safe, gradual transition with multiple safety nets and clear rollback procedures. The feature flag system has proven effective for this migration and can be reused for future architectural changes.

**Estimated Total Duration**: 3-4 months from current state to complete removal
**Risk Level**: Medium (mitigated by feature flags and gradual rollout)
**Impact**: High (improved maintainability, testability, and flexibility)