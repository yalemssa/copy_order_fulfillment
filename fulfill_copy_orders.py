#/usr/bin/python3

import os
import preservica_file_picker
import package_files
import create_shared_links
import generate_email_template
import clean_directories
import send_notifications

import copy_order_logging

'''
Combined copy order fulfillment scripts.

'''

#os.chdir(os.path.dirname(__file__))
log = copy_order_logging.get_logger(__name__)

def job_runner(results=False):
	try:
		log.debug('Picking files from Preservica...')
		preservica_file_picker.main()
		log.debug('Packaging files into .zips...')
		package_files.main()
		log.debug('Uploading to Box, creating shared links...')
		create_shared_links.main()
		# Note - if there is an error above the rest of this won't run; i.e. if there is already a link in Box,
		# which is the most common error that is encountered by the script. Should really add more error handling into
		# the Box script
		log.debug('Generating email templates...')
		generate_email_template.main()
		log.debug('Cleaning directories...')
		clean_directories.main()
		results = True
	except Exception as e:
		log.error(e)
	finally:
		send_notifications.main(success=results)


if __name__ == "__main__":
	job_runner()