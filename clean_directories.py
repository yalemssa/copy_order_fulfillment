#/usr/bin/python3

import json
import os
import shutil

import copy_order_logging

'''
After sending files, do the following:
    - Move emails to sent folder (maybe - it's helpful to do this manually to keep track; at least as long as I am doing this)
    - _Move input spreadsheets to data/orders/old_reports
    - _Delete unzipped files in data/orders/to_zip folder
    - _Move zipped_files in data/orders/to_send folder to data/orders/sent folder
    - Move orders/shared_link_report.csv to data/orders/old_reports
'''

log = copy_order_logging.get_logger(__name__)

def move_files(base_path, source_path, dest_path):
	source_path_full = f"{base_path}/{source_path}"
	files_in_source = os.listdir(source_path_full)
	for filename in files_in_source:
		if filename != '.DS_Store':
			full_path_old = f"{source_path_full}/{filename}"
			full_path_new = f"{base_path}/{dest_path}/{filename}"
			shutil.move(full_path_old, full_path_new)

def delete_folders(local_drive, source_path):
	to_zip_folder = f"{local_drive}/{source_path}"
	files_in_folder = [item for item in os.listdir(to_zip_folder) if item != '.DS_Store']
	for filename in files_in_folder:
		full_path = f"{to_zip_folder}/{filename}"
		if os.path.isdir(full_path):
			shutil.rmtree(full_path)
		else:
			log.debug(f"Not a directory: {full_path}")

def main():
	try:
		cfg = json.load(open('config/config.json'))
		network_drive = cfg.get('network_drive')
		local_drive = cfg.get('local_drive')
		# moves report files on network drive from orders/_new_ folder to sent/reports folder
		# had this set to the local drive, but I don't think that was doing anything
		move_files(network_drive, cfg.get('new_report_subfolder'), cfg.get('sent_report_subfolder'))
		# moves zipped files on local drive from orders/to_upload folder to sent/files folder
		move_files(local_drive, cfg.get('files_to_send_subfolder'), cfg.get('sent_files_subfolder'))
		# deletes unzipped folders on local drive from orders/to_zip
		delete_folders(local_drive, cfg.get('files_to_zip_subfolder'))
	except Exception as e:
		log.error(e)

if __name__ == "__main__":
	main()