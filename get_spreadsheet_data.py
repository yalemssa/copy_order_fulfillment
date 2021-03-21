#!/usr/bin/python3

import csv
import json
import traceback
import gspread


def get_spreadsheet_data(client, spreadsheet_id):
	# Opens the spreadsheet and returns all values as a list of lists
	sheet = client.open_by_key(spreadsheet_id).sheet1	
	return sheet, sheet.get_all_values()

def get_outstanding_requests_report(spreadsheet_data):
	# Takes the spreadsheet data list and returns just those
	# that have FALSE as the value in column 10.
	# This will be used to compile the report for sending Aeon emails
	header_row = ['request_date', 'patron_name', 'aeon_username', 'invoice_number', 'box_link', 'num_pdfs', 'num_av', 'affiliation']
	outstanding_requests = []
	for row in spreadsheet_data:
		patron_name = row[0]
		aeon_username = row[1]
		request_date = row[2]
		number_pdfs = row[3]
		number_av = row[6]
		invoice_number = row[7]
		affiliation = row[8]
		status = row[9]
		if patron_name != '' and status == 'FALSE' and (number_pdfs != '' or number_av != ''):
			new_row = [request_date, patron_name, aeon_username, invoice_number, number_pdfs, number_av, affiliation]
			outstanding_requests.append(new_row)
	return header_row, outstanding_requests		

def get_outstanding_requests_with_coordinates(spreadsheet_data):
	# Takes the spreadsheet data list and returns a dictionary of all
	# open requests (those with FALSE as the value in column 10), with
	# the request info as the value and the coordinate positions as the key.
	# This will be used for updating the spreadsheet after the requests are sent.
	outstanding_requests = {}
	for row_num, row in enumerate(spreadsheet_data, 1):
		patron_name = row[0]
		aeon_username = row[1]
		request_date = row[2]
		number_pdfs = row[3]
		number_av = row[6]
		invoice_number = row[7]
		affiliation = row[8]
		status = row[9]
		# There are some empty rows, so also check to make sure there is a value in the Patron Name
		# column. Only retrieve unfulfilled requests that are for PDFs or AV items, not for 
		# MADIDs or born-digital files.
		if patron_name != '' and status == 'FALSE' and (number_pdfs != '' or number_av != ''):
			new_row = [request_date, patron_name, aeon_username, invoice_number, number_pdfs, number_av, affiliation]
			outstanding_requests[(row_num, 10)] = new_row
	return outstanding_requests

def update_spreadsheet(spreadsheet_object, spreadsheet_data):
	# Loops through the dictionary of open requests and updates
	# the checkbox.
	for coordinates, values in spreadsheet_data.items():
		spreadsheet_object.update_cell(coordinates[0], coordinates[1], 'TRUE')

def create_aeon_report(cfg):
	spreadsheet_id = cfg.get("spreadsheet_id")
	client = gspread.service_account("config/service_account.json")
	sheet, values = get_spreadsheet_data(client, spreadsheet_id)
	header_row, outstanding_requests = get_outstanding_requests_report(values)
	return header_row, outstanding_requests

def update_data(cfg):
	spreadsheet_id = cfg.get("spreadsheet_id")
	client = gspread.service_account("config/service_account.json")
	sheet, values = get_spreadsheet_data(client, spreadsheet_id)
	outstanding_requests = get_outstanding_requests_with_coordinates(values)
	update_spreadsheet(sheet, outstanding_requests)

def main():
	cfg = json.load(open('config/config.json', 'r', encoding='utf-8'))
	header_row, outstanding_requests = create_aeon_report(cfg)
	# with open('aeon_report.csv', 'a', encoding='utf-8') as csvinfile:
	# 	csvin = csv.writer(csvinfile)
	# 	csvin.writerow(header_row)
	# 	csvin.writerows(outstanding_requests)


if __name__ == "__main__":
	main()


# possible other use case:
# populate a google sheet with data from ArchivesSpace