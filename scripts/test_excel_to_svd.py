"""Offline checks of register semantics and generated SVD; no hardware access."""
import copy
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

from excel_to_svd import convert, describe, integer, normalize, read_workbook, svd

TEMPLATE = Path(__file__).resolve().parents[1] / 'assets' / 'registers-template.xlsx'


class ConversionTests(unittest.TestCase):
    def setUp(self):
        self.rows, self.digest = read_workbook(TEMPLATE)

    def test_template_semantics_and_svd(self):
        m = normalize(self.rows)
        root = ET.fromstring(svd(m))
        self.assertEqual(root.findtext('cpu/name'), 'CM0')
        regs = root.findall('.//register')
        self.assertEqual(len(regs), 2)
        self.assertEqual(regs[1].findtext('addressOffset'), '0x4')
        self.assertEqual(regs[1].findtext('fields/field/modifiedWriteValues'), 'oneToClear')
        self.assertEqual(len(root.findall('.//enumeratedValue')), 6)
        self.assertIn('0x40000004', describe(m))
        self.assertEqual(m['peripherals'][0]['registers'][0]['source'], 'Registers!2')

    def test_missing_reset_not_guessed(self):
        self.rows['Registers'][0]['reset_value'] = None
        with self.assertRaisesRegex(ValueError, 'expected nonnegative'):
            normalize(self.rows)

    def test_reset_mask(self):
        self.rows['Registers'][0].update(reset_value='0x80',reset_mask='0x7f')
        with self.assertRaisesRegex(ValueError, 'reset overflow'):
            normalize(self.rows)

    def test_register_overlap(self):
        self.rows['Registers'][1]['offset'] = 0
        with self.assertRaisesRegex(ValueError, 'address overlap'):
            normalize(self.rows)

    def test_field_overlap(self):
        self.rows['Fields'][1]['lsb'] = 0
        with self.assertRaisesRegex(ValueError, 'overlapping fields'):
            normalize(self.rows)

    def test_field_overflow(self):
        self.rows['Fields'][0]['width'] = 33
        with self.assertRaisesRegex(ValueError, 'field out'):
            normalize(self.rows)

    def test_enum_overflow(self):
        self.rows['Enums'][0]['value'] = 2
        with self.assertRaisesRegex(ValueError, 'enum overflow'):
            normalize(self.rows)

    def test_orphan_reference(self):
        self.rows['Fields'][0]['register'] = 'UNKNOWN'
        with self.assertRaisesRegex(ValueError, 'orphan'):
            normalize(self.rows)

    def test_w1c_not_lost(self):
        self.rows['Registers'][0]['access'] = 'W1C'
        with self.assertRaisesRegex(ValueError, 'oneToClear'):
            normalize(self.rows)

    def test_side_effect_conflict(self):
        self.rows['Fields'][2]['access'] = 'RO'
        with self.assertRaisesRegex(ValueError, 'conflicts with access'):
            normalize(self.rows)

    def test_read_action_and_xml_escape(self):
        self.rows['Fields'][0].update(read_action='clear',description='A & B < C | D')
        root = ET.fromstring(svd(normalize(self.rows)))
        self.assertEqual(root.findtext('.//field/readAction'), 'clear')
        self.assertEqual(root.findtext('.//field/description'), 'A & B < C | D')
        self.assertIn('A &amp; B &lt; C &#124; D', describe(normalize(self.rows)))

    def test_exact_numbers_only(self):
        for v in (True, 2.5, -1, 2**53, '1<<2', 'TBD'):
            with self.subTest(v=v), self.assertRaises(ValueError):
                integer(v, 'test')
        self.assertEqual(integer('0xFFFFFFFFFFFFFFFF','test'),2**64-1)

    def test_duplicate_irq(self):
        row=copy.deepcopy(self.rows['Interrupts'][0])
        row['name']='OTHER'
        self.rows['Interrupts'].append(row)
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            normalize(self.rows)

    def test_reports_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'new'
            report=convert(TEMPLATE,out)
            self.assertEqual(report['svdconv']['status'],'not_run')
            self.assertEqual(report['input_sha256'],self.digest)
            self.assertTrue((out/'model.json').is_file())
            with self.assertRaises(FileExistsError):
                convert(TEMPLATE,out)

    def test_missing_tool_retains_report(self):
        with tempfile.TemporaryDirectory() as td:
            report=convert(TEMPLATE,Path(td)/'new',Path(td)/'missing.exe')
            self.assertTrue(report['errors'])
            self.assertTrue((Path(td)/'new/conversion_report.json').is_file())

    def test_formula_rejected(self):
        # Mutate one OOXML cell in a copy; never alter the source template.
        with tempfile.TemporaryDirectory() as td:
            target=Path(td)/'bad.xlsx'
            with zipfile.ZipFile(TEMPLATE) as src, zipfile.ZipFile(target,'w') as dst:
                for info in src.infolist():
                    data=src.read(info.filename)
                    if info.filename=='xl/worksheets/sheet4.xml':
                        root=ET.fromstring(data)
                        ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                        cell=root.find('.//s:c[@r="C2"]',ns)
                        self.assertIsNotNone(cell)
                        cell.clear(); cell.set('r','C2')
                        ET.SubElement(cell,'{'+ns['s']+'}f').text='1+1'
                        data=ET.tostring(root,encoding='utf-8',xml_declaration=True)
                    dst.writestr(info,data)
            with self.assertRaisesRegex(ValueError, 'formulas/errors'):
                read_workbook(target)


if __name__ == '__main__':
    unittest.main()
