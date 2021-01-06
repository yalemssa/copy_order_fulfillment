#/usr/bin/python3

import os
import shutil
from constants import console
from rich.progress import track

'''Zips Preservica files'''

def main():
    try:
        console.log('Starting...')
        dirpath = "data/orders/"
        dir_list = os.listdir(dirpath)
        for directory in track(dir_list):
            full_path = f"{dirpath}{directory}"
            if os.path.isdir(full_path):
                shutil.make_archive(full_path, 'zip', full_path)
    except Exception:
        console.print_exception()
    finally:
        console.log("Exiting...")


if __name__ == "__main__":
    main()