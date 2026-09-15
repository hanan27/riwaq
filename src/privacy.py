"""Conservative format detection, not identity verification. All test values are synthetic."""
import re
import unicodedata

# Broad formats intentionally mask even invalid checksums: privacy must not rely on validity.
SEPARATOR = r'[\s\-]*'
PATTERNS = [
 ('SA_IBAN', re.compile(r'(?<![A-Za-z0-9])SA' + (SEPARATOR+r'[0-9]')*22 + r'(?![0-9])', re.I)),
 ('SA_PHONE', re.compile(r'(?<![0-9])(?:\+?966|00966)' + SEPARATOR + r'[15]' + (SEPARATOR+r'[0-9]')*8 + r'(?![0-9])')),
 ('SA_PHONE', re.compile(r'(?<![0-9])0'+SEPARATOR+r'[15]'+(SEPARATOR+r'[0-9]')*8+r'(?![0-9])')),
 ('SA_ID', re.compile(r'(?<![0-9])[12]'+(SEPARATOR+r'[0-9]')*9+r'(?![0-9])')),
 ('EMAIL', re.compile(r'(?<![\w.+-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}(?![\w.-])')),
]

def pii_spans(text):
    if not isinstance(text, str): return []
    # Preserve an index map while folding Arabic digits and deleting zero-width controls.
    folded, positions = [], []
    for i,c in enumerate(text):
        if unicodedata.category(c) in ('Cf','Mn'): continue
        for char in unicodedata.normalize('NFKC',c):
            try: char=str(unicodedata.decimal(char))
            except (ValueError,TypeError): pass
            folded.append(char); positions.append(i)
    normalized=''.join(folded)
    found=[]
    for kind,pattern in PATTERNS:
        for match in pattern.finditer(normalized):
            start,end=positions[match.start()],positions[match.end()-1]+1
            if any(start<b and end>a for a,b,_ in found): continue
            found.append((start,end,kind))
    return sorted(found)

def mask_pii(text):
    if not isinstance(text,str): return text
    for start,end,kind in reversed(pii_spans(text)):
        text=text[:start]+'[MASKED_'+kind+']'+text[end:]
    return text

def mask_data(value):
    if isinstance(value,str): return mask_pii(value)
    if isinstance(value,list): return [mask_data(item) for item in value]
    if isinstance(value,tuple): return tuple(mask_data(item) for item in value)
    if isinstance(value,dict): return {mask_pii(k):mask_data(v) for k,v in value.items()}
    return value
