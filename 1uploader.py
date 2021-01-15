import ftplib
import os, io, json, hashlib, time     # type: ignore


FTP_ADR = "127.0.0.1"
FTP_PRT = 21
FTP_LOC = "OTA/"
FTP_USR = ""        # leave empty if annonymous
FTP_PSW = ""

BASE = "board/"     # no trailing slash


def delete_recursive(path):
    dirs = []
    files = []
    ftp.cwd(path)
    ftp.retrlines("LIST", lambda L: dirs.append(L[52:]) if L[0:1] == "d" else files.append(L[52:]))
    # print("Path:", path, "dirs: ", dirs, "Files: ", files)
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
            # print("STOR", name, localpath)
            ftp.storbinary('STOR ' + name, open(localpath, 'rb'))
            with open(localpath, 'rb') as f:
                h = hashlib.sha256(f.read())
            metadata.append({"name": localpath.replace("\\", "/").replace(omit, ""), "hash": h.digest().hex()})
        elif os.path.isdir(localpath):
            # print("MKD", name)

            try:
                ftp.mkd(name)
            # ignore "directory already exists"
            except ftplib.all_errors as e:
                if not e.args[0].startswith('550'):
                    raise

            # print("CWD", name)
            ftp.cwd(name)
            upload_recursive(ftp, localpath, omit)
            # print("CWD", "..")
            ftp.cwd("..")


ftp = ftplib.FTP(FTP_ADR)
if FTP_USR != "":
    ftp.login(FTP_USR, FTP_PSW)
else:
    ftp.login()

delete_recursive(FTP_LOC)

metadata = []

os.chdir(os.path.dirname(os.path.realpath(__file__)))
upload_recursive(ftp, BASE, BASE)
metafile = io.BytesIO()
metafile.write(json.dumps({"files": metadata}).encode())
metafile.seek(0)  # move to beginning of file
ftp.storbinary('STOR ' + "OTA_meta.json", metafile)

versionfile = io.BytesIO()
versionfile.write(json.dumps({"version": "{}{:02d}{:02d}{:02d}{:02d}{:02d}".format(*time.localtime()[0:6])}).encode())
versionfile.seek(0)
ftp.storbinary('STOR ' + "OTA_ver.json", versionfile)

ftp.quit()

