# -*- coding: utf-8 -*-
import json
import os
from anthropic import Anthropic

def run_audit(profile_file, output_file, result_label):
    if not os.path.exists(profile_file) or not os.path.exists(output_file):
        print(f"Skipping {result_label}: Files not found.")
        return

    with open(profile_file, 'r', encoding='utf-8-sig') as f:
        profile = json.load(f)
    with open(output_file, 'r', encoding='utf-8-sig') as f:
        output = json.load(f)

    client = Anthropic(api_key="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") # Using your established token logic

    prompt = f"Audit this career engine output for a {profile.get('role', 'User')}.\nProfile: {profile}\nOutput: {output}\nVerify if the 90% fidelity rule is met."
    
    # AI logic to audit the 'Optimum Logic' and 'Sequential Flow'
    response = client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    
    with open(f"audit_{result_label}.json", "w", encoding="utf-8") as f:
        json.dump({"audit": response.content[0].text}, f, indent=4)
    print(f"✅ Audit for {result_label} complete.")

# Run for both DJ and Wife
run_audit('profile_dj.json', 'output_dj.json', 'DJ_IT_Audit')
run_audit('profile_wife.json', 'output_wife.json', 'Wife_PostDoc')
