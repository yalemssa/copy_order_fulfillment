# MSSA Copy Order Fulfillment

Scripts to support an MSSA workflow for fulfilling copy orders for already-digitized materials.

## What's included

* `preservica_file_picker.py`: a lightweight Python console application to download files from Preservica.
* `package_files.py`: Packages folders into a .zip archive file
* `create_shared_links.py`: uploads .zip files to Yale Box, creates a shared public link which expires after 10 days
* `constants.py`: utility file to hold console app styling data
* `config.json`: user config settings

## Proposed workflow

1. Public Services staff receive a request from a researcher for digitized materials
2. Public Services staff ensures customer is registered in Aeon and signs the user agreement
3. Public Services staff fill out tracking spreadsheet and create Quickbooks order
4. Public Services staff run the ‘Preservica Access Copy Links’ [report](https://github.com/YaleArchivesSpace/yale-archivesspace-reports/blob/add_report/backend/model/digital_object_preservica_links.rb) in the ArchivesSpace staff interface to retrieve all Preservica digital content links for a given collection
5. Public services staff review the report and delete any files/rows that should **NOT** be downloaded and sent to the patron
6. Public services staff save the CSV file as a new file into a “hot folder” on a network drive; the file should be named with the collection call number, patron’s last name and order number separated by hyphens (i.e. ms116-customerlastname-ordernumber.csv)
7. At the end of each day a script runs from an MSSA/YAMS server which zips and shares the files via an expiring Yale Box link
8. **TBD**: process for sending an email with the Yale Box link to the patron

