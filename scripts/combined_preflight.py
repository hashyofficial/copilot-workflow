#!/usr/bin/env python3
"""One-download, read-only preflight for the first 33 yunluo MIUI 14 APK candidates.

Fails closed on unexpected source, invalid APK manifest, missing targets, and
inconsistent source partition/AVB metadata. Never modifies a firmware image.
"""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import time

from inventory import ROOT, TOOLS, VER, NAME, MD5, sha, fstype, command
from vbmeta_audit import FILES as AVB_FILES, audit_one

REPORT=ROOT/'reports-preflight'
ALLOW=ROOT/'config/first-pass-33.txt'
SCANNED_SUFFIXES={'.xml','.rc','.prop','.conf','.json','.ini','.cfg','.sh'}
CONFIG_LIMIT=2_000_000
SAFE_PARTS={'product_a','system_a','system_ext_a'}
SUPER_RAW_SIZE=9126805504

def emit(name,content):
    REPORT.mkdir(parents=True,exist_ok=True)
    (REPORT/name).write_text(content,encoding='utf8')

def tsv(name,cols,rows):
    emit(name,'\t'.join(cols)+'\n'+'\n'.join('\t'.join(map(str,r)) for r in rows)+'\n')

def permitted():
    targets=[x.strip() for x in ALLOW.read_text().splitlines() if x.strip() and not x.startswith('#')]
    if len(targets)!=33 or len(set(targets))!=33:
        raise RuntimeError('First-pass review must have exactly 33 unique candidates')
    parsed={}
    for target in targets:
        if ':' not in target:raise RuntimeError('Unqualified target: '+target)
        part,path=target.split(':',1)
        pure=PurePosixPath(path)
        if part not in SAFE_PARTS or not pure.is_absolute() or '..' in pure.parts or pure.suffix.lower()!='.apk':
            raise RuntimeError('Invalid or unreviewed target: '+target)
        if len(pure.parts)<4:raise RuntimeError('Refusing broad directory target: '+target)
        parsed[target]=(part,pure)
    return parsed

def extract_archive(archive,temporary):
    members=[('path','type','bytes')]
    clues=[]
    vbmeta={}
    super_path=temporary/'super.sparse.img'
    have_super=False
    # Streaming tar: enumerate EVERY source entry once, save only super + small AVB.
    with tarfile.open(archive,'r|gz') as stream:
        for item in stream:
            p=PurePosixPath(item.name)
            if p.is_absolute() or '..' in p.parts or item.issym() or item.islnk() or item.isdev():
                raise RuntimeError('Unsafe vendor archive member: '+item.name)
            members.append((item.name,'file' if item.isfile() else 'other',item.size))
            if not item.isfile():continue
            if p.name=='super.img' and p.parent.name=='images':
                if have_super:raise RuntimeError('Duplicate super.img')
                with stream.extractfile(item) as source,super_path.open('wb') as dest:
                    shutil.copyfileobj(source,dest,8*1024*1024)
                have_super=True
            elif p.parent.name=='images' and p.name in AVB_FILES:
                if p.name in vbmeta or item.size!=AVB_FILES[p.name]:
                    raise RuntimeError('Unexpected/duplicate AVB image: '+item.name)
                vbmeta[p.name]=stream.extractfile(item).read()
            elif item.size<=CONFIG_LIMIT and p.suffix.lower() in SCANNED_SUFFIXES:
                data=stream.extractfile(item).read().decode('utf-8','replace')
                if p.name.startswith('flash_') or p.name in ('misc.txt','anti_version.txt','crclist.txt','sparsecrclist.txt'):
                    clues.append('=== '+str(p)+' ===\n'+data[:150_000])
    tsv('archive-members.tsv',('path','type','bytes'),members[1:])
    emit('flash-scripts-and-metadata.txt','\n'.join(clues))
    if not have_super or set(vbmeta)!=set(AVB_FILES):
        raise RuntimeError('Source archive missing super or one of three vbmeta images')
    return super_path,vbmeta

def parse_partitions(layout,slot):
    if 'Partition table:' not in layout or 'Block device table:' not in layout:
        raise RuntimeError('Cannot recognize lpdump table')
    part_table=layout.split('Partition table:',1)[1].split('Super partition layout:',1)[0]
    result=[]
    for block in part_table.split('------------------------'):
        match=re.search(r'(?m)^\s*Name:\s*([A-Za-z0-9_.-]+)\s*$',block)
        if not match:continue
        if re.search(r'(?m)^\s*\d+\s*\.\.\s*\d+\s+(?:linear|zero)\b',block):
            result.append((slot,match.group(1)))
    return result

def avb_checks(vbmeta):
    audited=[audit_one(n,vbmeta[n]) for n in AVB_FILES]
    emit('avb-descriptors.json',json.dumps(audited,indent=2)+'\n')
    hashtrees={}
    for entry in audited:
        for descriptor in entry['descriptors']:
            if descriptor['type']=='hashtree':
                key=descriptor['partition']
                if key in hashtrees:raise RuntimeError('Duplicate AVB hashtree: '+key)
                hashtrees[key]=(entry['image'],descriptor)
    return audited,hashtrees

def find_aapt():
    home=Path(os.environ.get('ANDROID_HOME', '/usr/local/lib/android/sdk'))
    candidates=list((home/'build-tools').glob('*/aapt2'))
    candidates.sort(key=lambda p:[int(x) if x.isdigit() else x for x in re.split(r'(\d+)',p.parent.name)],reverse=True)
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate,os.X_OK):return str(candidate)
    for tool in ('aapt2','aapt'):
        path=shutil.which(tool)
        if path:return path
    raise RuntimeError('aapt2/aapt missing: cannot inspect Android package identities; install Android build-tools')

def apk_identity(aapt,file):
    cmd=[aapt,'dump','badging',str(file)]
    proc=subprocess.run(cmd,capture_output=True,text=True,timeout=70)
    if proc.returncode!=0:raise RuntimeError('aapt failed: '+proc.stderr[:250])
    txt=proc.stdout
    pkg=re.search(r"(?m)^package:\s+name='([^']+)'",txt)
    if not pkg:raise RuntimeError('Missing package ID in badging')
    needs=re.findall(r"(?m)^uses-library:'([^']+)'",txt)
    needs+=re.findall(r"(?m)^uses-package:'([^']+)'",txt)
    return pkg.group(1),sorted(set(needs))

def snapshot_entry(path,partition,mount):
    st=path.lstat()
    label='UNAVAILABLE'
    attrs=[]
    try:
        for attr in sorted(os.listxattr(path,follow_symlinks=False)):
            try:
                raw=os.getxattr(path,attr,follow_symlinks=False)
                attrs.append(attr+'='+hashlib.sha256(raw).hexdigest())
                if attr=='security.selinux':label=raw.decode('utf8','replace').strip('\0')
            except OSError:attrs.append(attr+'=UNREADABLE')
    except OSError:attrs.append('UNAVAILABLE')
    if stat.S_ISDIR(st.st_mode):kind='directory'
    elif stat.S_ISLNK(st.st_mode):kind='symlink'
    elif stat.S_ISREG(st.st_mode):kind='file'
    else:kind='other'
    link=os.readlink(path) if kind=='symlink' else ''
    rel='/'+str(path.relative_to(mount)) if path!=mount else '/'
    return (partition,rel,kind,st.st_uid,st.st_gid,oct(stat.S_IMODE(st.st_mode)),
            st.st_size,st.st_mtime_ns,label,hashlib.sha256('|'.join(attrs).encode()).hexdigest(),link)

def scan_image(slot,part,superraw,aapt,targets,full_apks,config_texts,
               snapshots,filesystem_rows,erofs_logs,problems):
    image_dir=superraw.parent/'partition'
    image_dir.mkdir(exist_ok=True)
    mount=superraw.parent/'mnt'
    mount.mkdir(exist_ok=True)
    try:
        proc=command(TOOLS/'lpunpack',f'--slot={slot}',f'--partition={part}',superraw,image_dir)
        if proc.returncode:raise RuntimeError('lpunpack '+proc.stderr[:400])
        image=image_dir/(part+'.img')
        if not image.is_file():raise RuntimeError('Missing unpacked '+part)
        filesystem=fstype(image)
        filesystem_rows.append((part,slot,filesystem,image.stat().st_size))
        if filesystem!='erofs':raise RuntimeError('Expected EROFS; observed '+filesystem)
        dump=command('dump.erofs','-s',image)
        erofs_logs.append('=== '+part+' ===\n'+dump.stdout+'\n'+dump.stderr)
        if dump.returncode:problems.append('dump.erofs failed for '+part)
        mounted=False
        try:
            result=command('mount','-t','erofs','-o','ro,loop',image,mount)
            if result.returncode:raise RuntimeError('EROFS mount failed: '+result.stderr[:300])
            mounted=True
            for directory,subdirs,files in os.walk(mount,followlinks=False):
                base=Path(directory)
                if part in SAFE_PARTS:
                    for entity in [base]+[base/n for n in subdirs+files]:
                        snapshots.append(snapshot_entry(entity,part,mount))
                for filename in files:
                    path=base/filename
                    if path.is_symlink():continue
                    rel='/'+str(path.relative_to(mount))
                    if filename.lower().endswith('.apk'):
                        location=part+':'+rel
                        try:
                            pkg,needs=apk_identity(aapt,path)
                            full_apks[location]=(pkg,needs)
                        except (RuntimeError,subprocess.TimeoutExpired) as ex:
                            full_apks[location]=('',[])
                            if location in targets:
                                problems.append('Cannot parse selected APK '+location+': '+str(ex))
                    elif path.suffix.lower() in SCANNED_SUFFIXES and path.stat().st_size<=CONFIG_LIMIT:
                        # Keep only text-like config; do not upload proprietary binary data.
                        if '/etc/' in rel or rel.startswith('/etc/'):
                            data=path.read_bytes()
                            if b'\0' not in data[:2048]:
                                config_texts.append((part+':'+rel,data.decode('utf8','replace')))
        finally:
            if mounted:
                subprocess.run(['umount',str(mount)],check=True)
    finally:
        shutil.rmtree(image_dir,ignore_errors=True)

def preflight():
    REPORT.mkdir(parents=True,exist_ok=True)
    targets=permitted()
    problems=[];warnings=[]
    with tempfile.TemporaryDirectory(prefix='yunluo-preflight-') as work:
        temp=Path(work);archive=temp/NAME
        subprocess.run(['python3',str(ROOT/'scripts/download.py'),
                        '--output',str(archive),'--report',str(REPORT/'cdn-probes.json')],check=True)
        observed=sha(archive,'md5')
        emit('source-checksum.txt','Source: '+NAME+'\nExpected MD5: '+MD5+'\nActual MD5: '+observed+'\n')
        if observed!=MD5:raise RuntimeError('Firmware archive checksum mismatch')
        original,images=extract_archive(archive,temp)
        # No second archive download and no second extraction of super.
        archive.unlink()
        avb,hashtrees=avb_checks(images)
        with original.open('rb') as f:sparse=f.read(4)==bytes.fromhex('3aff26ed')
        superraw=temp/'super.raw.img'
        if sparse:
            result=command(TOOLS/'simg2img',original,superraw)
            if result.returncode:raise RuntimeError('Sparse conversion failed: '+result.stderr)
            original.unlink()
        else:original.rename(superraw)
        if superraw.stat().st_size!=SUPER_RAW_SIZE:
            raise RuntimeError('Unexpected original raw super size; do not proceed')
        emit('super-source.txt','original_sparse='+str(sparse)+'\nraw_size='+str(superraw.stat().st_size)+
             '\nraw_sha256='+sha(superraw)+'\n')
        populated=[]
        for slot in (0,1):
            dump=command(TOOLS/'lpdump','-s',slot,superraw)
            emit('lpdump-slot'+str(slot)+'.txt',dump.stdout+'\nSTDERR:\n'+dump.stderr)
            if dump.returncode:
                problems.append('Missing/invalid lpdump metadata slot '+str(slot))
            else:
                for item in parse_partitions(dump.stdout,slot):
                    if item[1] not in [p[1] for p in populated]:
                        populated.append(item)
        if not populated:raise RuntimeError('No populated LP entries')
        aapt=find_aapt()
        emit('tools-and-versions.txt','aapt='+aapt+'\n'+command(aapt,'version').stdout+
             '\n'+command('mkfs.erofs','-V').stdout+'\n')
        full_apks={};config_texts=[];snapshots=[];filesystem_rows=[];erofs_logs=[]
        for slot,part in populated:
            scan_image(slot,part,superraw,aapt,targets,full_apks,config_texts,
                       snapshots,filesystem_rows,erofs_logs,problems)
        tsv('filesystems.tsv',('partition','metadata_slot','filesystem','bytes'),filesystem_rows)
        emit('erofs-superblock-summary.txt','\n'.join(erofs_logs))
        tsv('metadata-original.tsv',
            ('partition','path','type','uid','gid','mode','size','mtime_ns','selinux','xattrs_sha256','symlink_target'),snapshots)
        tsv('apk-packages.tsv',('location','android_package_id','required_uses_libraries'),
            [(loc,pkg,','.join(needs)) for loc,(pkg,needs) in sorted(full_apks.items())])
        expected=set(targets)
        found=set(full_apks)
        missing=sorted(expected-found)
        if missing:problems.extend('Target not present in original super: '+m for m in missing)
        candidate_packages={loc:full_apks[loc][0] for loc in expected&found if full_apks[loc][0]}
        if len(candidate_packages)!=33:problems.append('One or more candidate APKs lack a validated package ID')
        package_to_path={}
        for loc,(pkg,_) in full_apks.items():
            if pkg:package_to_path.setdefault(pkg,[]).append(loc)
        for loc,pkg in candidate_packages.items():
            outsiders=[x for x in package_to_path[pkg] if x!=loc and x not in targets]
            if outsiders:
                warnings.append('Same package ID has surviving APK variants: '+loc+' => '+str(outsiders))
        removed_pkgs=set(candidate_packages.values())
        for loc,(pkg,uses) in full_apks.items():
            if loc not in targets:
                for use in uses:
                    if use in removed_pkgs:
                        problems.append('Surviving APK declares required dependency '+use+' at '+loc)
        dirs=[]
        for loc in sorted(targets):
            part,path=targets[loc]
            folder=part+':'+str(path.parent)
            inside=[x for x in full_apks if x.startswith(folder+'/')]
            extras=[x for x in inside if x not in targets]
            if extras:warnings.append('Directory has additional APKs/splits to inspect: '+folder+': '+','.join(extras))
            dirs.append((loc,candidate_packages.get(loc,'UNPARSED'),folder,
                         'REVIEW ONLY — no deletion',','.join(extras)))
        tsv('first-pass-33-review.tsv',
            ('apk_location','android_package_id','dedicated_directory','action','extra_apks'),dirs)
        refs=[]
        for cfg_path,body in config_texts:
            for lineno,line in enumerate(body.splitlines(),1):
                for candidate,pkg in candidate_packages.items():
                    if pkg and pkg in line:
                        refs.append((candidate,pkg,cfg_path,lineno,re.sub(r'\s+',' ',line.strip())[:300]))
        tsv('config-references.tsv',('selected_apk','package','config_file','line','text'),refs)
        if refs:warnings.append(str(len(refs))+' source-config references to removal candidates; examine config-references.tsv')
        protected=('XiaomiServiceFrameworkGlobal','XMSFKeeperAll','MIUIXiaomiAccountGlobal',
                   'MIUICloudServiceGlobal','FindDevice','RtMiCloudSDK','DuraSpeed',
                   'GoogleOneTimeInitializer','GooglePartnerSetup','EmergencyInfoGms',
                   'FamilyLinkParentalControls','Updater','com.google.mainline.telemetry',
                   'com.google.mainline.adservices','NetworkBoost')
        for loc in targets:
            if any('/'+name+'/'+name+'.apk' in loc for name in protected):
                problems.append('Protected component unexpectedly selected: '+loc)
        desc_rows=[]
        sizes={part:count for part,_,_,count in filesystem_rows}
        for part,slot,typ,count in filesystem_rows:
            base=re.sub(r'_[ab]$','',part)
            if base in hashtrees:
                owner,desc=hashtrees[base]
                tree_end=desc.get('tree_offset',0)+desc.get('tree_size',0)
                valid=desc.get('image_size',count)<=count and tree_end<=count
                desc_rows.append((part,owner,desc.get('image_size',''),desc.get('tree_offset',''),
                                  desc.get('tree_size',''),count,'PASS' if valid else 'FAIL'))
                if not valid:problems.append('AVB hashtree exceeds '+part+' logical partition')
            else:
                desc_rows.append((part,'NOT_FOUND','','','',count,'CHECK'))
                warnings.append('AVB descriptor not found for '+part+' (could be non-verified)')
        tsv('avb-image-bounds.tsv',
            ('logical_partition','vbmeta_owner','payload_bytes','tree_offset','tree_bytes','partition_bytes','bounds'),desc_rows)
        if len(full_apks)<250:problems.append('Suspiciously few APKs discovered: '+str(len(full_apks)))
        if len(snapshots)<1000:problems.append('Suspiciously small metadata baseline')
        if len(populated)!=8:problems.append('Unexpected populated logical partition count: '+str(len(populated)))
        for entry in avb:
            if entry['flags']!=0:warnings.append('Original vbmeta flags not zero: '+entry['image'])
        emit('blockers.txt','\n'.join(problems)+'\n' if problems else 'No structural/manifest preflight blockers detected.\n')
        emit('review-warnings.txt','\n'.join(warnings)+'\n' if warnings else 'No config reference warnings detected.\n')
        report=['# Combined MIUI 14 preflight (read-only)','',
                'Firmware: '+VER+' (MD5 matched)',
                'Selected candidate APKs: 33 (no removals performed)',
                'Populated partitions scanned: '+str(len(populated)),
                'APK manifests scanned: '+str(len(full_apks)),
                'Metadata baseline records: '+str(len(snapshots)),
                'Config cross-references: '+str(len(refs)),
                'AVB metadata images parsed: '+str(len(avb)),
                'Structural errors: '+str(len(problems)),
                'Review warnings: '+str(len(warnings)),'',
                '**FLASH READINESS: NOT APPROVED.** Existing AVB flags are zero and',
                'stock hashtrees cover the intended partitions. No rebuilding, disabling',
                'verified boot, repackaging, or flashing occurs in this job.','',
                'The source metadata baseline does not prove reconstructed EROFS equivalence.',
                'A future rebuild must be mounted and compared path-by-path against this baseline',
                'for all retained entries, including labels, xattrs, symlinks, owners and modes.',
                'Even an error-free preflight cannot guarantee a first boot.','',
                'Review first-pass-33-review.tsv, config-references.tsv,',
                'avb-image-bounds.tsv and blockers.txt before any build.']
        emit('SUMMARY.md','\n'.join(report)+'\n')
        emit('status.json',json.dumps({'download_verified':True,'manifest_count':len(full_apks),
            'candidates':len(candidate_packages),'preflight_blockers':problems,
            'warnings':warnings,'flash_ready':False,'firmware_modified':False},indent=2)+'\n')
        print('\n'.join(report),flush=True)
        if problems:raise RuntimeError('Combined preflight has '+str(len(problems))+' blocking issues. See uploaded artifact.')

if __name__=='__main__':
    preflight()
