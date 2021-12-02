import hashlib, gc, os, time
import binascii as ubinascii
import libs.urequests as req               # type: ignore
import network

time.sleep(3)
# Is device microcontroller

_OTA_URL_BASE = "http://192.168.1.235/"

_UPDATE_DIR = "/OTA/DOWNLOADED"     # where to save downloaded content
_BACKUP_DIR = "/OTA/BACKUP"      # where to copy currently content
_VERSION_FILE = "/OTA/.VERSION"          # Version of current solution. if remote OTA_VER.json is bigger- need to perform update


def file_exists(path):
    try:
        f = open(path, "r")
        f.close()
        return True
    except OSError:     # type: ignore
        return False

def dir_exists(path):
    try:
        if os.stat(path)[0] & 0x4000:  # Dir
            return True
        else:
            return False
    except OSError:     # type: ignore
        return False

def check_file_hash(file, hash=None):
    h = hashlib.sha256()
    with open(file, 'rb') as f:
        for line in f:
            h.update(line)
        if hash is not None:
            return ubinascii.hexlify(h.digest()).decode('utf-8') == hash
        else:
            return ubinascii.hexlify(h.digest()).decode('utf-8')

def is_update_available(URL_BASE):       # by checking versions
    r = req.get("{}/OTA_ver.json".format(URL_BASE))
    if r.status_code == 200:
        try:
            v = r.json()
            OTA_ver = int(v["version"])
        except Exception as e:          # type: ignore
            print("{}/OTA_ver.json in not valid JSON file:".format(URL_BASE))
            print(r.content.decode("utf-8"))
            print(e)
            return False
        
    
        with open(_VERSION_FILE, "rb") as f:
            if OTA_ver > int(f.read()):
                return True
    elif r.status_code in [404, 400]:
        print("File '{1}' was not found in {0}".format(URL_BASE, "OTA_ver.json"))
    return False

def download_meta(meta_file):
    r = req.get(meta_file)
    if r.status_code == 200:
        return r.json()

def download_file(url_base, path, parent):
    # create directory structure for file
    full_path = parent
    for dir in path.split("/")[:-1]:        # check do direcotries exist
        full_path = "{}/{}".format(full_path, dir)
        if not dir_exists(full_path):
            # print(full_path, " dir does not exist. Creating")
            try:
                os.mkdir(full_path)
            except BaseException:
                print("Failed to create directory: {}".format(full_path))
    del full_path

    r = req.get("{}/{}".format(url_base, path))
    if r.status_code == 200:
        with open("{}/{}".format(parent, path), 'wb+') as f:
                f.write(r.content)
    else:
        print("Download error. HTTP error {0} for file {1}".format(r.status_code, path))

def remove_recursive(source, preserve_top=False, keep_files = []):
    for f in os.ilistdir(source):
        if not file_exists("{}/{}".format(source, f[0])):
            remove_recursive("/".join((source, f[0])))  # File or Dir
        else:
            os.remove("{}/{}".format(source, f[0]))

    if not preserve_top:
        os.rmdir(source)

def move_directory_tree(source, destination, exclude=[]):
    for f in (os.ilistdir(source)):
        if f[0] not in exclude:
            os.rename("{}/{}".format(source, f[0]), "{}/{}".format(destination, f[0]))

  
if __name__ == "__main__":
    # connect wifi if needed
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
    print("Connected. Network config:", sta_if.ifconfig())

    if not file_exists(_VERSION_FILE):
        with open(_VERSION_FILE, "w") as vf:
            vf.write("0")

    if is_update_available(_OTA_URL_BASE):                 # if local version older than in metadata
        print("Update is available")

        if dir_exists(_UPDATE_DIR):
            remove_recursive(_UPDATE_DIR, True)
        else:
            os.mkdir(_UPDATE_DIR)

        metafile = download_meta("{}/OTA_meta.json".format(_OTA_URL_BASE))          # download metadata from http
        for file in metafile["files"]:      # read files list
            download_file(_OTA_URL_BASE, file["name"], _UPDATE_DIR)
            if check_file_hash("{}/{}".format(_UPDATE_DIR, file["name"]), file["hash"]):
                print("Hash OK", file["hash"], file["name"])
            else:
                print("Hash does not match for file ", file["name"])

        # make backup of all files
        if metafile["do_backup"]:
            if dir_exists(_BACKUP_DIR):
                remove_recursive(_BACKUP_DIR, True)
            else:
                os.mkdir(_BACKUP_DIR)
            move_directory_tree("/", _BACKUP_DIR, ["OTA"])  # move everything excluding OTA directory


        
        # save all content or delete except OTA
        if metafile["preserve"]:
            pass

        # Copy new files from _UPDATE_DIR
        move_directory_tree(_UPDATE_DIR, os.getcwd())

        # update local version file
        with open(_VERSION_FILE, "w") as ver:
            ver.write(metafile["version"])
        
        # Clean up after finishing
        remove_recursive(_UPDATE_DIR)

    else:
        print("No update available")

