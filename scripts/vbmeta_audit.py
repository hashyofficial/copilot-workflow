#!/usr/bin/env python3
"""Read-only audit of AVB0 headers and descriptor graph for the yunluo ROM.

This checks the structure of vbmeta data, not the RSA signature or device bootability.
"""
import hashlib
import json
from pathlib import Path, PurePosixPath
import struct
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'reports-avb'
VER = 'V14.0.4.0.TLYMIXM'
NAME = 'yunluo_global_images_V14.0.4.0.TLYMIXM_20231207.0000.00_13.0_global_4003dcb1a4.tgz'
MD5 = '4003dcb1a4db404e2768801fdb429c4a'
FILES = {'vbmeta.img': 8192, 'vbmeta_system.img': 4096, 'vbmeta_vendor.img': 4096}
TAGS = {0:'property',1:'hashtree',2:'hash',3:'kernel_cmdline',4:'chain_partition',5:'bootconfig'}
ALG = {0:'NONE',1:'SHA256_RSA2048',2:'SHA256_RSA4096',3:'SHA256_RSA8192',4:'SHA512_RSA2048',5:'SHA512_RSA4096',6:'SHA512_RSA8192'}
HEADER = '>4sIIQQIQQQQQQQQQQQII48s80s'

def md5_file(file):
    h=hashlib.md5()
    with file.open('rb') as stream:
        for chunk in iter(lambda: stream.read(8*1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()

def unpack(data, offset, fmt):
    return struct.unpack_from('>'+fmt,data,offset)

def to_str(data):
    return data.split(b'\0', 1)[0].decode('utf-8','replace')

def descriptor(tag, body):
    out={'type':TAGS.get(tag, 'unknown'),'tag':tag,'bytes':len(body)}
    if tag == 4:
        if len(body)<76:raise ValueError('Short chain descriptor')
        roll,n,k,flags=unpack(body,0,'IIII')
        if 76+n+k>len(body):raise ValueError('Chained key out of bounds')
        out.update(partition=body[76:76+n].decode('utf8','replace'),rollback_index_location=roll,
                   flags=flags, public_key_sha256=hashlib.sha256(body[76+n:76+n+k]).hexdigest())
    elif tag == 2:
        if len(body)<116:raise ValueError('Short hash descriptor')
        n,salt,digest,flags=unpack(body,40,'IIII')
        if 116+n+salt+digest>len(body):raise ValueError('Hash descriptor out of bounds')
        out.update(partition=body[116:116+n].decode('utf8','replace'),
                   image_size=unpack(body,0,'Q')[0],hash_algorithm=to_str(body[8:40]),flags=flags)
    elif tag == 1:
        if len(body)<164:raise ValueError('Short hashtree descriptor')
        n,salt,digest,flags=unpack(body,88,'IIII')
        if 164+n+salt+digest>len(body):raise ValueError('Hashtree descriptor out of bounds')
        out.update(partition=body[164:164+n].decode('utf8','replace'),
                   image_size=unpack(body,4,'Q')[0],tree_offset=unpack(body,12,'Q')[0],
                   tree_size=unpack(body,20,'Q')[0],hash_algorithm=to_str(body[56:88]),flags=flags)
    return out

def audit_one(filename, blob):
    if len(blob)!=FILES[filename]:raise ValueError('Bad image size: '+filename)
    h=struct.unpack_from(HEADER,blob,0)
    if h[0]!=b'AVB0':raise ValueError('Bad AVB0 magic in '+filename)
    auth,aux=h[3],h[4]
    if 256+auth+aux>len(blob) or auth%64 or aux%64:raise ValueError('Bad AVB0 block sizes')
    puboff,pubsize=h[10],h[11]
    desc_off,desc_len=h[14],h[15]
    if puboff+pubsize>aux or desc_off+desc_len>aux:raise ValueError('AVB0 aux bounds exceeded')
    auxstart=256+auth
    desc=blob[auxstart+desc_off:auxstart+desc_off+desc_len]
    items=[];offset=0
    while offset<len(desc):
        if offset+16>len(desc):raise ValueError('Truncated descriptor')
        tag,size=unpack(desc,offset,'QQ')
        if size%8 or offset+16+size>len(desc):raise ValueError('Invalid descriptor length')
        items.append(descriptor(tag,desc[offset+16:offset+16+size]))
        offset+=16+size
    flags=h[17]
    return {'image':filename,'bytes':len(blob),'sha256':hashlib.sha256(blob).hexdigest(),
            'required_version':str(h[1])+'.'+str(h[2]),'algorithm':ALG.get(h[5],str(h[5])),
            'flags':flags,'hashtree_disabled':bool(flags&1),'verification_disabled':bool(flags&2),
            'rollback_index':h[16],'rollback_index_location':h[18],
            'release_string':to_str(h[19]),'public_key_sha256':hashlib.sha256(blob[auxstart+puboff:auxstart+puboff+pubsize]).hexdigest() if pubsize else None,
            'descriptors':items}

def extract_sources(archive):
    found={}
    with tarfile.open(archive,'r:gz') as stream:
        for info in stream:
            name=PurePosixPath(info.name)
            if name.is_absolute() or '..' in name.parts:raise ValueError('Unsafe path in archive')
            if not info.isfile() or name.parent.name!='images' or name.name not in FILES:continue
            if name.name in found or info.size!=FILES[name.name]:raise ValueError('Invalid vbmeta member '+info.name)
            found[name.name]=stream.extractfile(info).read()
            if len(found)==len(FILES):break
    if set(found)!=set(FILES):raise ValueError('Missing vbmeta members '+str(set(FILES)-set(found)))
    return found

def summary(items):
    lines=['# Original yunluo Global MIUI 14 AVB structural audit','',
           'Firmware: '+VER,'',
           'The ROM checksum was validated. This is read-only structural inspection; it does NOT verify cryptographic AVB signatures or device bootability.','',
           '| Image | Bytes | Flags | Algorithm | Rollback index |',
           '|---|---:|---:|---|---:|']
    for item in items:
        lines.append('| {image} | {bytes} | {flags} | {algorithm} | {rollback_index} |'.format(**item))
    for item in items:
        lines+=['','## '+item['image'],'','Image SHA256: '+item['sha256']]
        for d in item['descriptors']:
            lines.append('- '+d['type']+': '+d.get('partition','(no partition name)')+', flags: '+str(d.get('flags','n/a')))
    lines+=['','## Cautions',
        '- Header flags only apply to a top-level vbmeta per AOSP AVB0 specification; chained image flags must be zero.',
        '- Altering an AVB header invalidates its original signature. This audit creates NO modified vbmeta images.',
        '- Verify bootloader unlock, chain relationships and original firmware recovery method before any flash.','']
    return '\n'.join(lines)

def main():
    REPORT.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='yunluo-avb-') as tmp:
        archive=Path(tmp)/NAME
        subprocess.run(['python3',str(ROOT/'scripts/download.py'),'--output',str(archive),
                        '--report',str(REPORT/'download-sources.json')],check=True)
        observed=md5_file(archive)
        (REPORT/'firmware-checksum.txt').write_text('Expected MD5: '+MD5+'\nActual MD5: '+observed+'\n')
        if observed!=MD5:raise ValueError('Firmware MD5 does not match')
        data=extract_sources(archive)
        results=[audit_one(name,data[name]) for name in FILES]
    (REPORT/'vbmeta-descriptors.json').write_text(json.dumps(results,indent=2)+'\n')
    report=summary(results)
    (REPORT/'vbmeta-report.md').write_text(report)
    print(report,flush=True)

if __name__=='__main__':
    main()
