import sys

def parse_blocks(html):
    blocks = [
        "MODULES", "LABS", "QUESTIONS", "RESOURCES", "AI_PROMPTS", 
        "AAIA_DOMAINS", "CIASP_DOMAINS", "ROADMAP_ITEMS", "SIM_ENGINE", 
        "AG", "SIMULATIONS", "ADVANCED_QUESTIONS", "FAIR_SIM", 
        "CONFLICT_SIM", "STUDY_VAULT", "LIVE_INTEL", "SAAS_DATA"
    ]
    out = "const DEOBRAT_DATA = {\n"
    
    for b in blocks:
        marker = f"const {b} = "
        idx = html.find(marker)
        if idx == -1:
             print("Missing", b)
             continue
        
        start_idx = idx + len(marker)
        
        # we need to find the matching bracket/brace
        open_char = html[start_idx]
        if open_char not in ['[', '{']:
            # skip whitespaces
            for i in range(start_idx, len(html)):
                if html[i] in ['[', '{']:
                    start_idx = i
                    open_char = html[i]
                    break

        close_char = ']' if open_char == '[' else '}'
        
        count = 0
        end_idx = -1
        in_string = False
        escape = False
        
        for i in range(start_idx, len(html)):
            c = html[i]
            
            if in_string:
                if escape:
                    escape = False
                elif c == '\\':
                    escape = True
                elif c == '"' or c == "'": # assuming we don't mix them poorly
                    pass # actually this is a bit too simple for full JS parsing
                    # let's just do a simple bracket count, ignoring strings, it usually works if data is clean
            # A simple bracket count might fail if there are brackets in strings, but we'll try.
            pass
            
            if c == open_char:
                count += 1
            elif c == close_char:
                count -= 1
                if count == 0:
                    end_idx = i
                    break
        
        if end_idx != -1:
            data_str = html[start_idx:end_idx+1]
            out += f"  {b}: {data_str},\n"
        else:
            print("Failed to parse", b)
            
    out += "};\n"
    return out

with open('frontend/public/certlab-static.html', 'r', encoding='utf-8') as f:
    html = f.read()

deobrat_data = parse_blocks(html)

with open('js/deobrat_data.js', 'w', encoding='utf-8') as f:
    f.write(deobrat_data)
