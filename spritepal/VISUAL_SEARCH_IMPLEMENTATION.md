# Visual Search Implementation

This document describes the complete implementation of visual similarity search functionality in SpritePal. The visual search allows users to find sprites that look similar to a reference sprite using perceptual hashing and similarity algorithms.

## Overview

The visual search system consists of several interconnected components:

1. **Visual Similarity Engine** (`core/visual_similarity_search.py`) - Core similarity algorithms
2. **Advanced Search Dialog** (`ui/dialogs/advanced_search_dialog.py`) - Main search interface
3. **Similarity Results Dialog** (`ui/dialogs/similarity_results_dialog.py`) - Results display
4. **Index Builder** (`build_similarity_index.py`) - Utility to create searchable indexes
5. **Demo and Test Scripts** - Testing and demonstration utilities

## Components

### 1. Visual Similarity Engine

The core engine uses multiple techniques for robust similarity matching:

- **Perceptual Hash (pHash)**: Average-based hash resistant to scaling and minor changes
- **Difference Hash (dHash)**: Structural similarity detection based on gradients  
- **Color Histogram**: Color distribution matching for palette-sensitive comparisons
- **Combined Scoring**: Weighted combination of all metrics for robust results

**Key Features:**
- Fast similarity search using Hamming distance
- Configurable similarity thresholds
- Persistent index storage using pickle
- Metadata support for additional sprite information

### 2. Advanced Search Dialog Integration

The visual search tab in the Advanced Search Dialog provides:

**UI Components:**
- Reference sprite offset input with validation
- Live preview of reference sprite
- Similarity threshold slider (0-100%)
- Search scope selection (Current ROM, All Indexed, Selected Region)
- Browse button for sprite selection

**Functionality:**
- Real-time reference sprite preview updates
- Similarity index existence checking
- Automatic index building prompts
- Integration with existing search result system

**Key Methods:**
- `_start_visual_search()`: Main search initiation
- `_update_reference_preview()`: Live preview generation
- `_show_visual_search_results()`: Results display coordination
- `_offer_to_build_similarity_index()`: Index management

### 3. Similarity Results Dialog

Specialized dialog for displaying visual search results:

**Features:**
- Grid layout with sprite thumbnails
- Similarity scores and hash distances
- Click-to-select sprite navigation
- Responsive layout with scrolling
- Integration with main application sprite selection

**Components:**
- `SimilarityResultWidget`: Individual result display
- `SimilarityResultsDialog`: Main results container
- `show_similarity_results()`: Convenience function

### 4. Search Worker Integration

The visual search is integrated into the existing `SearchWorker` threading system:

**Visual Search Process:**
1. Load similarity index from disk
2. Validate reference sprite exists in index
3. Perform similarity search with progress reporting
4. Convert results to compatible format
5. Emit results to UI thread

**Error Handling:**
- Missing similarity index detection
- Invalid reference sprite handling
- Search timeout and cancellation support
- Graceful degradation for corrupted indexes

## Usage Workflow

### For Users

1. **Open Advanced Search Dialog**
   - Navigate to ROM extraction or main interface
   - Open Advanced Search (Ctrl+Shift+F or menu)
   - Switch to "Visual Search" tab

2. **Select Reference Sprite**
   - Enter sprite offset manually (e.g., "0x80000")  
   - Use Browse button for guided selection
   - Preview updates automatically

3. **Configure Search**
   - Adjust similarity threshold (default 80%)
   - Select search scope (usually "Current ROM")

4. **Execute Search**
   - Click "Search" button
   - Monitor progress bar
   - Review results in similarity dialog

5. **Navigate Results**
   - Click on result thumbnails to view
   - Use "Go to Sprite" buttons for navigation
   - Results sorted by similarity score

### For Developers

1. **Build Similarity Index**
   ```bash
   python build_similarity_index.py rom_file.sfc
   ```

2. **Test Visual Search**
   ```bash
   python test_visual_search.py rom_file.sfc
   ```

3. **Run Demo**
   ```bash
   python demo_visual_search.py rom_file.sfc
   ```

## Implementation Details

### Similarity Algorithm

The similarity score combines three metrics:

```python
total_similarity = (
    phash_similarity * 0.4 +    # Structural similarity
    dhash_similarity * 0.3 +    # Gradient similarity  
    hist_similarity * 0.3       # Color similarity
)
```

### Performance Optimizations

- **Lazy Loading**: Indexes loaded only when needed
- **Caching**: Preview generation cached for performance
- **Threading**: Search operations run in background threads
- **Progress Reporting**: Real-time feedback for long operations

### Error Recovery

- **Missing Index**: Offers to build index automatically
- **Corrupted Index**: Graceful fallback with error reporting
- **Invalid Offsets**: Input validation with helpful error messages
- **Search Timeouts**: Cancellation support with partial results

## File Structure

```
spritepal/
├── core/
│   └── visual_similarity_search.py    # Core similarity engine
├── ui/
│   └── dialogs/
│       ├── advanced_search_dialog.py   # Main search interface
│       └── similarity_results_dialog.py # Results display
├── build_similarity_index.py           # Index building utility
├── test_visual_search.py              # Testing script
├── demo_visual_search.py              # Demonstration app
└── VISUAL_SEARCH_IMPLEMENTATION.md    # This documentation
```

## Configuration

### Similarity Engine Parameters

- `hash_size`: Hash dimensions (default: 8 = 64-bit hash)
- `similarity_threshold`: Minimum match score (0.0-1.0)
- `max_results`: Maximum results to return

### Search Parameters

- `start_offset`: ROM scan start position
- `end_offset`: ROM scan end position  
- `step_size`: Scanning increment (affects thoroughness vs speed)

### UI Settings

- `preview_size`: Reference sprite preview dimensions
- `grid_columns`: Results dialog grid layout
- `cache_size`: Preview cache maximum entries

## Edge Cases

### No Similarity Index

**Problem**: Visual search requires pre-built similarity index
**Solution**: Automatic detection with user prompt to build index
**Fallback**: Clear error message with building instructions

### Reference Sprite Not Found

**Problem**: User enters offset not in similarity index
**Solution**: Validation with specific error message
**Fallback**: Suggest re-scanning or different offset

### No Similar Sprites

**Problem**: Reference sprite has no matches above threshold
**Solution**: Results dialog shows "no results" with suggestions
**Fallback**: Suggest lowering similarity threshold

### Corrupted Index

**Problem**: Similarity index file damaged or incompatible
**Solution**: Error detection with option to rebuild
**Fallback**: Graceful degradation with error reporting

## Future Enhancements

### Near-term Improvements

1. **Advanced Sprite Browser**: Visual sprite selection interface
2. **Batch Processing**: Index building for multiple ROMs
3. **Custom Similarity Weights**: User-adjustable algorithm parameters
4. **Export Results**: Save similarity search results to file

### Long-term Enhancements

1. **LSH Indexing**: Locality-sensitive hashing for very large databases
2. **Machine Learning**: Neural network-based similarity detection
3. **Animation Detection**: Temporal similarity for sprite sequences
4. **Cross-ROM Search**: Search across multiple game databases

## Testing

### Manual Testing

1. Run `demo_visual_search.py` with a ROM file
2. Build index using the demo interface
3. Test search with various offsets and thresholds
4. Verify results display and navigation

### Automated Testing

```bash
# Build index for testing
python build_similarity_index.py test_rom.sfc -s 0x80000 -e 0x100000

# Run visual search test
python test_visual_search.py test_rom.sfc
```

### Integration Testing

The visual search integrates with existing SpritePal testing infrastructure:

```bash
# Run relevant tests
pytest tests/ -k "visual" -v

# Run with GUI tests (if available)
pytest tests/ -m "gui" --capture=no
```

## Troubleshooting

### Common Issues

1. **"No similarity index found"**
   - Run `build_similarity_index.py` first
   - Verify ROM file path is correct

2. **"Reference sprite not found in index"**
   - Check offset is within scanned range
   - Verify offset contains valid sprite data

3. **"No similar sprites found"**
   - Lower similarity threshold
   - Try different reference sprite
   - Verify index contains multiple sprites

4. **Preview not showing**
   - Check ROM file accessibility
   - Verify offset points to valid sprite data
   - Check preview generation dependencies

### Debug Mode

Enable verbose logging for troubleshooting:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

This provides detailed information about:
- Index loading and validation
- Similarity calculations
- Preview generation
- Error conditions

## Conclusion

The visual similarity search implementation provides a comprehensive solution for finding visually similar sprites in ROM files. The system is designed for robustness, performance, and extensibility, with clear error handling and user guidance throughout the workflow.

The modular design allows for easy enhancement and integration with other SpritePal components, while the thorough testing framework ensures reliability across different ROM types and usage scenarios.