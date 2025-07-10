# Security Review Report - Pixel Editor Codebase

## Executive Summary

This security review covers the pixel editor codebase with focus on `indexed_pixel_editor.py`, `sprite_injector.py`, `sprite_extractor.py`, and file I/O operations. The review identified several security concerns ranging from low to high severity.

## Findings by Severity

### HIGH SEVERITY

#### 1. Path Traversal Vulnerabilities
**Files Affected:** Multiple files including `indexed_pixel_editor.py`, `sprite_injector.py`, `sprite_extractor.py`

**Issue:** The codebase lacks proper path validation and sanitization, allowing potential path traversal attacks.

**Examples:**
- `indexed_pixel_editor.py:147`: `file_path = os.path.abspath(file_path)` - While `abspath` is used, there's no validation against directory traversal
- `sprite_injector.py:85`: Direct file opening without path validation: `with open(vram_file, "rb") as f:`
- `sprite_extractor.py:38`: `with open(vram_file, "rb") as f:` - No validation of file path

**Risk:** Attackers could read/write files outside intended directories using paths like `../../../../etc/passwd`

**Recommendation:** 
- Implement path sanitization function that validates against a whitelist of allowed directories
- Use `os.path.realpath()` and check if resolved path is within allowed directory
- Reject paths containing `..` segments

#### 2. Command Injection Risk
**Files Affected:** `sprite_editor/controllers/viewer_controller.py`, various test files

**Issue:** Usage of `subprocess.run()` with potentially user-controlled input

**Examples:**
- `viewer_controller.py`: Uses `subprocess.run(["open", tmp.name])` where tmp.name could be manipulated
- Multiple test files use `subprocess.run()` with constructed commands

**Risk:** If user input reaches subprocess commands, arbitrary command execution is possible

**Recommendation:**
- Never construct shell commands from user input
- Use `subprocess.run()` with `shell=False` (default) and pass arguments as list
- Validate all inputs before passing to subprocess

### MEDIUM SEVERITY

#### 3. Insufficient Input Validation
**Files Affected:** All major modules

**Issue:** Limited validation of user inputs, especially for numeric values and file formats

**Examples:**
- `sprite_injector.py:189`: `offset = int(args.offset, 16)` - No validation of hex input range
- `indexed_pixel_editor.py:1403`: `valid_index = max(0, min(15, index))` - Silent clamping instead of validation
- No validation of PNG file structure beyond mode check

**Risk:** Could lead to unexpected behavior, crashes, or exploitation of parsing vulnerabilities

**Recommendation:**
- Add comprehensive input validation for all user inputs
- Validate file formats thoroughly before processing
- Use explicit error handling instead of silent value clamping

#### 4. JSON Parsing Without Size Limits
**Files Affected:** `indexed_pixel_editor.py`, palette handling modules

**Issue:** JSON files are loaded without size restrictions

**Examples:**
- `indexed_pixel_editor.py:124`: `loaded = json.load(f)` - No size check
- `indexed_pixel_editor.py:1014`: `palette_data = json.load(f)` - Could load arbitrarily large files

**Risk:** Large JSON files could cause memory exhaustion (DoS)

**Recommendation:**
- Check file size before loading
- Use streaming JSON parser for large files
- Set reasonable limits on palette/metadata file sizes

#### 5. Resource Exhaustion - Image Operations
**Files Affected:** Image processing modules

**Issue:** No limits on image dimensions or memory usage

**Examples:**
- PNG loading doesn't check dimensions before allocation
- No limits on tile count or sprite sheet size
- `Image.new()` calls without size validation

**Risk:** Large images could exhaust memory causing DoS

**Recommendation:**
- Implement maximum image dimension limits
- Check available memory before large allocations
- Add progress indication for long operations

### LOW SEVERITY

#### 6. Information Disclosure
**Files Affected:** `indexed_pixel_editor.py`, debug/logging code

**Issue:** Debug mode exposes internal paths and system information

**Examples:**
- `indexed_pixel_editor.py:55`: `DEBUG_MODE = True` - Hardcoded to True
- Full file paths exposed in error messages
- Stack traces shown to users

**Risk:** Leaks system information useful for attackers

**Recommendation:**
- Set `DEBUG_MODE = False` for production
- Sanitize error messages to remove sensitive paths
- Log detailed errors server-side, show generic messages to users

#### 7. Missing File Type Validation
**Files Affected:** All file I/O operations

**Issue:** Files are opened based on extension without validating actual content

**Examples:**
- PNG files validated only by PIL, not by magic bytes
- Binary files (.bin, .dmp) opened without format validation
- Palette files (.pal.json) not validated against schema

**Risk:** Malformed files could trigger parsing vulnerabilities

**Recommendation:**
- Check file magic bytes/headers before processing
- Implement format validators for each file type
- Use schema validation for JSON files

#### 8. Unsafe Default Permissions
**Files Affected:** `indexed_pixel_editor.py`

**Issue:** Settings directory created without explicit permissions

**Example:**
- `indexed_pixel_editor.py:100`: `self.settings_dir.mkdir(exist_ok=True)` - Uses default umask

**Risk:** Settings files might be world-readable

**Recommendation:**
- Set explicit permissions (0o700) on settings directory
- Set restrictive permissions on settings files

## Additional Observations

### Positive Security Practices
1. Use of `os.path.abspath()` in many places (though not sufficient alone)
2. No use of `eval()` or `exec()` in core code
3. Subprocess calls mostly use list arguments (safer than shell strings)
4. Input mode validation for images

### Areas Needing Improvement
1. No centralized input validation framework
2. No security headers or CSRF protection (if web interface planned)
3. No rate limiting on file operations
4. No audit logging of security-relevant events

## Recommendations Summary

### Immediate Actions (High Priority)
1. Implement path traversal protection with whitelist-based validation
2. Add size limits for all file operations
3. Validate all numeric inputs with explicit ranges
4. Disable debug mode in production

### Short-term Actions (Medium Priority)
1. Add comprehensive input validation layer
2. Implement file type validation by content
3. Add resource limits for image operations
4. Improve error handling to avoid information leakage

### Long-term Actions (Low Priority)
1. Implement security logging and monitoring
2. Add automated security testing to CI/CD
3. Consider sandboxing for file operations
4. Implement principle of least privilege for file access

## Code Examples for Fixes

### Path Validation Function
```python
import os

def validate_file_path(file_path, allowed_dirs=None):
    """Validate file path against directory traversal attacks"""
    if allowed_dirs is None:
        allowed_dirs = [os.getcwd()]
    
    # Resolve to absolute path
    abs_path = os.path.abspath(file_path)
    real_path = os.path.realpath(abs_path)
    
    # Check if path is within allowed directories
    for allowed_dir in allowed_dirs:
        allowed_real = os.path.realpath(allowed_dir)
        if real_path.startswith(allowed_real + os.sep) or real_path == allowed_real:
            return real_path
    
    raise ValueError(f"Path '{file_path}' is not within allowed directories")
```

### Input Validation Example
```python
def validate_offset(offset_str):
    """Validate hex offset input"""
    try:
        offset = int(offset_str, 16)
        if offset < 0 or offset > 0xFFFFFF:  # Example max
            raise ValueError(f"Offset {offset_str} out of valid range")
        return offset
    except ValueError as e:
        raise ValueError(f"Invalid hex offset: {offset_str}") from e
```

### File Size Check
```python
def safe_load_json(file_path, max_size=10*1024*1024):  # 10MB default
    """Load JSON file with size limit"""
    file_path = validate_file_path(file_path)
    
    file_size = os.path.getsize(file_path)
    if file_size > max_size:
        raise ValueError(f"File too large: {file_size} bytes (max: {max_size})")
    
    with open(file_path, 'r') as f:
        return json.load(f)
```

## Conclusion

The pixel editor codebase shows good programming practices but lacks comprehensive security controls. The most critical issues are path traversal vulnerabilities and insufficient input validation. Implementing the recommended fixes would significantly improve the security posture of the application.

Priority should be given to path validation and input sanitization as these represent the highest risk vulnerabilities that could be exploited by malicious users.