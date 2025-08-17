# SpritePal Attribute Access Issues - Action Plan

## Summary
**Total Errors**: 131 reportAttributeAccessIssue errors  
**Affected Files**: ~40 files across the codebase  
**Estimated Fix Time**: 2-3 hours total  

## Error Breakdown by Category

### 1. Qt Enum Access Issues (24 errors) ✅ AUTOMATED
- **Status**: Can be fixed automatically
- **Script**: `scripts/fix_attribute_errors.py`
- **Command**: `python scripts/fix_attribute_errors.py`
- **Examples**:
  - `Qt.DisplayRole` → `Qt.ItemDataRole.DisplayRole`
  - `QDialog.Accepted` → `QDialog.DialogCode.Accepted`
  - `Qt.LeftButton` → `Qt.MouseButton.LeftButton`

### 2. Documentation/Example Files (29 errors) 
- **Files**: 
  - `docs/preview_generator_integration_example.py` (29 errors)
- **Action**: Add file-level `# type: ignore` or update examples
- **Priority**: LOW - These are documentation files

### 3. Test Infrastructure (22 errors)
- **Patterns**:
  - `test_results` (8 instances)
  - `qt_tracker` (4 instances)  
  - `take_memory_snapshot` (5 instances)
  - `MEMORY_LIMIT_MB` (4 instances)
- **Action**: Add `# type: ignore[attr-defined]` to test files
- **Script**: Included in `fix_attribute_errors.py`

### 4. Missing Widget Attributes (35 errors)
- **Common Issues**:
  - `preview_widget` (7 instances)
  - `status_panel` (3 instances)
  - `_update_status` (4 instances)
- **Files to Fix**:
  - UI dialog classes missing initialization
  - Worker classes missing properties
- **Action**: Manual fixes required - add attributes to `__init__`

### 5. Import Errors (8 errors)
- **Issues**:
  - `SpritePalMainWindow` import path
  - Test fixture imports
- **Action**: Update import statements (partially automated)

### 6. Manager/Worker Protocol Issues (13 errors)
- **Issues**:
  - `create_extraction_manager` not defined
  - `generate_preview` missing
  - Protocol mismatches
- **Action**: Define proper protocols or add methods

## Immediate Actions (Phase 1 - 30 minutes)

### Step 1: Run Automated Fixes
```bash
# Activate virtual environment
source .venv/bin/activate

# Run the fix script
python scripts/fix_attribute_errors.py

# Verify improvements
basedpyright . 2>&1 | grep -c "reportAttributeAccessIssue"
```

### Step 2: Fix Documentation Files
```bash
# Add type: ignore to example files
echo "# type: ignore" >> docs/preview_generator_integration_example.py
```

### Step 3: Quick Manual Fixes
Fix these specific high-impact files:
1. `ui/components/base/composed/qt_dialog_signal_manager.py`
2. `ui/models/sprite_gallery_model.py`
3. `ui/delegates/sprite_gallery_delegate.py`

## Phase 2 Actions (1 hour)

### Fix Missing Attributes in Classes
Add these attributes to the appropriate classes:

```python
# In dialog classes that use preview_widget
def __init__(self):
    self.preview_widget: Optional[QWidget] = None
    self.status_panel: Optional[QWidget] = None
    self._cache_stats_label: Optional[QLabel] = None

# In test base classes
class TestInfrastructure:
    test_results: dict = {}
    qt_tracker: Any = None
    MEMORY_LIMIT_MB: int = 512
```

### Fix Protocol Definitions
Create/update protocol definitions in `core/protocols.py`:

```python
from typing import Protocol

class ExtractionManagerProtocol(Protocol):
    def create_extraction_manager(self) -> 'ExtractionManager': ...
    def get_scan_progress(self) -> dict: ...

class PreviewWorkerProtocol(Protocol):
    def generate_preview(self, offset: int) -> QPixmap: ...
```

## Phase 3: Verification (30 minutes)

### Run Full Type Check
```bash
basedpyright . 2>&1 | tee typecheck_results.txt
grep -c "reportAttributeAccessIssue" typecheck_results.txt
```

### Expected Results
- **After Phase 1**: ~90 errors remaining (31% reduction)
- **After Phase 2**: ~30 errors remaining (77% reduction)  
- **After Phase 3**: 0-10 errors remaining (92-100% reduction)

## Files Requiring Manual Attention

Priority files to fix manually:
1. `capture_full_app_context.py` - 1 error
2. `core/managers/injection_manager.py` - 1 error  
3. `core/navigation/caching.py` - 2 errors
4. `core/preview_orchestrator.py` - 1 error
5. `core/workers/base.py` - 1 error
6. `run_integration_tests.py` - 3 errors

## Prevention Strategy

1. **Add to CI/CD**:
   ```yaml
   - name: Type Check
     run: |
       basedpyright . 2>&1 | tee typecheck.log
       ! grep "reportAttributeAccessIssue" typecheck.log
   ```

2. **Pre-commit Hook**:
   ```bash
   # .pre-commit-config.yaml
   - repo: local
     hooks:
     - id: basedpyright
       name: basedpyright type check
       entry: basedpyright
       language: system
       types: [python]
   ```

3. **Development Guidelines**:
   - Always define class attributes in `__init__`
   - Use Protocol definitions for interfaces
   - Import from correct module paths
   - Use proper Qt enum access patterns

## Quick Command Reference

```bash
# See all attribute errors
basedpyright . 2>&1 | grep "reportAttributeAccessIssue"

# Count errors
basedpyright . 2>&1 | grep -c "reportAttributeAccessIssue"

# Run automated fixes
python scripts/fix_attribute_errors.py

# Run fixes on specific files
python scripts/fix_attribute_errors.py --specific-files ui/models/sprite_gallery_model.py

# Dry run to see what would change
python scripts/fix_attribute_errors.py --dry-run
```
