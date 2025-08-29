# Sprite Discovery Workflow Consolidation Guide

## Problem Statement
Finding sprites in-game (Mesen2) and extracting them (SpritePal) requires manual offset transcription, which is error-prone and breaks flow.

## Recommended Solution: Progressive Enhancement

### Phase 1: Clipboard Integration (Immediate - 30 mins)
**Status: Implemented in Lua script**

#### Mesen2 Side (Lua Script)
- **Key 9**: Display all sprite offsets (3 seconds)
- **Key 0**: Copy first sprite offset to clipboard file
- **Key 3**: Export session JSON with all discovered sprites

The Lua script now writes to:
- `sprite_clipboard.txt` - Single offset for quick transfer
- `sprite_session_*.json` - Complete session data

#### SpritePal Side Integration
Add to `ui/tabs/manual_offset/browse_tab.py`:

```python
def read_clipboard_offset(self) -> Optional[int]:
    """Read offset from Mesen2 clipboard file."""
    clipboard_file = Path.home() / "Mesen2" / "sprite_clipboard.txt"
    if clipboard_file.exists():
        try:
            with open(clipboard_file, 'r') as f:
                offset_str = f.read().strip()
                if offset_str.startswith("0x"):
                    return int(offset_str, 16)
                elif offset_str.startswith("$"):
                    return int(offset_str[1:], 16)
        except (ValueError, IOError):
            pass
    return None

def paste_from_clipboard(self):
    """Navigate to offset from clipboard."""
    offset = self.read_clipboard_offset()
    if offset:
        self.set_offset(offset)
        self.manual_spinbox.setValue(offset)
```

Add button to UI:
```python
self.paste_button = QPushButton("📋 Paste Offset")
self.paste_button.clicked.connect(self.paste_from_clipboard)
```

### Phase 2: Session Import (Next Step - 2 hours)

#### Data Flow
1. Play game in Mesen2, sprites are tracked automatically
2. Press key to export session JSON
3. In SpritePal, "Import Session" shows sprite gallery
4. Click any sprite to jump to its offset

#### Session JSON Format
```json
{
  "timestamp": "2024-01-19 15:30:00",
  "frame_count": 1800,
  "sprites_found": [
    {
      "offset": "0x3798ED",
      "tile": 45,
      "palette": 3,
      "size": "16x16",
      "position": {"x": 120, "y": 80}
    }
  ]
}
```

### Phase 3: Live Monitoring (Future - 1 week)

#### Architecture
```
Mesen2 → Named Pipe → SpritePal Monitor → Live Gallery
```

- Real-time sprite discovery feed
- Click to extract from live view
- Automatic sprite grouping by context

## Usage Workflow

### Current (Manual)
1. See sprite in game
2. Press 9 to show offsets
3. Write down offset
4. Open SpritePal
5. Type offset manually
6. Extract

### With Clipboard (Phase 1)
1. See sprite in game
2. Press 0 to copy offset
3. In SpritePal, click "Paste"
4. Extract

### With Session (Phase 2)
1. Play game normally
2. Export session when done
3. Import in SpritePal
4. Browse visual gallery
5. Click sprites to extract

## Benefits Analysis

| Approach | Implementation Time | Friction Reduction | Value |
|----------|-------------------|-------------------|-------|
| Clipboard | 30 mins | 60% | High |
| Session Import | 2 hours | 80% | Very High |
| Live Monitor | 1 week | 95% | Excellent |
| Unified App | Months | 99% | Ideal but costly |

## Technical Considerations

### Why Not Direct Clipboard?
- Mesen2 Lua API doesn't have clipboard access
- File-based transfer is more reliable
- Allows for richer data (JSON sessions)

### Why Not Memory Sharing?
- Cross-process memory sharing is complex
- Platform-specific implementation needed
- File-based is simpler and portable

### Future Enhancements
1. **Visual Similarity Search**: Screenshot → Find in ROM
2. **Sprite Relationships**: Track which sprites appear together
3. **Auto-naming**: Context-based sprite naming
4. **Batch Operations**: Extract all sprites from a level

## Implementation Priority

1. **Today**: Clipboard button in SpritePal
2. **This Week**: Session import UI
3. **Next Month**: Live monitoring prototype
4. **Future**: Consider unified application

## Conclusion

The clipboard + session approach provides 80% of the value with 20% of the effort. It maintains tool separation while dramatically reducing friction. The progressive enhancement path allows for incremental improvements without architectural changes.