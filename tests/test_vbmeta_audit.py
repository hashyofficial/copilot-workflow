"""Small offline AVB0 structure tests run before the expensive firmware download."""
import pathlib
import struct
import sys
import unittest

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"scripts"))
from vbmeta_audit import HEADER, audit_one, descriptor

class AvbAuditTests(unittest.TestCase):
    def test_header_size_and_empty_image(self):
        self.assertEqual(struct.calcsize(HEADER), 256)
        fields=[b'AVB0',1,2,0,64,0] + [0]*11 + [0,0,b'avbtool test\0'.ljust(48,b'\0'),bytes(80)]
        self.assertEqual(len(fields),21)
        blob=struct.pack(HEADER,*fields)+bytes(64)+bytes(8192-256-64)
        obj=audit_one('vbmeta.img',blob)
        self.assertEqual(obj['flags'],0)
        self.assertEqual(obj['descriptors'],[])
    def test_chain_descriptor(self):
        name=b'vbmeta_system';key=b'example-key'
        body=struct.pack('>IIII',1,len(name),len(key),0)+bytes(60)+name+key
        body+=bytes((-len(body))%8)
        obj=descriptor(4,body)
        self.assertEqual(obj['partition'],'vbmeta_system')
        self.assertEqual(obj['rollback_index_location'],1)
    def test_hash_descriptor(self):
        name=b'boot';salt=b'1'*8;digest=b'2'*32
        body=struct.pack('>Q',4567)+b'sha256'.ljust(32,b'\0')
        body+=struct.pack('>IIII',len(name),len(salt),len(digest),0)
        body+=bytes(60)+name+salt+digest
        body+=bytes((-len(body))%8)
        obj=descriptor(2,body)
        self.assertEqual(obj['partition'],'boot')
        self.assertEqual(obj['image_size'],4567)
    def test_hashtree_descriptor(self):
        name=b'system';salt=b'1'*8;digest=b'2'*32
        body=struct.pack('>IQQQIIIQQ',1,99999,99999,4096,4096,4096,0,0,0)
        self.assertEqual(len(body),56)
        body+=b'sha256'.ljust(32,b'\0')
        body+=struct.pack('>IIII',len(name),len(salt),len(digest),0)
        body+=bytes(60)+name+salt+digest
        body+=bytes((-len(body))%8)
        obj=descriptor(1,body)
        self.assertEqual(obj['partition'],'system')
        self.assertEqual(obj['tree_size'],4096)
if __name__=='__main__':
    unittest.main()
