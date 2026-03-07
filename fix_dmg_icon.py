with open('pack_dmg.sh', 'r') as f:
    content = f.read()

# remove the broken part I just accidentally added
content = content.replace('''else
    echo "Warning: Required Python libs (xattr or Foundation) missing, skipping custom DMG icon setting"
fi

