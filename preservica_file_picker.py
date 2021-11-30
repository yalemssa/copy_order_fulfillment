 #/usr/bin/python3

import csv
from datetime import datetime
#from functools import partial
import json
from lxml import etree
import os
import sys
import traceback
#from multiprocessing import Pool
from concurrent.futures import ThreadPoolExecutor

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

log = copy_order_logging.get_logger(__name__)

class PreservicaDownloader():
    def __init__(self, dirpath, username, pw, tenant, api_url):
        self.dirpath = dirpath
        self.username = username
        self.pw = pw
        self.tenant = tenant
        self.api_url = api_url
        self.session = requests.Session()
        self.token = self.__token__()
        
    def __token__(self):
        response = requests.post(f'https://{self.api_url}accesstoken/login?username={self.username}&password={self.pw}&tenant={self.tenant}')
        if response.status_code == 200:
            console.log('[bold green]Connected.[/bold green]')
            return response.json()['token']
        else:
            console.log(f"[bold red]Get new token failed with error code: {response.status_code}[/bold red]")
            console.log(response.request.url)
            raise SystemExit

    def get_security_code(self, url, headers):
        xml_data = self.session.get(url, headers=headers)
        tree = etree.fromstring(bytes(xml_data.text, encoding='utf8'))
        return tree.find(".//{http://www.tessella.com/XIP/v4}DeliverableUnits/{http://www.tessella.com/XIP/v4}DeliverableUnit/{http://www.tessella.com/XIP/v4}SecurityTag").text

    def send_request(self, csv_row, master_task, directory_path, try_number=0):
        try:
            headers = {'Preservica-Access-Token': self.token}
            url = csv_row['direct_download_link']
            file_size = csv_row['size_in_bytes']
            filename = csv_row['filename'].replace('(*)', '')
            deliverable_unit = f"https://preservica.library.yale.edu/api/entity/deliverableUnits/{csv_row['deliverable_unit']}"
            #print(file_size)
            '''See https://2.python-requests.org/en/master/user/advanced/#body-content-workflow
            #for more info on how streaming works; basically only downloads the thing until you
            access the "content" attribute. THe 'get' call downloads the response headers only

            Also either need to call close on the request or put it in the context manager i.e.
            what I did below
            '''
            security_code = self.get_security_code(deliverable_unit, headers)
            if "CLOSED" in security_code:
                # this is fine for now, since I am still running the scripts
                filename = f"RESTRICTED_{filename}"
                #console.print(filename)
                log.debug(filename)
            with self.session.get(url, headers=headers, stream=True) as req:
                #resets the bar for each new download; how will this work with multiprocessing?
                #possibly each processor will have it's own bar, which is fine because 
                #the overall bar will display properly
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
def opencsvdict(input_csv=None):
    """Opens a CSV in DictReader mode."""
    try:
        if input_csv is None:
            input_csv = console.input('[#6c99bb]Please enter path to input CSV file: [/#6c99bb]')
        if input_csv in ('quit', 'Q', 'Quit'):
            raise SystemExit
        infile = open(input_csv, 'r', encoding='utf-8')
        #DON'T USE THIS YET
        #skips first 2 rows of CSV file with weird header
        for i in range(3):
            next(infile)
        #rowcount = sum(1 for line in open(input_csv).readlines()) - 1
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

def get_total_file_size(input_files, input_directory):
    '''Gets the total file size of the files to be downloaded.
    NOTE: using this requires using the report from AS, which
    limits utility for downloading Preservation manifestations,
    since that data will not be in AS. BUT it wopuld be in any report
    that I run for folks'''
    #master_task = 
    total_size_combo = []
    for filename in input_files:
        with open(f"{input_directory}/{filename}", encoding='utf8') as csvfile:
            if filename != '.DS_Store':
                # print(filename)
                csv_reader = csv.reader(csvfile)
                next(csv_reader)
                #skips the first few rows
                for _ in range(4):
                    next(csv_reader)
                total_size = sum(int(row[6]) for row in csv_reader if row[0] != '')
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
        client = PreservicaDownloader(configure(cfg, 'output_folder'), configure(cfg, 'preservica_username'), configure_password(cfg), configure(cfg, 'tenant'), configure(cfg, 'preservica_api_url'))
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



