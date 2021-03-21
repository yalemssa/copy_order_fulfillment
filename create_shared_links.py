#/usr/bin/python3

from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import sys
import traceback

from boxsdk import Client, OAuth2
import requests

import get_spreadsheet_data as gsd


'''Uploads files to Box
   Creates a shared, expiring link in Box
   Creates a report for sending Aeon emails, using shared link data and data from Google sheets
   '''

class BoxClient():
	def __init__(self, config):
		self.config = config
		self.token = self.config.get('box_token')
		#self.token = self.get_token()
		self.client_id = self.config.get('box_client_id')
		self.client_secret = self.config.get('box_client_secret')
		self.path_to_files = self.config.get('box_path_to_files')
		self.box_folder_id = self.config.get('box_folder_id')
		self.box_subject_id = self.config.get('box_subject_id')
		self.link_output = self.config.get('link_file')
		self.sheet_header, self.sheet_data = gsd.create_aeon_report(self.config)
		self.expiration_date = get_expiration_date()
		self.client = self.authenticate()

	def get_token(self):
		params = {'client_id': self.client_id, 'client_secret': self.client_secret, 'grant_type': 'client_credentials', 'box_subject_id': self.box_subject_id, 'box_subject_type': 'enterprise'}
		headers = {'Content-Type': 'application/x-www-form-urlencoded'}
		return requests.post('https://api.box.com/oauth2/token', headers=headers , data=params).json()

	def authenticate(self):
		auth = OAuth2(client_id=self.client_id, client_secret=self.client_secret, access_token = self.token)
		return Client(auth)

	def upload_file_process(self, zipped_file):
		file_size = Path(f"{self.path_to_files}/{zipped_file}").stat().st_size
		if file_size > 50000000:
			# Box docs recommend using chunked uploader for files greater than 50MB
			try:
				chunked_uploader = self.client.folder(self.box_folder_id).get_chunked_uploader(f"{self.path_to_files}/{zipped_file}")
				new_file = chunked_uploader.start()
			except Exception:
				print(traceback.format_exc())
		else:
			# If less tha 50MB, just upload the file
			new_file = self.client.folder(self.box_folder_id).upload(f"{self.path_to_files}/{zipped_file}")
		get_shared_link = self.share_file(new_file.id)
		print(zipped_file, file_size)
		return (zipped_file, get_shared_link)

	def upload_files(self):
		'''Upload a .zip file from'''
		file_list = os.listdir(self.path_to_files)
		with open(self.link_output, 'a', encoding='utf-8') as link_file:
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

	# def delete_file(self):
	# 	'''Delete files that are older than 10 days'''
	# 	pass

# def test_get_shared_link(box):
# 	file_id = '760778908915'
# 	shared_link = box.client.file(file_id).get_shared_link_download_url()
# 	print(shared_link)

def get_expiration_date():
	current_date = datetime.now()
	t_delta = timedelta(days=11)
	future_date = str(current_date + t_delta)
	return f"{future_date.partition(' ')[0]}T00:00:00"


def main():
	cfg = json.load(open('config/config.json'))
	box = BoxClient(cfg)
	box.upload_files()

if __name__ == "__main__":
	main()
