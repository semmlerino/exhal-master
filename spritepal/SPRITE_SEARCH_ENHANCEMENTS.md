# Sprite Search Enhancement Implementation Guide

This guide describes how to integrate the new sprite search enhancements into SpritePal.

## Overview of Enhancements

### 1. **Parallel Sprite Search** (3-4x speedup)
- Divides ROM into chunks for concurrent searching
- Adaptive step sizing based on sprite density
- Multi-threaded decompression and validation

### 2. **Visual Similarity Search**
- Find sprites that look similar using perceptual hashing
- Identify animation sequences and sprite variations
- Export/import similarity databases

### 3. **Advanced Search UI**
- Multiple search modes (parallel, visual, pattern)
- Rich filtering options
- Search history with replay
- Keyboard shortcuts for power users

## Integration Steps

### Step 1: Update Dependencies

Add to `requirements.txt`:
```
scipy>=1.11.0  # For DCT in perceptual hashing
Pillow>=10.0.0  # Already included
numpy>=1.24.0  # For hash calculations
```

### Step 2: Wire Up Advanced Search Dialog

In `ui/rom_extraction_panel.py`, add menu item:

```python
def _setup_search_menu(self):
    """Add advanced search to toolbar or menu."""
    # In toolbar setup
    self.advanced_search_action = QAction("Advanced Search...", self)
    self.advanced_search_action.setShortcut("Ctrl+Shift+F")
    self.advanced_search_action.triggered.connect(self._open_advanced_search)
    self.toolbar.addAction(self.advanced_search_action)

def _open_advanced_search(self):
    """Open advanced search dialog."""
    if not self.rom_path:
        QMessageBox.warning(self, "No ROM", "Please load a ROM first")
        return
    
    from ui.dialogs.advanced_search_dialog import AdvancedSearchDialog
    
    dialog = AdvancedSearchDialog(self.rom_path, self)
    dialog.sprite_selected.connect(self._navigate_to_sprite)
    dialog.exec()
```

### Step 3: Replace Linear Scanner

In `ui/rom_extraction/workers/scan_worker.py`, update to use parallel finder:

```python
def run(self):
    """Use parallel finder for better performance."""
    try:
        from core.parallel_sprite_finder import ParallelSpriteFinder
        
        # Create parallel finder
        finder = ParallelSpriteFinder(
            num_workers=4,  # Or from settings
            step_size=self.step_size
        )
        
        # Search with progress
        results = finder.search_parallel(
            self.rom_path,
            self.start_offset,
            self.end_offset,
            progress_callback=self._emit_progress,
            cancellation_token=self._cancel_requested
        )
        
        # Emit results
        for result in results:
            sprite_data = {
                'offset': result.offset,
                'size': result.size,
                'compressed_size': result.compressed_size,
                'tile_count': result.tile_count,
                'confidence': result.confidence
            }
            self.sprite_found.emit(result.offset, sprite_data)
        
        self.finished.emit()
        
    except Exception as e:
        self.error.emit(str(e))
    finally:
        if finder:
            finder.shutdown()
```

### Step 4: Add Visual Search to Context Menu

In `ui/rom_extraction_panel.py`, add to sprite context menu:

```python
def _create_sprite_context_menu(self, offset: int):
    """Add visual search option."""
    menu = QMenu()
    
    # Existing options...
    
    # Add visual search
    find_similar_action = QAction("Find Similar Sprites...", menu)
    find_similar_action.triggered.connect(
        lambda: self._find_similar_sprites(offset)
    )
    menu.addAction(find_similar_action)
    
    return menu

def _find_similar_sprites(self, reference_offset: int):
    """Find sprites similar to the selected one."""
    # Use visual similarity engine
    if not hasattr(self, '_similarity_engine'):
        from core.visual_similarity_search import VisualSimilarityEngine
        self._similarity_engine = VisualSimilarityEngine()
        self._index_current_sprites()
    
    # Find similar
    matches = self._similarity_engine.find_similar(
        reference_offset,
        max_results=20,
        similarity_threshold=0.8
    )
    
    # Display results
    self._show_similarity_results(matches)
```

### Step 5: Enable Keyboard Shortcuts

Add to `ui/managers/keyboard_handler.py`:

```python
SPRITE_SEARCH_SHORTCUTS = {
    'Ctrl+F': 'quick_search',           # Quick search bar
    'Ctrl+Shift+F': 'advanced_search',  # Advanced search dialog
    'F3': 'find_next',                  # Next search result
    'Shift+F3': 'find_previous',        # Previous search result
    'Ctrl+G': 'goto_offset',            # Go to offset dialog
    '/': 'search_current_view',         # Search in current view
}
```

### Step 6: Add Performance Settings

In `utils/constants.py`, add:

```python
# Parallel search settings
PARALLEL_SEARCH_WORKERS = 4
PARALLEL_SEARCH_CHUNK_SIZE = 0x40000  # 256KB
ADAPTIVE_STEP_MIN = 0x10
ADAPTIVE_STEP_MAX = 0x2000

# Visual search settings
PERCEPTUAL_HASH_SIZE = 8
SIMILARITY_CACHE_SIZE = 10000
VISUAL_SEARCH_BATCH_SIZE = 100
```

### Step 7: Create Search Cache

For persistent search results and faster repeated searches:

```python
class SpriteSearchCache:
    """Cache search results for performance."""
    
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)
        
    def get_cache_key(self, rom_path: str, params: dict) -> str:
        """Generate cache key from search parameters."""
        import hashlib
        rom_hash = hashlib.md5(Path(rom_path).read_bytes()).hexdigest()[:8]
        param_str = json.dumps(params, sort_keys=True)
        param_hash = hashlib.md5(param_str.encode()).hexdigest()[:8]
        return f"{rom_hash}_{param_hash}"
    
    def save_results(self, key: str, results: list):
        """Save search results to cache."""
        cache_file = self.cache_dir / f"{key}.cache"
        with open(cache_file, 'wb') as f:
            pickle.dump(results, f)
    
    def load_results(self, key: str) -> list | None:
        """Load cached results if available."""
        cache_file = self.cache_dir / f"{key}.cache"
        if cache_file.exists():
            with open(cache_file, 'rb') as f:
                return pickle.load(f)
        return None
```

## Performance Optimization Tips

### 1. Pre-build Similarity Index
For ROMs that are frequently searched, pre-build the similarity index:

```python
# On first ROM load
def _prebuild_search_index(self):
    """Build search indexes in background."""
    from core.visual_similarity_search import VisualSimilarityEngine
    
    # Run in background thread
    def build_index():
        engine = VisualSimilarityEngine()
        # Index all found sprites
        for offset, sprite_data in self.found_sprites.items():
            if sprite_data.get('image'):
                engine.index_sprite(offset, sprite_data['image'])
        # Save index
        engine.export_index(self._get_index_path())
    
    QThreadPool.globalInstance().start(build_index)
```

### 2. Use Memory Mapping for Large ROMs
For very large ROMs, use memory mapping:

```python
import mmap

def open_rom_mmap(rom_path: str):
    """Open ROM with memory mapping for efficient access."""
    with open(rom_path, 'rb') as f:
        return mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
```

### 3. GPU Acceleration (Future)
For even faster visual similarity search, consider GPU acceleration:

```python
# Future enhancement using CuPy or PyTorch
def calculate_phash_gpu(images_batch):
    """Calculate perceptual hashes on GPU."""
    # Convert to GPU arrays
    # Apply DCT using cuFFT
    # Return hashes
    pass
```

## Testing

### Unit Tests
```python
def test_parallel_search_performance():
    """Verify parallel search is faster than linear."""
    rom_data = create_test_rom(size=10*1024*1024)  # 10MB
    
    # Linear search
    start = time.time()
    linear_results = linear_search(rom_data)
    linear_time = time.time() - start
    
    # Parallel search
    start = time.time()
    parallel_results = parallel_search(rom_data, workers=4)
    parallel_time = time.time() - start
    
    # Verify same results
    assert len(linear_results) == len(parallel_results)
    
    # Verify speedup
    speedup = linear_time / parallel_time
    assert speedup > 2.0  # At least 2x faster
```

### Integration Tests
```python
def test_visual_similarity_accuracy():
    """Test visual similarity finds related sprites."""
    # Create test sprites with variations
    base_sprite = create_test_sprite(pattern="mario_stand")
    variations = [
        create_test_sprite(pattern="mario_stand", palette_shift=10),
        create_test_sprite(pattern="mario_walk1"),
        create_test_sprite(pattern="luigi_stand"),
    ]
    
    # Index sprites
    engine = VisualSimilarityEngine()
    engine.index_sprite(0x1000, base_sprite)
    for i, var in enumerate(variations):
        engine.index_sprite(0x2000 + i*0x100, var)
    
    # Find similar
    matches = engine.find_similar(0x1000, threshold=0.7)
    
    # Verify palette swap is most similar
    assert matches[0].offset == 0x2000
    assert matches[0].similarity_score > 0.9
```

## Deployment Checklist

- [ ] Update requirements.txt with new dependencies
- [ ] Add search enhancement settings to config
- [ ] Create help documentation for new features
- [ ] Update keyboard shortcuts reference
- [ ] Test on multiple ROM types
- [ ] Profile memory usage with large ROMs
- [ ] Verify thread safety of parallel search
- [ ] Add feature flag for gradual rollout
- [ ] Create tutorial video for advanced search

## Future Enhancements

1. **Machine Learning Sprite Detection**
   - Train model on known sprite patterns
   - Automatic sprite type classification

2. **Cloud Search Index**
   - Share sprite databases between users
   - Community-sourced sprite locations

3. **Real-time Search**
   - Search as you type with instant results
   - Live preview during search

4. **Batch Operations**
   - Search multiple ROMs simultaneously
   - Export all found sprites at once