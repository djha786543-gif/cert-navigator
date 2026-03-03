import re
import os

files = ['js/deobrat_data.js', 'js/pooja_data.js']

for fp in files:
    with open(fp, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Clean up invalid script tags and nested const declarations
    # The error is that some values captured included `</script> <script> const FOO = ` inside the value,
    # and then the value ended with `];` or `};`.

    def replacer(match):
        val = match.group(1)
        # remove any script tags or variable declarations inside the matched block
        # Actually, let's just do a clean pass: 
        # For the keys in DEOBRAT_DATA, their values shouldn't contain script tags.
        val = re.sub(r'</script>\s*<script[^>]*>', '', val)
        val = re.sub(r'const\s+[A-Z_]+\s*=\s*', '', val)
        val = re.sub(r';\s*$', '', val)
        return val

    # Since it's malformed JS now, let's do somewhat manual fix:
    # We'll just replace literal bad strings.
    
    # Strip </script>, <script> entirely
    content = content.replace('</script>', '')
    content = content.replace('<script>', '')
    # Strip "const " from inside
    content = re.sub(r'const\s+[A-Z_]+\s*=\s*(?=\{)', '', content)
    content = re.sub(r'const\s+[A-Z_]+\s*=\s*(?=\[)', '', content)
    content = re.sub(r'let\s+state\s*=', '', content)
    content = re.sub(r'function\s+[a-zA-Z_]+\s*\(.*?\)\s*\{', '', content)

    # Let's just fix the trailing semicolons in the object literal
    content = re.sub(r'];\s*(?=\w+:)', '],', content)
    content = re.sub(r'};\s*(?=\w+:)', '},', content)
    content = re.sub(r'];\s*(?=})', ']', content)
    content = re.sub(r'};\s*(?=})', '}', content)

    # Also fix ROADMAP_ITEMS block in deobrat and pooja
    content = re.sub(r'ROADMAP_ITEMS.*?(?=\s*SIM_ENGINE)', 'ROADMAP_ITEMS: /* fixed manually */ [],\n  ', content, flags=re.DOTALL)

    with open(fp, 'w', encoding='utf-8') as f:
        f.write(content)
