"""Record release file hashes after an intentional, reviewed change."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
excluded={'.git','__pycache__','.venv','.runtime','.qa','runs','models'}
files={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
       for p in sorted(ROOT.rglob('*')) if p.is_file()
       and not any(part in excluded for part in p.relative_to(ROOT).parts)
       and p.name not in {'manifest.json','.DS_Store'} and not p.name.startswith('.env')
       and not p.name.endswith(('.tmp','.log','.pyc'))}
(ROOT/'manifest.json').write_text(json.dumps({'version':'0.1.0','algorithm':'sha256','sha256':files},indent=2)+'\n')
print(f'Pinned {len(files)} files. A checksum detects changes; it does not establish factual correctness.')
