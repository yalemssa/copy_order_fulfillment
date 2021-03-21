#!/usr/bin/python3


def email_template(order_number, box_link, sender_name):
	return f'''
	Your Yale Manuscripts & Archives Digital Duplication request {order_number} is now complete. The resulting digital files have been shared with you by the Yale Box service. Use the following link to download the files, and save them locally to your computer: {box_link}.
	 
	Please note that the files will stay on the Yale server for only 10 days, and that you should download it as soon as possible. If you have any problem retrieving the file, please email mssa.assist@yale.edu for assistance.
	                                       	
	Best Regards,

	{sender_name}
	Manuscripts and Archives
	Yale University Library
	'''

def main():
	# open the Aeon report
	# Fill out the template
	# Write to a text file(s)
	pass


if __name__ == "__main__":
	main()