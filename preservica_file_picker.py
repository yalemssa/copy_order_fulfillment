 #/usr/bin/python3

import csv
from datetime import datetime
#from functools import partial
import json
#from lxml import etree
import xml.etree.ElementTree as ET
import os
import sys
import traceback
#from multiprocessing import Pool
from concurrent.futures import ThreadPoolExecutor
import warnings

import requests
from rich import print
from rich.progress import track
from rich.padding import Padding

from constants import console, progress

import copy_order_logging

'''Script to retrieve metadata from Preservica content API'''

"""TODO
-instead of using number of files use total number of bytes - sum the size_in_bytes column
-not sure if i will be able to track download progress per file - how would that work?
    -possibly by streaming i.e. https://stackoverflow.com/questions/37573483/progress-bar-while-download-file-over-http-with-requests/37573701
    -https://stackoverflow.com/questions/60343944/how-does-requests-stream-true-option-streams-data-one-block-at-a-time
    -https://stackoverflow.com/questions/16694907/download-large-file-in-python-with-requests
    -https://stackoverflow.com/questions/24688479/size-of-raw-response-in-bytes
    -https://stackoverflow.com/questions/57497833/python-requests-stream-data-from-api
        -If we stream we can't get the size in bytes - but that data is in the CSV,
        so should use that....probably will need to add it in the download file function,
        as it takes the CSV row as an argument. So start a new task with the byte size from
        the CSV as the total. Then in have the request stream and as it does add to the
        progress bar. Not sure how this will affect returning the file, since the actual
        writing doesn't happen until later. I don't like that and would rather it
        happeen sooner, but when I was testing the multiprocessing module and put the
        write-to-file portion right after the download filee part it did not work. Had to
        call the process file stuff after the results were in. 


"""

# suppress warnings during testing
warnings.filterwarnings("ignore")
log = copy_order_logging.get_logger(__name__)

class PreservicaDownloader():
    def __init__(self, dirpath, username, pw, api_url):
        self.dirpath = dirpath
        self.username = username
        self.pw = pw
        self.api_url = api_url
        self.session = requests.Session()
        self.token = self.__token__()
        
    # def __token__(self):
    #     response = requests.post(f'https://{self.api_url}accesstoken/login?username={self.username}&password={self.pw}&tenant={self.tenant}')
    #     if response.status_code == 200:
    #         console.log('[bold green]Connected.[/bold green]')
    #         return response.json()['token']
    #     else:
    #         console.log(f"[bold red]Get new token failed with error code: {response.status_code}[/bold red]")
    #         console.log(response.request.url)
    #         raise SystemExit

    def __token__(self):
        response = requests.post(f'https://{self.api_url}accesstoken/login', data=f'username={self.username}&password={self.pw}', headers={'accept': 'application/json', 'Content-Type': 'application/x-www-form-urlencoded'}, verify=False)
        if response.status_code == 200:
            console.log('[bold green]Connected.[/bold green]')
            return {'Preservica-Access-Token': response.json()['token']}
        else:
            console.log(f"[bold red]Get new token failed with error code: {response.status_code}[/bold red]")
            console.log(response.request.url)
            raise SystemExit

    def get_security_code(self, url, headers):
        # this needs to be redone
        xml_data = self.session.get(url, headers=headers)
        tree = etree.fromstring(bytes(xml_data.text, encoding='utf8'))
        return tree.find(".//{http://www.tessella.com/XIP/v4}DeliverableUnits/{http://www.tessella.com/XIP/v4}DeliverableUnit/{http://www.tessella.com/XIP/v4}SecurityTag").text


    def get_bitstream(self, ref):
        content_objects = []
        # Using Access/1 because just doing Access doesn't reliably get what I need. Will continue to keep
        # an eye on things to make sure that 
        req = self.session.get(f"https://{self.api_url}entity/information-objects/{ref}/representations/Access/1", headers=self.token, verify=False)
        if req.status_code == 200:
            # also want to include one with just a single access copy so I can see the dif
            #print(req.text, '\n')
            xml_data = ET.fromstring(req.text)
            content_object_data = xml_data.iter("{http://preservica.com/EntityAPI/v6.5}ContentObject")
            for element in content_object_data:
                #bitstream_url = f"https://{self.api_url}entity/content-objects/{element.attrib.get('ref')}/generations/1/bitstreams/1/content"
                bitstream_url = f"https://{self.api_url}entity/content-objects/{element.attrib.get('ref')}/generations/1/bitstreams/1"
                content_objects.append(bitstream_url)
                # content_objects.append({'info_object_ref': ref, 'content_object_title': element.attrib.get('title'), 'content_object_ref': element.attrib.get('ref'), 'type': element.attrib.get('type'), 'bitstream_url': bitstream_url})
        else:
            # better error handling here
            print(f'Info object not found: {ref}')
            print(f'Error: {req.status_code}')
        return content_objects


    def get_bitstream_metadata(self, urls):
        req = self.session.get(urls[0], headers=self.token)
        if req.status_code == 200:
            metadata = ET.fromstring(req.text)
            filename = metadata.find(".//{http://preservica.com/XIP/v6.5}Bitstream/{http://preservica.com/XIP/v6.5}Filename")
            file_size = metadata.find(".//{http://preservica.com/XIP/v6.5}Bitstream/{http://preservica.com/XIP/v6.5}FileSize")
            # need some better error handling here
            return filename.text, file_size.text
        else:
            print(f'Metadata not found for bitstream {urls[0]}')
            return 0, 0

    def send_request(self, csv_row, master_task, directory_path, try_number=0):
        try:
            # need to make this better - want to know if there are multiple access copies for things - lol
            urls = self.get_bitstream(csv_row['deliverable_unit'])
            filename, file_size = self.get_bitstream_metadata(urls)
            with self.session.get(f"{urls[0]}/content", headers=self.token, stream=True) as req:
                if req.status_code == 200:
                    try:
                        #filename = self.get_filename(req.headers)
                        download_task = progress.add_task("download", filename=filename, start=False)
                        progress.update(download_task, total=int(file_size))
                        progress.start_task(download_task)
                        with open(f"{directory_path}/{filename}", 'wb') as outfile:
                            for chunk in req.iter_content(1024):
                                #progress.advance(download_task, len(chunk))
                                progress.update(download_task, advance=len(chunk))
                                #this works
                                progress.update(master_task, advance=len(chunk))
                                outfile.write(chunk)
                        progress.remove_task(download_task)
                    except Exception as e:
                        log.error(e)
                        console.print_exception()
                if req.status_code == 404:
                    #what happens here in terms of the progress bar?
                    #it doesn't create one, but what happens?
                    console.log(f'[bold red]{url}: {req.status_code}[/bold red]')
                    return '404 NOT FOUND'
                if req.status_code == 502:
                    if try_number > 0 and try_number < 3:
                        console.log(f'Trying again, try number {try_number}')
                        console.log(f'[bold red]{url}: {req.status_code}[/bold red]')
                        return self.send_request(url, csv_row, master_task, try_number=try_number + 1)
                    if try_number > 2:
                        console.log(f'Exceeded 2 tries, skipping record')
                        console.log(f'[bold red]{url}: {req.status_code}[/bold red]')
                        return '502 BAD GATEWAY'
                elif req.status_code == 401:
                    #same question as above
                    self.token = self.__token__()
                    return self.send_request(url, csv_row, master_task)
                else:
                    #also...
                    return f'SOME ERROR: {req.status_code}'
        except Exception as e:
            log.error(e)
            console.print_exception()
            #return f'SOME ERROR: {traceback.format_exc()}'

    # def download_file(self, download_task, master_task, csv_row):
    #     #the identifiers are in the first and only row of the CSV
    #     preservica_uri = csv_row['direct_download_link']
    #     file_size = csv_row['size_in_bytes']
    #     self.send_request(preservica_uri, file_size)
        # if isinstance(data_file, requests.models.Response):
        #     data_content = data_file.content
        #     file_name = self.get_filename(data_file)
        #     return data_content, file_name
        # else:
        #     #LOL don't do this
        #     return preservica_uri, 'ERROR.txt'

    def get_filename(self, file_headers):
        #file_headers = datafile.headers
        return file_headers.get('Content-Disposition').replace('attachment; filename=', '').replace('"', '')

    def process_results(self, datafile, filename):
        with open(f"{self.dirpath}/{filename}", 'wb') as outfile:
            outfile.write(datafile)


def configure(config_file, field):
    if config_file.get(field) != "":
        return config_file.get(field)
    else:
        return console.input(f"[#6c99bb]Please enter the {field}: [/#6c99bb]")

def configure_password(config_file):
    pres_password = config_file.get('preservica_password')
    if pres_password != "":
        return pres_password
    else:
        return console.input(f"[#6c99bb]Please enter your preservica_password: [/#6c99bb]", password=True)

#Open a CSV in dictreader mode
def opencsvdict(input_csv=None, skip_rows=True):
    """Opens a CSV in DictReader mode."""
    try:
        if input_csv is None:
            input_csv = console.input('[#6c99bb]Please enter path to input CSV file: [/#6c99bb]')
        if input_csv in ('quit', 'Q', 'Quit'):
            raise SystemExit
        infile = open(input_csv, 'r', encoding='utf-8')
        if skip_rows:
            for i in range(3):
                next(infile)
            rowcount = sum(1 for line in open(input_csv).readlines()) - 1
        else:
            rowcount = sum(1 for line in open(input_csv).readlines()) - 4
        return csv.DictReader(infile), rowcount, input_csv
    except FileNotFoundError:
        return opencsvdict()

def welcome():
    console.log("[#b05279]Starting...[/#b05279]")
    console.rule()
    console.rule("[color(11)]Hello![/color(11)]")
    console.rule("[color(11)]This is the Preservica File Picker[/color(11)]")
    console.rule()
    console.log("[#b05279]Checking your credentials...[/#b05279]")    
    #THESE DON'T WORK
    #print("Not sure how it works? Click [link=https://github.com/yalemssa]here[/link]")
    #print("Visit my [link=https://www.willmcgugan.com]blog[/link]!")

def wrap_up():
    #link to directory...
    console.rule("[color(11)]Goodbye![/color(11)]")
    console.log("[#b05279]Exiting...[#b05279]")
    #console.save_text('console_output.txt')

def run_thread_pool_executor(pool, client, csvfile, master_task, directory_path):
    try:
        for row in csvfile:
            if row['to_download'] != '':
                pool.submit(client.send_request, row, master_task, directory_path)
    except Exception as e:
        log.error(e)
        console.print_exception()

def get_total_file_size(input_files, input_directory, skip_rows=True):
    '''Gets the total file size of the files to be downloaded.
    NOTE: using this requires using the report from AS, which
    limits utility for downloading Preservation manifestations,
    since that data will not be in AS. BUT it wopuld be in any report
    that I run for folks'''
    #master_task = 

    # Want to start pulling directly from Preservica, so will not need this anymore.
    total_size_combo = []
    for filename in input_files:
        with open(f"{input_directory}/{filename}", encoding='utf8') as csvfile:
            if filename != '.DS_Store':
                # print(filename)
                csv_reader = csv.reader(csvfile)
                next(csv_reader)
                if skip_rows:
                    #skips the first few rows
                    for _ in range(4):
                        next(csv_reader)
                total_size = sum(int(row[6]) for row in csv_reader if (row[0] != '' and row[6].isdigit()))
                total_size_combo.append(total_size)
    return sum(total_size_combo)

def configure_output_dir(config_file, filename):
    output_dir = config_file.get('output_folder')
    subdir = filename.replace('.csv', '')
    full_path = f"{output_dir}/{subdir}"
    if not os.path.exists(full_path):
        os.mkdir(full_path)
    return full_path

def main():
    welcome()
    cfg = json.load(open('config/config.json'))
    input_directory = cfg.get('input_folder')
    input_files = os.listdir(input_directory)
    try:
        client = PreservicaDownloader(configure(cfg, 'output_folder'), configure(cfg, 'preservica_username'), configure_password(cfg), configure(cfg, 'preservica_api_url'))
        # data = testing(client)
        # print(data)
        log.debug('Getting total file size')
        total_file_size = get_total_file_size(input_files, input_directory)
        master_task = progress.add_task("overall", total=total_file_size, filename="Overall Progress")
        with progress:
            with ThreadPoolExecutor(max_workers=8) as pool:
                for filename in input_files:
                    if filename != '.DS_Store':
                        csvfile, rowcount, input_csv = opencsvdict(f"{input_directory}/{filename}")
                        directory_path = configure_output_dir(cfg, filename)
                        run_thread_pool_executor(pool, client, csvfile, master_task, directory_path)
    except (KeyboardInterrupt, SystemExit):
        log.debug('Aborted')
        console.print('[bold red]Aborted![/bold red]')
    except Exception as e:
        console.print_exception()
        log.error(e)
    finally:
        wrap_up()
        


if __name__ == "__main__":
    main()



