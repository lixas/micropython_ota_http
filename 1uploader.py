import ftplib
import os, io, json, hashlib, time     # type: ignore


FTP_ADR = "127.0.0.1"
FTP_PRT = 21
FTP_LOC = "/"
FTP_USR = ""        # leave empty if annonymous
FTP_PSW = ""
BASE = "board/"     # with trailing slash

# settings for json file to be used on board
DO_BACKUP = True       # make copy of existing files for backup
PRESERVE_ALL = False     # keep files that are already exists


def delete_recursive(path):
    dirs = []
    files = []
    ftp.cwd(path)
    ftp.retrlines("LIST", lambda L: dirs.append(L[52:]) if L[0:1] == "d" else files.append(L[52:]))
    for file in files:
        ftp.delete(file)
    for dir in dirs:
        delete_recursive(dir)
        ftp.cwd("..")
        ftp.rmd(dir)


def upload_recursive(ftp, path, omit):
    for name in os.listdir(path):
        localpath = os.path.join(path, name)
        if os.path.isfile(localpath):
            ftp.storbinary('STOR ' + name, open(localpath, 'rb'))
            with open(localpath, 'rb') as f:
                h = hashlib.sha256(f.read())
            metadata.append({"name": localpath.replace("\\", "/").replace(omit, ""), "hash": h.digest().hex()})
        elif os.path.isdir(localpath):
            try:
                ftp.mkd(name)
            # ignore "directory already exists"
            except ftplib.all_errors as e:
                if not e.args[0].startswith('550'):
                    raise
            ftp.cwd(name)
            upload_recursive(ftp, localpath, omit)
            ftp.cwd("..")


ftp = ftplib.FTP(FTP_ADR)
if FTP_USR != "":
    ftp.login(FTP_USR, FTP_PSW)
else:
    ftp.login()

delete_recursive(FTP_LOC)

version = "{}{:02d}{:02d}{:02d}{:02d}{:02d}".format(*time.localtime()[0:6])
metadata = []

os.chdir(os.path.dirname(os.path.realpath(__file__)))
upload_recursive(ftp, BASE, BASE)
metafile = io.BytesIO()
metafile.write(json.dumps({
    "version": version,
    "do_backup": DO_BACKUP,
    "preserve": PRESERVE_ALL,
    "files": metadata
}).encode())
metafile.seek(0)  # move to beginning of file
ftp.storbinary('STOR ' + "OTA_meta.json", metafile)

versionfile = io.BytesIO()
versionfile.write(json.dumps({"version": version}).encode())
versionfile.seek(0)
ftp.storbinary('STOR ' + "OTA_ver.json", versionfile)

ftp.quit()

