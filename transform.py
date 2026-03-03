import codecs

data = open('js/deobrat_data.js', 'r', encoding='utf-8').read()

# First, fix up Deobrat data to remove CISA
# (In the provided data, we use CIASP for cybersecurity. Let's rename CIASP to AIGP for Deobrat)
deobrat_data = data.replace("CIASP", "AIGP").replace("ciasp", "aigp")
# Make sure CISA is marked completed if it appears
deobrat_data = deobrat_data.replace("CISA", "CISA (Completed)")

# Save Deobrat data
with open('js/deobrat_data.js', 'w', encoding='utf-8') as f:
    f.write(deobrat_data)

# Now transform to Pooja's data
pooja_data = data
replacements = [
    ("DEOBRAT_DATA", "POOJA_DATA"),
    ("AI Audit", "Genomic QC Review"),
    ("AI Auditing", "Genomic QC Review"),
    ("AI governance", "Bioinformatics Governance"),
    ("Risk Assessment", "Quality Assurance Assessment"),
    ("AI Ethics", "Research Ethics"),
    ("AI Controls", "Assay Controls"),
    ("AI Compliance", "Regulatory Compliance"),
    ("AI Risk Management Framework", "GLP/GCP Guidelines"),
    ("NIST AI RMF", "GLP/GCP Guidelines"),
    ("EU AI Act", "FDA 21 CFR Part 11"),
    ("ISO 42001", "ISO 13485"),
    ("NIST CSF 2.0", "CAP/CLIA Standards"),
    ("SOC 2 Type II", "EMA Annex 11"),
    ("SOC 2", "EMA Annex 11"),
    ("CIS Controls", "ICH E6 Good Clinical Practice"),
    ("Cybersecurity", "Lab Systems Compliance"),
    ("Information Security", "Laboratory Operations"),
    ("Security Risk", "Protocol Risk"),
    ("Incident Response", "Protocol Deviation Response"),
    ("AAIA", "MolGen-QC"),
    ("aaia", "molgen-qc"),
    ("CIASP", "Bioinfo-Lead"),
    ("ciasp", "bioinfo-lead"),
    ("CISA", "Removed"),
    ("ITGC", "SOP compliance"),
    ("SOX", "GXP"),
    ("AI system", "CRISPR screen"),
    ("AI models", "RNA-Seq pipelines"),
    ("model drift", "batch effect"),
    ("Model drift", "Batch effect"),
    ("Model validation", "Assay validation"),
    ("bias", "technical variance"),
    ("Bias", "Technical Variance"),
    ("Fairlearn", "FastQC"),
    ("AIF360", "MultiQC"),
    ("Evidently AI", "Seurat"),
    ("Great Expectations", "Bioconductor"),
    ("Python", "R/Bioconductor"),
    ("Data Quality", "Sample Quality"),
    ("data drift", "sample contamination"),
    ("algorithms", "protocols"),
    ("audit", "QC review"), 
    ("Audit", "QC Review"),
    ("Auditor", "Scientist"),
    ("auditor", "scientist"),
    ("Chief AI Officer", "Principal Investigator"),
    ("security", "integrity"),
    ("Ransomware", "Sample Loss Incident"),
    ("phishing", "protocol deviation"),
    ("CIO", "Lab Director")
]

for old, new in replacements:
    pooja_data = pooja_data.replace(old, new)

with open('js/pooja_data.js', 'w', encoding='utf-8') as f:
    f.write(pooja_data)
