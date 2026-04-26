#!/usr/bin/env python3
"""Check two test files for encoding/indentation issues."""
import sys

files = [
    'tests/test_association_discovery.py',
    'tests/test_learning_evolution_integration.py'
]

for f in files:
    with open(f, 'rb') as fh:
        raw = fh.read()
    
    issues = []
    
    # Check for null bytes
    if b'\x00' in raw:
        issues.append("NULL BYTES FOUND")
    
    # Check for non-UTF-8
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError as e:
        issues.append(f"UTF-8 decode error: {e}")
        print(f"{f}: {', '.join(issues)}")
        continue
    
    print(f"{f}: UTF-8 OK ({len(raw)} bytes, {text.count(chr(10))} lines)")
    
    # Check for mixed tabs/spaces
    lines_with_tabs = []
    lines_with_unusual = []
    
    for i, line in enumerate(text.split('\n'), 1):
        stripped = line.lstrip()
        leading = line[:len(line)-len(stripped)] if stripped != line else line
        if '\t' in leading:
            lines_with_tabs.append(i)
        for ch in leading:
            if ch not in (' ', '\t'):
                lines_with_unusual.append((i, f"U+{ord(ch):04X} ({repr(ch)})"))
    
    if lines_with_tabs:
        print(f"  TABS in indentation on lines: {lines_with_tabs[:10]}")
    else:
        print(f"  No tab indentation")
    
    if lines_with_unusual:
        print(f"  UNUSUAL whitespace: {lines_with_unusual[:10]}")
    else:
        print(f"  No unusual whitespace")
    
    if issues:
        print(f"  OTHER ISSUES: {', '.join(issues)}")
    
    # Check indentation consistency
    indent_levels = set()
    for line in text.split('\n'):
        stripped = line.lstrip()
        if stripped and not stripped.startswith('#'):
            leading = line[:len(line)-len(stripped)]
            if leading:
                indent_levels.add(len(leading))
    
    print(f"  Indent levels used: {sorted(indent_levels)}")
    
    # Verify all indents are multiples of 4
    bad_indents = [i for i in indent_levels if i % 4 != 0]
    if bad_indents:
        print(f"  WARNING: Non-multiple-of-4 indents: {bad_indents}")
    else:
        print(f"  All indents are multiples of 4")
    
    print()
