"""Explicit-file CMSIS pack helper. No installation or hardware access. Python 3.10+."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile


def sha(data):
    return hashlib.sha256(data).hexdigest()


def safe_name(name):
    if not isinstance(name, str) or not name or '\\' in name or ':' in name:
        raise ValueError(f'Unsafe relative path: {name!r}')
    p = PurePosixPath(name)
    if p.is_absolute() or any(x in ('', '.', '..') or x.endswith((' ', '.')) for x in name.split('/')):
        raise ValueError(f'Unsafe relative path: {name!r}')
    if any(ord(c) < 32 for c in name) or any(c in name for c in '*?<>|"'):
        raise ValueError(f'Unsupported path: {name!r}')
    return name


def parse_xml(data):
    # Reject DTD/entities, including UTF-16 encoded XML, before ElementTree parsing.
    if b'<!DOCTYPE' in data.replace(b'\x00', b'').upper() or b'<!ENTITY' in data.replace(b'\x00', b'').upper():
        raise ValueError('DTD/entities are not supported')
    return ET.fromstring(data)


def unique_json(pairs):
    obj = {}
    for k, v in pairs:
        if k in obj:
            raise ValueError(f'Duplicate JSON key: {k}')
        obj[k] = v
    return obj


def snapshot(manifest):
    root = manifest.resolve().parent
    spec = json.loads(manifest.read_text(encoding='utf-8-sig'), object_pairs_hook=unique_json)
    if not isinstance(spec, dict) or set(spec) != {'pdsc', 'files'}:
        raise ValueError('Manifest must contain only pdsc and files')
    pdsc = safe_name(spec['pdsc'])
    names = spec['files']
    if not isinstance(names, list) or not names:
        raise ValueError('files must be a nonempty list')
    seen, data = set(), {}
    for name in names:
        safe_name(name)
        if name.casefold() in seen:
            raise ValueError(f'Duplicate/case-colliding entry: {name}')
        seen.add(name.casefold())
        cursor = root
        for part in name.split('/'):
            if part not in {x.name for x in cursor.iterdir()}:
                raise ValueError(f'Missing or case-mismatched path: {name}')
            cursor = cursor / part
            if cursor.is_symlink():
                raise ValueError(f'Symlink not allowed: {name}')
            if not cursor.resolve().is_relative_to(root):
                raise ValueError(f'Path leaves source root: {name}')
        if not cursor.is_file():
            raise ValueError(f'Explicit files only: {name}')
        data[name] = cursor.read_bytes()
    if '/' in pdsc or pdsc not in data or not pdsc.endswith('.pdsc'):
        raise ValueError('pdsc must name an included root-level .pdsc file')
    if [n for n in data if n.lower().endswith('.pdsc')] != [pdsc]:
        raise ValueError('Exactly one PDSC is allowed')
    return pdsc, data


def basic_check(pdsc, data):
    result = {'errors': [], 'warnings': [], 'files': {n: sha(b) for n, b in sorted(data.items())}}
    errors = result['errors']
    doc = parse_xml(data[pdsc])
    if doc.tag != 'package':
        raise ValueError('Expected non-namespaced package root')
    vendor, name = doc.findtext('vendor', '').strip(), doc.findtext('name', '').strip()
    for label, value in [('vendor', vendor), ('name', name)]:
        if not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]*', value):
            errors.append(f'Missing/unsupported {label}: {value!r}')
    if pdsc != f'{vendor}.{name}.pdsc':
        errors.append('PDSC filename does not match vendor.name.pdsc')
    for key in ('description', 'url'):
        if not doc.findtext(key, '').strip():
            errors.append(f'Missing {key}')
    releases = doc.findall('releases/release')
    version = releases[0].get('version', '') if releases else ''
    if not re.fullmatch(r'\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?', version):
        errors.append('First release must have supported numeric three-part version')
    result['pack_name'] = f'{vendor}.{name}.{version}.pack'
    if b'REPLACE_' in data[pdsc]:
        errors.append('Unfilled template markers in PDSC')
    refs = []
    for el in doc.iter():
        for tag, attr in [('algorithm', 'name'), ('debug', 'svd'), ('compile', 'header'), ('file', 'name'), ('license', 'name')]:
            if el.tag == tag and el.get(attr):
                refs.append((el.get(attr), el.tag == 'file' and el.get('category') == 'include'))
        if el.tag in ('license', 'readme') and el.text and el.text.strip():
            refs.append((el.text.strip(), False))
    for ref, directory in refs:
        if ref.startswith(('https://', 'http://')):
            result['warnings'].append(f'External reference not fetched: {ref}')
            continue
        try:
            safe_name(ref.rstrip('/') if directory else ref)
            if directory:
                if not any(n.startswith(ref.rstrip('/') + '/') for n in data):
                    errors.append(f'Include directory has no manifest files: {ref}')
            elif ref not in data:
                errors.append(f'Referenced file absent from manifest or wrong case: {ref}')
        except ValueError as e:
            errors.append(str(e))
    result['warnings'].append('Basic check covers common references only; inheritance, complex conditions, FLM and hardware semantics are not validated.')
    return result


def official_checks(stage, pdsc, args):
    result = {'xsd': {'status': 'not_run'}, 'packchk': {'status': 'not_run'}}
    if args.xsd:
        from lxml import etree
        schema_path = Path(args.xsd).resolve(strict=True)
        parser = etree.XMLParser(resolve_entities=False, no_network=True)
        try:
            schema = etree.XMLSchema(etree.parse(str(schema_path), parser))
            passed = schema.validate(etree.parse(str(stage / pdsc), parser))
            log = str(schema.error_log)
        except etree.LxmlError as e:
            passed, log = False, str(e)
        result['xsd'] = {'status': 'passed' if passed else 'failed', 'path': str(schema_path),
                         'sha256': sha(schema_path.read_bytes()), 'log': log}
    if args.packchk:
        exe = Path(args.packchk).resolve(strict=True)
        cmd = [str(exe), str(stage / pdsc)]
        deps = []
        for dep in args.include:
            p = Path(dep).resolve(strict=True)
            deps.append({'path': str(p), 'sha256': sha(p.read_bytes())})
            cmd += ['-i', str(p)]
        run = subprocess.run(cmd, cwd=stage, capture_output=True, text=True, errors='replace', timeout=120)
        result['packchk'] = {'status': 'passed' if run.returncode == 0 else 'failed',
                             'path': str(exe), 'sha256': sha(exe.read_bytes()), 'command': cmd,
                             'dependencies': deps, 'returncode': run.returncode,
                             'stdout': run.stdout, 'stderr': run.stderr}
    return result


def create_zip(path, data):
    with zipfile.ZipFile(path, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name, blob in sorted(data.items()):
            info = zipfile.ZipInfo(name, date_time=(2000, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, blob)


def inspect(path):
    errors, entries, seen, roots = [], [], set(), []
    with zipfile.ZipFile(path) as z:
        for item in z.infolist():
            n = item.filename
            try:
                safe_name(n.rstrip('/') if item.is_dir() else n)
            except ValueError as e:
                errors.append(str(e))
            normalized = n.rstrip('/').casefold()
            if normalized in seen:
                errors.append(f'Duplicate/case collision: {n}')
            seen.add(normalized)
            if stat.S_ISLNK(item.external_attr >> 16):
                errors.append(f'Symlink entry: {n}')
            entries.append({'path': n, 'bytes': item.file_size})
            if n.lower().endswith('.pdsc'):
                roots.append(n)
        if len(roots) != 1 or '/' in roots[0] or '\\' in roots[0]:
            errors.append('Expected exactly one PDSC at ZIP root; possible extra wrapper directory')
        metadata = {}
        if len(roots) == 1:
            if z.getinfo(roots[0]).file_size > 8 * 1024 * 1024:
                errors.append('PDSC exceeds inspection size limit')
            else:
                doc = parse_xml(z.read(roots[0]))
                metadata = {k: doc.findtext(k) for k in ('vendor', 'name', 'description')}
        return {'mode': 'inspect_only', 'errors': errors, 'metadata': metadata, 'entries': entries,
                'note': 'No extraction, installation, full reference or hardware validation performed.'}


def process(args):
    if args.command == 'inspect':
        return inspect(args.path)
    pdsc, data = snapshot(Path(args.path))
    result = basic_check(pdsc, data)
    result['source_manifest'] = str(Path(args.path).resolve())
    result['source_manifest_sha256'] = sha(Path(args.path).read_bytes())
    result['verified_at_utc'] = datetime.now(timezone.utc).isoformat()
    result['verification'] = {'svdconv': 'not_run', 'keil_install': 'not_run', 'build_example': 'not_run', 'hardware': 'not_run'}
    if result['errors']:
        return result
    with tempfile.TemporaryDirectory(prefix='cmsis-pack-') as tmp:
        stage = Path(tmp)
        for name, blob in data.items():
            p = stage / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(blob)
        result['official'] = official_checks(stage, pdsc, args)
        if any(v['status'] == 'failed' for v in result['official'].values()):
            result['errors'].append('Official validation failed; see logs')
        if args.command == 'build':
            result['draft'] = args.draft
            if not args.draft and any(v['status'] != 'passed' for v in result['official'].values()):
                result['errors'].append('Normal build requires both --packchk and --xsd; use --draft only for unverified review artifacts')
            if not result['errors']:
                out = Path(args.out).resolve()
                # Exclusive directory creation: never overwrite an existing delivery.
                out.mkdir(parents=True, exist_ok=False)
                dest = out / result['pack_name']
                create_zip(dest, data)
                result['output'] = str(dest)
                result['pack_sha256'] = sha(dest.read_bytes())
                (out / 'validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
                (out / 'SHA256SUMS.txt').write_text(''.join(f'{h}  {n}\n' for n, h in result['files'].items()), encoding='utf-8')
                if args.draft:
                    (out / 'DRAFT_NOT_RELEASE_VALIDATED.txt').write_text('Review artifact only. See validation.json for unperformed validation.\n', encoding='utf-8')
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    subs = ap.add_subparsers(dest='command', required=True)
    for command in ('inspect', 'check', 'build'):
        sub = subs.add_parser(command)
        sub.add_argument('path', help='PACK archive for inspect; pack-files.json for check/build')
        if command != 'inspect':
            sub.add_argument('--packchk', help='Explicit trusted local executable path')
            sub.add_argument('--xsd', help='Local PACK.xsd; requires lxml')
            sub.add_argument('-i', '--include', action='append', default=[])
        if command == 'build':
            sub.add_argument('--out', required=True)
            sub.add_argument('--draft', action='store_true')
    args = ap.parse_args(argv)
    try:
        result = process(args)
    except (ValueError, OSError, ET.ParseError, zipfile.BadZipFile, ImportError, subprocess.SubprocessError) as e:
        result = {'errors': [f'{type(e).__name__}: {e}']}
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 1 if result.get('errors') else 0


if __name__ == '__main__':
    sys.exit(main())
