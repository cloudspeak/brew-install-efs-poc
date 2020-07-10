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

    # Debugging: Check that find_library can see the libraries
    print("find_library proj:", find_library('proj'))
    print("find_library exif:", find_library('exif'))

    # Simple test to call the `proj_area_create` function on the proj library and the
    # `exif_content_new` function on the exif library.  If they return a pointer,
    # they are working.

    proj_result = None
    exif_result = None

    try:
        projlib = ctypes.CDLL(find_library('proj'))
        proj_result = projlib.proj_area_create()
        print("Call proj_area_create result:", proj_result)
    except Exception:
        pass

    try:
        exiflib = ctypes.CDLL(find_library('exif'))
        exif_result = exiflib.exif_content_new()
        print("Call exif_content_new result:", exif_result)
    except Exception:
        pass

    if proj_result is None and exif_result is None:
        raise Exception("Could not find libraries")
    
    return { 
            'message' : "Found a library",
            'libproj_found': proj_result is not None,
            'libexif_found': exif_result is not None,
            'libproj_pointer': proj_result,
            'libexif_pointer': exif_result,
        }
