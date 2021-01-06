#/usr/bin/python3

from datetime import datetime, timedelta
import os
import sys
from boxsdk import Client, OAuth2


'''Uploads files to Box
   Creates a shared, expiring link in Box
   '''

class BoxClient():
	def __init__(self, config):
		#move all of this to a config in production
		self.config = json.load(open('config.json'))
		self.token = self.config.get('box_token')
		self.client_id = self.config.get('box_client_id')
		self.client_secret = self.config.get('box_client_secret')
		self.path_to_files = self.config.get('box_path_to_filees')
		self.box_folder_id = self.config.get('box_folder_id')
		self.expiration_date = get_expiration_date()
		self.client = self.authenticate()

	# this will not work until the app is authenticated by the enterprise admin -
	# still need to determine whether I should use the JWT or the limited 
	# access app - all I need to do is be able to upload files, create and
	# share expirable download links publicly, and delete files
	# def authenticate_jwt(self):
	# 	config = JWTAuth.from_settings_file('jwtconfig.json')
	# 	return Client(config)

	def authenticate(self):
		#this is for dev only. Waiting for authorization for app token authentication
		auth = OAuth2(client_id=self.client_id, client_secret=self.client_secret, access_token=self.token)
		return Client(auth)

	def upload_files(self):
		'''Upload a .zip file from'''
		file_list = os.listdir(self.path_to_files)
		for zipped_file in file_list:
			file_size = sys.getsizeof(f"{self.path_to_files}/{zipped_file}")
			if file_size > 50000000:
				pass
				#upload_session = client.folder(self.box_folder_id).create_upload_session(file_size, zipped_file)
				#upload part of a filee
				#close seession and create file from uploaded chunks
			else:
				#just upload the file
				new_file = self.client.folder(self.box_folder_id).upload(f"{self.path_to_files}/{zipped_file}")
				get_shared_link = self.share_file(new_file.id)
				print(get_shared_link)

	def share_file(self, file_id):
		'''Create a public link that expires after 10 days'''
		return self.client.file(file_id).get_shared_link(access='open', allow_download=True, unshared_at=self.expiration_date)

	def delete_file(self):
		'''Delete files that are older than 10 days'''
		pass

def test_get_shared_link(box):
	file_id = '760778908915'
	shared_link = box.client.file(file_id).get_shared_link_download_url()
	print(shared_link)

def get_expiration_date():
	current_date = datetime.now()
	t_delta = timedelta(days=11)
	future_date = str(current_date + t_delta)
	return f"{future_date.partition(' ')[0]}T00:00:00"

def main():
	box = BoxClient()
	box.upload_files()

if __name__ == "__main__":
	main()
