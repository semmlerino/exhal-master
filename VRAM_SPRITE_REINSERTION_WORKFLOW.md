# Complete VRAM Sprite Reinsertion Workflow

Here's the exact workflow to reinsert a modified sprite into VRAM:

## **Step 1: Extract Sprites from VRAM**
```bash
python3 sprite_editor/sprite_extractor.py --offset 0xC000 --size 0x4000 --output sprites_to_edit.png
```
- Extracts sprites from VRAM offset `0xC000` (VRAM address `$6000`)
- Creates indexed grayscale PNG for editing
- Size `0x4000` = 16KB of sprite data (512 tiles)

## **Step 2: Edit the Sprite**
- Open `sprites_to_edit.png` in your image editor
- **CRITICAL: Keep in indexed color mode (16 colors max)**
- Edit using only existing palette colors
- Save as PNG maintaining indexed format

## **Step 3: Inject Modified Sprite Back**
```bash
python3 sprite_editor/sprite_injector.py edited_sprites.png --vram VRAM.dmp --offset 0xC000 --output VRAM_edited.dmp --preview
```

**Parameters:**
- `edited_sprites.png` - Your modified sprite sheet
- `--vram VRAM.dmp` - Original VRAM dump file
- `--offset 0xC000` - VRAM offset (default for sprites)
- `--output VRAM_edited.dmp` - Output file for emulator
- `--preview` - Creates preview PNG of injected sprites

## **Step 4: Load in Emulator**
- Load `VRAM_edited.dmp` in your SNES emulator
- Sprites appear at VRAM address `$6000`

## **Automated Workflow Script**
```bash
# Extract sprites
python3 sprite_editor/sprite_workflow.py extract

# Edit sprites_to_edit.png in your editor...

# Inject back
python3 sprite_editor/sprite_workflow.py inject edited_sprites.png
```

## **Quick Injection (Default Settings)**
```bash
python3 sprite_editor/sprite_workflow.py quick edited_sprites.png
```

The workflow converts PNG → SNES 4bpp tiles → patches VRAM dump → ready for emulator.