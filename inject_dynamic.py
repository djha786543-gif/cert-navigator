import re

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

with open('dynamic_data.html', 'r', encoding='utf-8') as f:
    dynamic_code = f.read()

# Remove the broken JS files
html = html.replace('<script src="js/deobrat_data.js"></script>\n', '')
html = html.replace('<script src="js/pooja_data.js"></script>\n', '')

# Insert the dynamic definition just before <script src="js/profiles.js">
html = html.replace('<script src="js/profiles.js"></script>', dynamic_code + '\n<script src="js/profiles.js"></script>')

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)
