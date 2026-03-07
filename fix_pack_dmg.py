import os

with open('pack_dmg.sh', 'r') as f:
    lines = f.readlines()

# Find the conversion line
final_lines = []
found_convert = False
for i, line in enumerate(lines):
    final_lines.append(line)
    if 'hdiutil convert "$TEMP_DMG"' in line:
        found_convert = True
        # Keep next line (rm -f TEMP_DMG)
        final_lines.append(lines[i+1])
        break

if found_convert:
    # Add the clean icon logic
    new_tail = '''
# v2.8.16 Sets custom icon for the DMG file itself
DMG_FILE="dist/$DMG_NAME"
ICON_SOURCE="assets/DMG-box.png"
if [ -f "$ICON_SOURCE" ] && [ -f "$DMG_FILE" ]; then
    echo "[DMG] Setting custom icon to DMG file..."
    if command -v fileicon &> /dev/null; then
        fileicon set "$DMG_FILE" "$ICON_SOURCE"
    else
        # Fallback for Jimmy's environment
        if [ -f "/usr/local/bin/fileicon" ]; then
            /usr/local/bin/fileicon set "$DMG_FILE" "$ICON_SOURCE"
        fi
    fi
fi

echo "[DMG] Done: dist/$DMG_NAME"
'''
    with open('pack_dmg.sh', 'w') as f:
        f.writelines(final_lines)
        f.write(new_tail)
    print("Fixed pack_dmg.sh")
