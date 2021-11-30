#!/usr/bin/python3

import csv
from datetime import datetime
import json
import copy_order_logging

log = copy_order_logging.get_logger(__name__)

def todays_date():
	return str(datetime.now()).split(' ')[0]

def email_template(order_number, patron_name, box_link, sender_name):
	return f'''Dear {patron_name[1]} {patron_name[0]},\n\nYour Yale Manuscripts & Archives Digital Duplication request {order_number} is now complete. The resulting digital files have been shared with you by the Yale Box service. Use the following link to download the files, and save them locally to your computer: {box_link}.\n\nPlease note that the files will stay on the Yale server for only 10 days, and that you should download it as soon as possible. If you have any problem retrieving the file, please email mssa.assist@yale.edu for assistance.\n\nBest Regards,\n\n{sender_name}\nManuscripts and Archives\nYale University Library'''

def main():
	try:
		cfg = json.load(open('config/config.json', 'r', encoding='utf8'))
		sender_name = cfg.get('aeon_sender')
		network_drive = cfg.get('network_drive')
		fp = f"{network_drive}/orders/orders_to_send_{todays_date()}.csv"
		with open(fp) as csvin:
			shared_links = csv.reader(csvin)
			next(shared_links)
			for row in shared_links:
				patron_name = row[1].split(', ')
				log.debug(patron_name)
				invoice_number = row[3]
				box_link = row[4]
				template = email_template(invoice_number, patron_name, box_link, sender_name)
				with open(f'{network_drive}/emails/to_send/{patron_name[0].lower()}{patron_name[1]}-{invoice_number}.txt', 'a', encoding='utf-8') as ofile:
					ofile.write(template)
	except Exception as e:
		log.error(e)

if __name__ == "__main__":
	main()