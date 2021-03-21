#!/usr/bin/python3

import csv
import json

def email_template(order_number, patron_name, box_link, sender_name):
	return f'''Dear {patron_name[1]} {patron_name[0]},\n\nYour Yale Manuscripts & Archives Digital Duplication request {order_number} is now complete. The resulting digital files have been shared with you by the Yale Box service. Use the following link to download the files, and save them locally to your computer: {box_link}.\n\nPlease note that the files will stay on the Yale server for only 10 days, and that you should download it as soon as possible. If you have any problem retrieving the file, please email mssa.assist@yale.edu for assistance.\n\nBest Regards,\n\n{sender_name}\nManuscripts and Archives\nYale University Library'''

def main():
	cfg = json.load(open('config/config.json', 'r', encoding='utf8'))
	sender_name = cfg.get('aeon_sender')
	with open('data/orders/shared_link_report.csv') as csvin:
		shared_links = csv.reader(csvin)
		next(shared_links)
		for row in shared_links:
			patron_name = row[1].split(', ')
			print(patron_name)
			invoice_number = row[3]
			box_link = row[4]
			template = email_template(invoice_number, patron_name, box_link, sender_name)
			with open(f'data/emails/to_send/{invoice_number}.txt', 'a', encoding='utf-8') as ofile:
				ofile.write(template)

if __name__ == "__main__":
	main()