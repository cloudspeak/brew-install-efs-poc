import subprocess
import os
import shutil
import ctypes

from ctypes.util import find_library

def my_handler(event, context):

    # Append to environment variables
    packages_path = os.environ["LAMBDA_PACKAGES_PATH"]
    os.environ["PATH"] = f"{os.environ["PATH"]}:{packages_path}/bin"
    os.environ["LD_LIBRARY_PATH"] = f"{os.environ["LD_LIBRARY_PATH"]}:{packages_path}/lib"

    print("PATH=", os.environ["PATH"])
    print("LDPATH=", os.environ["LD_LIBRARY_PATH"])

    o = subprocess.run(["/sbin/ldconfig", "--version"], check=False, capture_output=True, encoding="utf-8")
    print(o)
    print(shutil.which("objdump"))
    print(shutil.which("ld"))
    print("Storage dir:", packages_path)
    print("Storage dir content:", os.listdir(packages_path))

    print("Find lib:", find_library('libproj.so'))

    testlib = ctypes.CDLL('libproj.so')
    x = testlib.proj_area_create()
    print(x)

    return { 
        'message' : "Called library successfully",
        'result': x
    }