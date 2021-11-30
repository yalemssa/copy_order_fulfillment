#/usr/bin/python3

import os
import shutil
from constants import console
from rich.progress import track
import copy_order_logging

'''Zips Preservica files'''

log = copy_order_logging.get_logger(__name__)

def main():
    try:
        log.debug('Packaging files')
        dirpath = "data/orders/to_zip"
        output_path = f"data/orders/uploads/"
        dir_list = [item for item in os.listdir(dirpath) if item not in ('.DS_Store', 'to_upload')]
        log.debug(dir_list)
        for directory in track(dir_list):
            full_path = f"{dirpath}/{directory}"
            final_path = f"{output_path}/{directory}"
            if os.path.isdir(full_path):
                shutil.make_archive(final_path, 'zip', full_path)
    except Exception as e:
        log.error(e)
        console.print_exception()
        raise e

if __name__ == "__main__":
    main()