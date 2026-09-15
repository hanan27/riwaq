"""Create a self-contained review form. Labels start blank and must be supplied by a human."""
import hashlib
import json
import random
from pathlib import Path
from live import judge_candidates


def build_review(root):
    root=Path(root)
    golden=json.loads((root/'data/golden.json').read_text())
    candidates=judge_candidates(golden)
    random.Random(213).shuffle(candidates)
    payload={'candidates':candidates,'golden':golden,
             'golden_sha256':hashlib.sha256(json.dumps(golden,sort_keys=True).encode()).hexdigest()}
    embedded=json.dumps(payload,ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    output=root/'Riwaq_Human_Review.html'
    output.write_text((root/'templates/review.html').read_text().replace('__PAYLOAD__',embedded))
    return output


def validate_owner_approval(root,path):
    root=Path(root)
    cases=json.loads((root/'data/golden.json').read_text())
    approval=json.loads(Path(path).read_text())
    expected=hashlib.sha256(json.dumps(cases,sort_keys=True).encode()).hexdigest()
    if approval.get('golden_sha256')!=expected or approval.get('case_ids')!=[c['id'] for c in cases]:
        raise ValueError('Approval refers to a different golden set')
    if approval.get('owner_approved') is not True or not approval.get('reviewer') or not approval.get('reviewed_at'):
        raise ValueError('Explicit owner approval, reviewer and date are required')
    return approval
