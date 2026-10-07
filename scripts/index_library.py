#!/usr/bin/env python3
"""Index local reference libraries without copying or altering their contents."""
import argparse
import hashlib
import json
from pathlib import Path

SUPPORTED = {'.pdf', '.docx', '.pptx', '.mp4', '.mov', '.mkv', '.webm', '.srt', '.vtt'}

def build_index(roots):
    records, seen = [], {}
    for label, root in roots:
        root = root.expanduser().resolve(strict=True)
        if not root.is_dir():
            raise ValueError(f'Not a directory: {root}')
        for path in sorted(root.rglob('*')):
            rel = path.relative_to(root)
            if path.is_symlink() or any(p.startswith('.') for p in rel.parts):
                continue
            if not path.is_file() or path.suffix.lower() not in SUPPORTED:
                continue
            if not path.resolve().is_relative_to(root):
                continue
            digest = hashlib.sha256()
            with path.open('rb') as stream:
                for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
                    digest.update(chunk)
            key = digest.hexdigest()
            record = {
                'id': f'F{len(records)+1:04d}', 'library': label,
                'relative_path': str(rel), 'bytes': path.stat().st_size,
                'sha256': key, 'duplicate_of': seen.get(key),
                'read_status': 'indexed_only',
                'award_status': 'unverified',
            }
            seen.setdefault(key, record['id'])
            records.append(record)
    return records

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', action='append', required=True, metavar='LABEL=PATH')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    roots, labels = [], set()
    for item in args.root:
        label, sep, value = item.partition('=')
        if not sep or not label or not value or label in labels:
            parser.error('--root needs unique non-empty LABEL=PATH values')
        labels.add(label)
        roots.append((label, Path(value)))
    if args.output.exists():
        parser.error('output exists; choose a new filename to preserve earlier review records')
    rows = build_index(roots)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump({'schema_version': 1, 'records': rows}, stream, ensure_ascii=False, indent=2)
    print(f'{len(rows)} files; {sum(r["duplicate_of"] is None for r in rows)} unique contents')

if __name__ == '__main__':
    main()
