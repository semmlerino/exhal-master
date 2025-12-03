# Next Steps Plan: Finding Real Kirby Sprites

## 🔴 Problem Summary
- **What Failed**: Extracted data from 0x0C0000, 0x349D33, etc. shows no recognizable sprites
- **Root Cause**: Never used Mesen 2 to trace actual sprites - just guessed offsets
- **Result**: Likely extracted background tiles or level data, not character sprites

## 🎯 Strategic Options (Ranked by Likelihood of Success)

### Option 1: Use Mesen 2 Properly (Most Reliable)
**Success Rate: 95%** - This is the proven method

#### Prerequisites:
- [ ] Install Mesen 2 emulator
- [ ] Have Kirby Super Star ROM loaded
- [ ] Have `trace_sprite_guide.py` ready

#### Steps:
1. **Launch Mesen 2 with Kirby Super Star**
   ```bash
   # Run the interactive guide
   python trace_sprite_guide.py
   ```

2. **Find Kirby in Game**
   - Start game, enter Green Greens
   - Pause when Kirby is clearly visible
   - Take screenshot for reference

3. **Locate in VRAM**
   - Tools → Tile Viewer
   - Look for Kirby's round shape in sprite tiles
   - Note VRAM address (e.g., $2000)

4. **Set Breakpoint**
   - Debug → Debugger
   - Add VRAM write breakpoint at that address
   - Reset to before level loads

5. **Trace to ROM**
   - Continue execution
   - When breakpoint hits, check DMA registers
   - Note source address (e.g., $XX:YYYY)

6. **Extract Verified Sprite**
   ```bash
   python mesen2_sprite_extractor.py $XX:YYYY
   ```

### Option 2: Use Community Resources (Quick Win)
**Success Rate: 80%** - Leverage existing work

#### Immediate Actions:
1. **Download Pre-Extracted Sprites**
   - Visit [The Spriters Resource](https://www.spriters-resource.com/snes/kirbysuperstar/)
   - Compare their sprites with our attempts
   - Identify what real sprites should look like

2. **Search ROM Hacking Forums**
   ```python
   # Search for documented offsets
   searches = [
       "Kirby Super Star sprite offset",
       "Kirby graphics location ROM",
       "ExHAL Kirby character data"
   ]
   ```

3. **Check GitHub Projects**
   - Look for Kirby Super Star disassembly projects
   - Find ROM maps with sprite locations
   - Clone and examine extraction tools

### Option 3: Systematic ROM Scanning (Brute Force)
**Success Rate: 60%** - Time-consuming but thorough

#### Approach:
1. **Scan for Sprite Patterns**
   ```python
   # Scan ROM for HAL compression headers
   for offset in range(0, rom_size, 0x100):
       if is_hal_compressed(offset):
           decompress_and_check(offset)
   ```

2. **Pattern Recognition**
   - Look for 16x16 or 32x32 tile groups
   - Check for symmetrical patterns (characters)
   - Identify animation frame sequences

3. **Visual Validation**
   - Generate previews for all candidates
   - Manual inspection for character shapes

### Option 4: Reverse Engineer from Save States (Advanced)
**Success Rate: 70%** - Requires technical knowledge

#### Method:
1. **Create Save State**
   - Save state with Kirby on screen
   - Extract VRAM contents from state file
   - Identify sprite tiles directly

2. **Cross-Reference with ROM**
   - Search ROM for matching tile data
   - Find compressed source
   - Verify with ExHAL

## 📊 Validation Criteria

### How to Know We Found Real Sprites:
1. **Visual Check**
   - [ ] Clear character shapes visible
   - [ ] Consistent art style
   - [ ] Animation frames align

2. **Technical Check**
   - [ ] Tiles form 16x16 or 32x32 sprites
   - [ ] <30% empty tiles (not 54%)
   - [ ] Palette indices make sense

3. **Community Validation**
   - [ ] Matches known sprite sheets
   - [ ] Other hackers confirm offsets

## 🚀 Recommended Action Plan

### Phase 1: Quick Validation (1 hour)
1. **Download known good sprites** from Spriters Resource
2. **Compare structure** with our extracted data
3. **Identify differences** (tile arrangement, format, etc.)

### Phase 2: Mesen 2 Tracing (2-3 hours)
1. **Install Mesen 2** if not already available
2. **Follow trace_sprite_guide.py** step-by-step
3. **Document found addresses** in known_sprites.json
4. **Extract and verify** with visual inspection

### Phase 3: Community Research (1-2 hours)
1. **Search ROM hacking forums** for documented offsets
2. **Check GitHub** for disassembly projects
3. **Ask in Discord/forums** if stuck

### Phase 4: Systematic Scanning (if needed)
1. **Write scanner script** to find all HAL compressed data
2. **Extract all candidates** to separate folder
3. **Batch generate previews**
4. **Manual inspection** for sprites

## 💡 Key Insights

### Why Our Current Data Isn't Sprites:
- **No character shapes** → Not character graphics
- **54% empty** → Wrong data type (sprites are denser)
- **Random patterns** → Viewing non-graphics as tiles

### What We're Looking For:
- **Kirby**: Round body, feet, facial features
- **Enemies**: Recognizable shapes (Waddle Dee, etc.)
- **Items**: Stars, food, power-ups
- **UI Elements**: Health bars, text, icons

## 📝 Success Metrics

- [ ] Find and extract Kirby's sprite
- [ ] Find at least 3 enemy sprites
- [ ] Document verified ROM offsets
- [ ] Create visual proof (clear sprite sheet)
- [ ] Update known_sprites.json with findings

## ⚠️ Common Pitfalls to Avoid

1. **Don't assume** decompression success = sprites
2. **Don't skip** visual validation
3. **Don't ignore** community resources
4. **Don't guess** - trace or use verified offsets

## 🎮 Tools Ready to Use

- ✅ `trace_sprite_guide.py` - Interactive Mesen 2 guide
- ✅ `mesen2_sprite_extractor.py` - Extract from SNES addresses
- ✅ `batch_sprite_extractor.py` - Process multiple sprites
- ✅ ExHAL - Decompress HAL data
- ✅ Visualization scripts - Generate sprite sheets

---

**Next Immediate Step**: Download sprites from Spriters Resource to understand what we're looking for, then use Mesen 2 to trace actual sprite locations.