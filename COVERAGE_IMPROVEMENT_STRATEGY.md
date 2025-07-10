# Coverage Improvement Strategy

## Current Status Analysis

### ✅ High Coverage Modules (80%+)
- `sprite_assembler.py`: 100% 
- `sprite_disassembler.py`: 100%
- `sprite_injector.py`: 99%
- `sprite_extractor.py`: 98%
- `constants.py`: 100%
- `validation.py`: 100%
- `tile_utils.py`: 70%+

### 🟡 Medium Coverage Modules (40-80%)
- `sprite_editor_core.py`: ~78%
- `palette_utils.py`: ~78%
- `oam_palette_mapper.py`: ~66%
- `security_utils.py`: ~55%

### 🔴 Low/Zero Coverage Modules (0-40%)
**Priority 1 (Core functionality)**:
- `sprite_workflow.py`: 0% (70 lines)
- `png_to_snes.py`: 0% (36 lines)
- `snes_tiles_to_png.py`: 0% (49 lines)

**Priority 2 (GUI/Controllers)**:
- Controllers: 16-42% coverage
- Views: 18-31% coverage
- Workers: 30-56% coverage

**Priority 3 (Utility/Demo scripts)**:
- `compare_preview_sizes.py`: 0%
- `extract_all_palettes.py`: 0%
- `multi_palette_demo.py`: 0%
- `multi_palette_viewer.py`: 13%

## 🎯 Strategic Improvement Plan

### Phase 1: Core Module Testing (High Impact)
**Target: +15% overall coverage**

1. **Test `sprite_workflow.py` (0% → 95%)**
   - Full workflow orchestration
   - Error recovery
   - State management
   - File operations

2. **Test `png_to_snes.py` (0% → 95%)**
   - PNG conversion to SNES format
   - Various image formats
   - Error handling

3. **Test `snes_tiles_to_png.py` (0% → 95%)**
   - SNES to PNG conversion
   - Palette handling
   - File I/O

**Estimated effort**: 3-4 test files, ~200 tests

### Phase 2: Controller/Model Testing (Medium Impact)
**Target: +10% overall coverage**

4. **Test Controllers (16-42% → 80%)**
   - Extract controller: Core extraction logic
   - Inject controller: Injection workflows
   - Main controller: Application orchestration
   - Palette controller: Palette operations

5. **Test Models (25-41% → 75%)**
   - Project model: Project state management
   - Sprite model: Sprite data handling
   - Palette model: Palette operations

**Estimated effort**: 5-6 test files, ~150 tests

### Phase 3: GUI Testing (Medium Impact)
**Target: +8% overall coverage**

6. **Test Views (18-31% → 60%)**
   - Main window: Core GUI functionality
   - Tab widgets: Tab-specific logic
   - Dialogs: Modal interactions

7. **Test Workers (30-56% → 80%)**
   - Extract worker: Background extraction
   - Inject worker: Background injection
   - Signal handling and progress

**Estimated effort**: 3-4 test files, ~100 tests

### Phase 4: Integration & Edge Cases (Lower Impact)
**Target: +5% overall coverage**

8. **Improve existing module coverage**
   - Fill gaps in medium-coverage modules
   - Edge cases and error paths
   - Platform-specific code

9. **Test utility scripts**
   - Demo scripts (if used in workflows)
   - Debugging tools

**Estimated effort**: 2-3 test files, ~50 tests

## 🚀 Immediate Action Plan

### Week 1: Core Modules
```bash
# Create tests for core 0% modules
- test_sprite_workflow.py
- test_png_to_snes.py  
- test_snes_tiles_to_png.py
```

### Week 2: Controllers
```bash
# Improve controller coverage
- test_extract_controller.py (enhance existing)
- test_inject_controller.py (enhance existing)
- test_main_controller.py (new)
- test_palette_controller.py (new)
```

### Week 3: Models & GUI
```bash
# Test models and views
- test_project_model.py (enhance existing)
- test_sprite_model.py (new)
- test_main_window.py (enhance existing)
```

## 🎯 Coverage Targets

| Module Type | Current | Target | Impact |
|-------------|---------|--------|--------|
| Core Logic | 35% | 85% | High |
| Controllers | 25% | 75% | High |
| Models | 35% | 75% | Medium |
| Views | 25% | 60% | Medium |
| Workers | 45% | 80% | Medium |
| Utilities | 15% | 70% | Low |
| **Overall** | **35%** | **75%** | **+40%** |

## 🛠️ Testing Tools & Techniques

### 1. **Systematic Testing Approach**
```python
# Template for each module:
@pytest.mark.unit
class TestModuleName:
    def test_basic_functionality(self):
        """Test core happy path"""
        pass
    
    def test_error_handling(self):
        """Test error conditions"""
        pass
    
    def test_edge_cases(self):
        """Test boundary conditions"""
        pass

@pytest.mark.integration  
class TestModuleNameIntegration:
    def test_real_world_usage(self):
        """Test with real data"""
        pass
```

### 2. **Coverage-Driven Development**
- Run coverage after each test file
- Target specific uncovered lines
- Use `--cov-report=html` for visual feedback

### 3. **Mocking Strategy**
- **Minimal mocking**: Test real functionality when possible
- **Mock external dependencies**: File I/O, network, GUI when needed
- **Wrap don't replace**: Use `MagicMock(wraps=real_method)` pattern

### 4. **Test Data Management**
```python
# Shared fixtures for consistent test data
@pytest.fixture
def sample_sprite_data():
    """Real sprite data for integration tests"""
    pass

@pytest.fixture  
def temp_project(tmp_path):
    """Complete temporary project structure"""
    pass
```

## 📊 Success Metrics

- **Overall coverage**: 35% → 75% (+40%)
- **Core modules**: 100% coverage maintained
- **Critical paths**: All major workflows tested
- **Error handling**: All exception paths covered
- **GUI stability**: All Qt tests passing reliably

## 🔧 Implementation Commands

```bash
# Run coverage analysis
python3 run_tests_grouped.py

# Focus on specific modules
python3 -m pytest --cov=sprite_editor.sprite_workflow --cov-report=html

# Test new modules as created
python3 -m pytest sprite_editor/tests/test_sprite_workflow.py -v

# Check overall progress
python3 -m pytest --cov=sprite_editor --cov-report=term-missing | grep TOTAL
```

This strategy will systematically improve coverage while maintaining code quality and test reliability.