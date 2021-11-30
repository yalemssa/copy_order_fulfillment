#/usr/bin/python3

from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import sys
import traceback

from boxsdk import Client, JWTAuth
import requests

import get_spreadsheet_data as gsd

import copy_order_logging


'''Uploads files to Box
   Creates a shared, expiring link in Box
   Creates a report for sending Aeon emails, using shared link data and data from Google sheets
   Deletes all expired files
   Logs current files in directory
   '''

log = copy_order_logging.get_logger(__name__)

class BoxClient():
	def __init__(self, config):
		self.config = config
		self.path_to_files = self.config.get('box_path_to_files')
		self.box_folder_id = self.config.get('box_folder_id')
		self.link_output = self.config.get('link_file')
		self.sheet_header, self.sheet_data = gsd.create_aeon_report(self.config)
		self.expiration_date = get_expiration_date()
		self.client = self.authenticate()

	def authenticate(self):
		config = JWTAuth.from_settings_file('config/jwtconfig.json')
		return Client(config)

	def upload_file_process(self, zipped_file, new_file=None):
		file_path = f"{self.path_to_files}/{zipped_file}"
		file_size = Path(file_path).stat().st_size
		try:
			if file_size > 50000000:
				# Box docs recommend using chunked uploader for files greater than 50MB
				try:
					chunked_uploader = self.client.folder(self.box_folder_id).get_chunked_uploader(f"{self.path_to_files}/{zipped_file}")
					new_file = chunked_uploader.start()
				except Exception as e:
					log.error(e)
			else:
				# If less tha 50MB, just upload the file
				new_file = self.client.folder(self.box_folder_id).upload(f"{self.path_to_files}/{zipped_file}")
			if new_file:
				get_shared_link = self.share_file(new_file.id)
				log.debug(f"{zipped_file} {file_size} {get_shared_link}")
				return (zipped_file, get_shared_link)
		except BrokenPipeError:
			log.error('BrokenPipeError')
			log.debug('Trying again...')
			self.upload_file_process(zipped_file)
		except Exception as e:
			log.debug(file_path)
			log.error(e)
			raise e

	def upload_files(self):
		'''Upload a .zip file from'''
		file_list = os.listdir(self.path_to_files)
		current_date = str(datetime.now()).split(' ')[0]
		with open(f'{self.link_output}_{current_date}.csv', 'a', encoding='utf-8') as link_file:
			csvin = csv.writer(link_file)
			csvin.writerow(self.sheet_header)
			futures = []
			with ThreadPoolExecutor(max_workers=8) as pool:
				for zipped_file in file_list:
					if zipped_file != ".DS_Store":
						future = pool.submit(self.upload_file_process, zipped_file)
						futures.append(future)
			for future in futures:
				zipped_file, shared_link = future.result()
				self.write_report(zipped_file, shared_link, csvin)

	def share_file(self, file_id):
		'''Create a public link that expires after 10 days'''
		return self.client.file(file_id).get_shared_link(access='open', allow_download=True, unshared_at=self.expiration_date)

	def write_report(self, zipped_file, shared_link, csvin):
		for row in self.sheet_data:
			invoice_number = row[3]
			if invoice_number in zipped_file:
				row.insert(4, shared_link)
				csvin.writerow(row)

	def delete_expired_links(self):
		'''Deletes expired links'''
		log.debug("Deleting expired links...")
		items = self.client.folder(self.box_folder_id).get_items(fields=['name', 'id', 'created_at', 'shared_link'])
		for item in items:
			try:
				if not item.shared_link:
					log.debug(f"Expired link, deleting file: {item.id} {item.name} {item.created_at}")
					self.client.file(item.id).delete()
				else:
					log.debug(f"Active link, skipping file: {item.id} {item.name}")
			except Exception as e:
				log.debug(f'Error on {item}')
				log.error(e)
				continue

	def delete_selected_files(self):
		log.debug("Deleting files...")
		items = self.client.folder(self.box_folder_id).get_items(fields=['name', 'id', 'created_at', 'shared_link'])
		for item in items:
			try:
				if item.name in ('WillSoper-3082.zip', 'TrencherAdam-3081.zip', 'ElihuRubin-3059a.zip', 'KenHughes-3083.zip', 'LisaWoodward-3079.zip', 'lynchKelly-3080.zip'):
					log.debug(f"Deleting file: {item.id} {item.name} {item.created_at}")
					self.client.file(item.id).delete()
				else:
					log.debug(f"Skipping file: {item.id} {item.name}")
			except Exception as e:
				log.debug(f'Error on {item}')
				log.error(e)
				continue			

	def get_folder_listing(self):
		log.debug("Getting current folder listing")
		items = self.client.folder(self.box_folder_id).get_items(fields=['name', 'id', 'created_at', 'shared_link'])
		for item in items:
			log.debug(f"{item.id} {item.name} {item.created_at} {item.shared_link}")

def get_expiration_date():
	current_date = datetime.now()
	t_delta = timedelta(days=11)
	future_date = str(current_date + t_delta)
	return f"{future_date.partition(' ')[0]}T00:00:00"


def main():
	cfg = json.load(open('config/config.json'))
	box = BoxClient(cfg)
	box.upload_files()
	#box.delete_expired_links()
	#box.delete_selected_files()
	box.get_folder_listing()

if __name__ == "__main__":
	main()
