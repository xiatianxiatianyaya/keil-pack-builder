"""Offline regression: python -m unittest discover -s scripts -p test_pack_tool.py -v"""
import argparse
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

spec = importlib.util.spec_from_file_location('pack_tool', Path(__file__).with_name('pack_tool.py'))
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


class PackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'src'
        self.source.mkdir()
        self.pdsc = 'ExampleVendor.Demo.pdsc'
        self.xml = b'''<?xml version="1.0"?>
<package schemaVersion="1.7.2">
<vendor>ExampleVendor</vendor><name>Demo</name><description>Offline packaging fixture</description>
<url>https://example.org/packs/</url><license>LICENSE.txt</license>
<releases><release version="0.0.1" date="2026-10-30">Offline fixture</release></releases>
</package>'''
        (self.source / self.pdsc).write_bytes(self.xml)
        (self.source / 'LICENSE.txt').write_text('Synthetic test fixture only.', encoding='utf-8')
        self.manifest = self.source / 'pack-files.json'
        self.write_manifest([self.pdsc, 'LICENSE.txt'])

    def write_manifest(self, names):
        self.manifest.write_text(json.dumps({'pdsc': self.pdsc, 'files': names}), encoding='utf-8')

    def args(self, **changes):
        a = argparse.Namespace(command='build', path=str(self.manifest), out=str(self.root / 'out'),
                               draft=True, packchk=None, xsd=None, include=[])
        for k, v in changes.items():
            setattr(a, k, v)
        return a

    def test_deterministic_archive_and_manifest_only(self):
        (self.source / 'private.bin').write_bytes(b'not for distribution')
        first = tool.process(self.args())
        second = tool.process(self.args(out=str(self.root / 'out2')))
        self.assertFalse(first['errors'])
        self.assertEqual(first['pack_sha256'], second['pack_sha256'])
        with zipfile.ZipFile(first['output']) as z:
            self.assertEqual(set(z.namelist()), {self.pdsc, 'LICENSE.txt'})
            self.assertEqual(z.read(self.pdsc), self.xml)
        self.assertEqual(first['official']['packchk']['status'], 'not_run')
        self.assertEqual(first['verification']['hardware'], 'not_run')

    def test_existing_output_preserved(self):
        out = self.root / 'out'
        out.mkdir()
        (out / 'keep.txt').write_text('keep')
        with self.assertRaises(FileExistsError):
            tool.process(self.args())
        self.assertEqual((out / 'keep.txt').read_text(), 'keep')

    def test_normal_build_requires_official_validation(self):
        result = tool.process(self.args(draft=False))
        self.assertTrue(result['errors'])
        self.assertFalse((self.root / 'out').exists())

    def test_missing_reference_stops_build(self):
        (self.source / self.pdsc).write_bytes(self.xml.replace(b'</package>', b'<devices><family><debug svd="absent.svd"/></family></devices></package>'))
        self.assertTrue(tool.process(self.args())['errors'])
        self.assertFalse((self.root / 'out').exists())

    def test_bad_paths(self):
        for path in ('../secret', '/tmp/secret', 'C:/secret', 'file:stream', 'a//b', 'a/./b', 'a\\b', 'a/..', 'a.'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                tool.safe_name(path)

    def test_case_mismatch_rejected_on_windows(self):
        self.write_manifest([self.pdsc, 'license.txt'])
        with self.assertRaises(ValueError):
            tool.snapshot(self.manifest)

    def test_duplicate_entries_rejected(self):
        self.write_manifest([self.pdsc, 'LICENSE.txt', 'LICENSE.txt'])
        with self.assertRaises(ValueError):
            tool.snapshot(self.manifest)

    def test_duplicate_json_keys(self):
        self.manifest.write_text('{"pdsc":"a","pdsc":"b","files":[]}')
        with self.assertRaises(ValueError):
            tool.snapshot(self.manifest)

    def test_entity_rejected(self):
        raw = '<!DOCTYPE package [<!ENTITY a "boom">]><package>&a;</package>'
        for encoding in ('utf-8', 'utf-16'):
            with self.subTest(encoding=encoding), self.assertRaises(ValueError):
                tool.parse_xml(raw.encode(encoding))

    def test_nested_pdsc_in_archive(self):
        p = self.root / 'wrapped.pack'
        with zipfile.ZipFile(p, 'w') as z:
            z.writestr('wrapper/' + self.pdsc, self.xml)
        self.assertTrue(tool.inspect(p)['errors'])

    def test_unsafe_archive_not_extracted(self):
        p = self.root / 'unsafe.pack'
        with zipfile.ZipFile(p, 'w') as z:
            z.writestr(self.pdsc, self.xml)
            z.writestr('../escaped.txt', 'escape')
        self.assertTrue(tool.inspect(p)['errors'])
        self.assertFalse((self.root / 'escaped.txt').exists())

    def test_unfilled_template_not_accepted(self):
        (self.source / self.pdsc).write_bytes(self.xml.replace(b'Offline fixture', b'REPLACE_NOTES'))
        self.assertTrue(tool.process(self.args())['errors'])


if __name__ == '__main__':
    unittest.main()
