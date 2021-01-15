import hashlib, gc, os, time
import binascii as ubinascii

_Platform = "MPY"        # "PC" or "MPY"

if _Platform == "PC":
    import requests as req               # type: ignore
elif _Platform == "MPY":
    import libs.urequests as req               # type: ignore


_UPDATE_DIR = "OTA/UPDATE"     # where to save downloaded content
_BACKUP_DIR = "OTA/BACKUP"     # where to copy currently content
_UPDATE_FLAG = ".OTA_PENDING"    # no trailing slash. name of file with indicates that update should be performed. Contains URL base of update
_VERSION_FILE = ".VERSION"          # file, where

# _URL_BASE = ""      # will be read from _UPDATE_FLAG where is update


def file_exists(path):
    try:
        f = open(path, "r")
        exists = True
        f.close()
    except OSError:     # type: ignore
        exists = False
    return exists


def dir_exists(path):
    try:
        f = os.listdir(path)
        if f != []:
            exists = True
        else:
            exists = False
    except OSError:      # type: ignore
        exists = False
    return exists


def check_file_hash(file, hash=None):
    h = hashlib.sha256()
    with open(file, 'rb') as f:
        for line in f:
            h.update(line)
        if hash is not None:
            return ubinascii.hexlify(h.digest()).decode('utf-8') == hash
        else:
            return ubinascii.hexlify(h.digest()).decode('utf-8')

def is_update_pending():       # by checking versions
    # global _URL_BASE
    r = req.get("{}/OTA_ver.json".format(_URL_BASE))
    if r.status_code == 200:
        try:
            v = r.json()
            OTA_ver = int(v["version"])
        except Exception as e:          # type: ignore
            print("{}/OTA_ver.json in not valid JSON file:".format(_URL_BASE))
            print(r.content.decode("utf-8"))
            print(e)
            return False
        
    
        with open(_VERSION_FILE, "rb") as f:
            if OTA_ver > int(f.read()):
                return True
    elif r.status_code in [404, 400]:
        print("File '{1}' was not found in {0}".format(_URL_BASE, "OTA_ver.json"))
    return False

def download_meta():
    global _URL_BASE
    r = req.get("{}/OTA_meta.json".format(_URL_BASE))
    if r.status_code == 200:
        return r.json()

def download_file(path, parent):
    global _URL_BASE
    # create directory structure for file
    full_path = parent
    for dir in path.split("/")[:-1]:        # check do direcotries exist
        full_path = "{}/{}".format(full_path, dir)
        if not dir_exists(full_path):
            print(full_path, " dir does not exist. Creating")
            try:
                os.mkdir(full_path)
            except:
                pass
    del full_path

    r = req.get("{}/{}".format(_URL_BASE, path))
    if r.status_code == 200:
        with open("{}/{}".format(parent, path), 'wb+') as f:
                f.write(r.content)

def check_for_new_version(location):
    # connect to wifi
    r = req.get("{}/OTA_ver.json".format(location))
    if r.status_code == 200:
        OTA_ver = int(r.json()["version"])

        # check for local version
        local_ver = 0
        if file_exists(_VERSION_FILE):
            with open(_VERSION_FILE, "rb") as f:
                local_ver = int(f.read())
        
        if OTA_ver > local_ver:
            with open(_UPDATE_FLAG, "w+") as f:
                f.write(location.encode('utf-8'))
            return True
        else:
            return False

def rm(d, preserve_top=False):  # Remove file or tree
    try:
        if os.stat(d)[0] & 0x4000:  # Dir
            for f in os.ilistdir(d):
                if f[0] not in ('.', '..'):
                    rm("/".join((d, f[0])))  # File or Dir
            if not preserve_top:
                os.rmdir(d)
        else:  # File
            os.remove(d)
    except:
        print("rm of '%s' failed" % d)

# print(check_file_hash("boot.py", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"))
# Cler UPDATE catalog recursive

if _Platform == "PC":
    os.chdir(os.path.dirname(os.path.realpath(__file__)))

if _Platform == "MPY":
    import network
    gc.collect()
    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        print("Connecting to WiFi...")
        sta_if.active(True)
        sta_if.connect("wifi-name", "wifi-pass")
        while not sta_if.isconnected():
            print(".", end="")
            time.sleep(0.3)
    print(".")
    print("Connected")
    print('network config:', sta_if.ifconfig())

# connect wifi if needed
with open("{}".format(_UPDATE_FLAG), "rb") as f:
    _URL_BASE = f.read().decode("utf-8")

if is_update_pending():                 # if local version older than in metdata
    print("Update is available")
    metafile = download_meta()          # download metadata
    if dir_exists(_UPDATE_DIR):
        rm(_UPDATE_DIR, True)
    else:
        os.mkdir(_UPDATE_DIR)
    for file in metafile["files"]:      # read files list
        download_file(file["name"], _UPDATE_DIR)
        if check_file_hash("{}/{}".format(_UPDATE_DIR, file["name"]), file["hash"]):
            print("OK", file["hash"], file["name"])
        else:
            print("Hash does not match for file ", file["name"])
            print("Local  {}".format(check_file_hash("{}/{}".format(_UPDATE_DIR, file["name"]))))
            print("Remote {}".format(file["hash"]))
else:
    print("No update available")



#         Download file
#         Check hash
# create update_pending file
