import subprocess
import os
import shutil
import ctypes

from ctypes.util import find_library

def my_handler(event, context):
    # Debugging: check that the environment variables include the EFS libraries path
    print("EFS libraries: ", os.environ["LAMBDA_PACKAGES_PATH"])
    print("PATH=", os.environ["PATH"])
    print("LD_LIBRARY_PATH=", os.environ["LD_LIBRARY_PATH"])

    # Debugging: check that the tools required by ctypes are present
    print(subprocess.run(["/sbin/ldconfig", "--version"], check=False, capture_output=True, encoding="utf-8").stdout)
    print(shutil.which("objdump"))
    print(shutil.which("ld"))

    # Debugging: Check that find_library can see the proj library
    print("find_library:", find_library('proj'))

    # Simple test to call the `proj_area_create` function on the proj library.  The result
    # is just a pointer if we get that rather than an error, it is working.

    print("A different message")

    try:
        projlib = ctypes.CDLL(find_library('proj'))
        result = projlib.proj_area_create()
        print("Call proj_area_create result:", result)
        return { 
            'message' : "Called library successfully",
            'result': result
        }
    except Exception:
        raise "Failed: could not find library"
