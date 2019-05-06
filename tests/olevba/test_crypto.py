"""Check decryption of files from olevba works."""

import sys
import unittest
import os
from os.path import join as pjoin
from subprocess import check_output, CalledProcessError
import json
from collections import OrderedDict

from tests.test_utils import DATA_BASE_DIR, SOURCE_BASE_DIR

from oletools import crypto


@unittest.skipIf(not crypto.check_msoffcrypto(),
                 'Module msoffcrypto not installed for python{}.{}'
                 .format(sys.version_info.major, sys.version_info.minor))
class OlevbaCryptoWriteProtectTest(unittest.TestCase):
    """
    Test documents that are 'write-protected' through encryption.

    Excel has a way to 'write-protect' documents by encrypting them with a
    hard-coded standard password. When looking at the file-structure you see
    an OLE-file with streams `EncryptedPackage`, `StrongEncryptionSpace`, and
    `EncryptionInfo`. Contained in the first is the actual file.  When opening
    such a file in excel, it is decrypted without the user noticing.

    Olevba should detect such encryption, try to decrypt with the standard
    password and look for VBA code in the decrypted file.

    All these tests are skipped if the module `msoffcrypto-tools` is not
    installed.
    """
    def test_autostart(self):
        """Check that autostart macro is found in xls[mb] sample file."""
        # create a PYTHONPATH environment var to prefer our olevba
        env = os.environ
        try:
            env['PYTHONPATH'] = SOURCE_BASE_DIR + os.pathsep + \
                                os.environ['PYTHONPATH']
        except KeyError:
            env['PYTHONPATH'] = SOURCE_BASE_DIR

        for suffix in 'xlsm', 'xlsb':
            example_file = pjoin(
                DATA_BASE_DIR, 'encrypted',
                'autostart-encrypt-standardpassword.' + suffix)
            try:
                output = check_output([sys.executable, '-m', 'olevba', '-j',
                                       example_file],
                                      universal_newlines=True, env=env)
            except CalledProcessError as err:
                print(err.output)
                raise
            data = json.loads(output, object_pairs_hook=OrderedDict)
            # debug: json.dump(data, sys.stdout, indent=4)
            self.assertEqual(len(data), 4)
            self.assertIn('script_name', data[0])
            self.assertIn('version', data[0])
            self.assertEqual(data[0]['type'], 'MetaInformation')
            self.assertIn('return_code', data[-1])
            self.assertEqual(data[-1]['type'], 'MetaInformation')
            self.assertEqual(data[1]['container'], None)
            self.assertEqual(data[1]['file'], example_file)
            self.assertEqual(data[1]['analysis'], None)
            self.assertEqual(data[1]['macros'], [])
            self.assertEqual(data[1]['type'], 'OLE')
            self.assertEqual(data[2]['container'], example_file)
            self.assertNotEqual(data[2]['file'], example_file)
            self.assertEqual(data[2]['type'], "OpenXML")
            analysis = data[2]['analysis']
            self.assertEqual(analysis[0]['type'], 'AutoExec')
            self.assertEqual(analysis[0]['keyword'], 'Auto_Open')
            macros = data[2]['macros']
            self.assertEqual(macros[0]['vba_filename'], 'Modul1.bas')
            self.assertIn('Sub Auto_Open()', macros[0]['code'])


if __name__ == '__main__':
    unittest.main()
