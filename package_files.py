#/usr/bin/python3

import os
import shutil
from constants import console
from rich.progress import track

'''Zips Preservica files'''

def main():
    try:
        console.log('Starting...')
        dirpath = "data/orders/to_zip"
        output_path = f"data/orders/to_send/"
        dir_list = os.listdir(dirpath)
        print(dir_list)
        for directory in track(dir_list):
            if directory not in ("to_send", ".DS_Store"):
                full_path = f"{dirpath}/{directory}"
                final_path = f"{output_path}/{directory}"
                if os.path.isdir(full_path):
                    shutil.make_archive(final_path, 'zip', full_path)
    except Exception:
        console.print_exception()
    finally:
        console.log("Exiting...")


if __name__ == "__main__":
    main()