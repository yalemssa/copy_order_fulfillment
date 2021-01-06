#/usr/bin/python3

import csv
from datetime import datetime
#from functools import partial
import json
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

    def send_request(self, master_task, csv_row):
        try:
            headers = {'Preservica-Access-Token': self.token}
            url = csv_row['direct_download_link']
            file_size = csv_row['size_in_bytes']
            '''See https://2.python-requests.org/en/master/user/advanced/#body-content-workflow
            #for more info on how streaming works; basically only downloads the thing until you
            access the "content" attribute. THe 'get' call downloads the response headers only

            Also either need to call close on the request or put it in the context manager i.e.
            what I did below
            '''
            with self.session.get(url, headers=headers, stream=True) as req:
                #resets the bar for each new download; how will this work with multiprocessing?
                #possibly each processor will have it's own bar, which is fine because 
                #the overall bar will display properly
                if req.status_code == 200:
                    try:
                        filename = self.get_filename(req.headers)
                        #print(filename)
                        download_task = progress.add_task("download", filename=filename, start=False)
                        #print('Task added')
                        #print(download_task)
                        progress.update(download_task, total=int(file_size))
                        progress.start_task(download_task)
                        with open(f"{self.dirpath}/{filename}", 'wb') as outfile:
                            for chunk in req.iter_content(1024):
                                #progress.advance(download_task, len(chunk))
                                progress.update(download_task, advance=len(chunk))
                                #not at all sure this will work...what about yielding it?????????
                                #then will have output for the process results function rather
                                #than passing.
                                #could I yield the chunk here? how will it know what outfile to write to?
                                outfile.write(chunk)
                                #yield chunk
                            #self.process_results(chunk, filename)
                        progress.advance(master_task, int(file_size))
                    except Exception:
                        console.print_exception()
                        #print(traceback.format_exc())
                if req.status_code == 404:
                    #what happens here in terms of the progress bar?
                    #it doesn't create one, but what happens?
                    console.log(f'[bold red]{url}: {req.status_code}[/bold red]')
                    return '404 NOT FOUND'
                elif req.status_code == 401:
                    #same question as above
                    self.token = self.__token__()
                    return self.send_request(url, file_size)
                else:
                    #also...
                    return f'SOME ERROR: {req.status_code}'
        except Exception:
            #console.log(traceback.format_exc())
            console.print_exception()
            #return f'SOME ERROR: {traceback.format_exc()}'

    def download_file(self, download_task, master_task, csv_row):
        #the identifiers are in the first and only row of the CSV
        preservica_uri = csv_row['direct_download_link']
        file_size = csv_row['size_in_bytes']
        self.send_request(preservica_uri, file_size)
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
        #skips first 2 rows of CSV file with weird header
        for i in range(3):
            next(infile)
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
    console.save_text('console_output.txt')

def run_multiprocess(client, csvfile, chunks, rowcount):
	with progress:
	    with Pool() as pool:
	        #HAVE TO HAVE THIS IN THE LOOP OR IT DOESNT WORK
	        #maybe can define the master task here?
	        #master_task = progress.add_task("overall", total=total_file_size)
	        for _ in pool.imap_unordered(client.download_file, csvfile, chunksize=chunks):
	            pass
	            #progress.advance(master_task, len(data))
	            #client.process_results(data, filename)

def run_thread_pool_executor(client, csvfile, total_file_size):
    master_task = progress.add_task("overall", total=total_file_size, filename="Overall Progress")
    with progress:
        #print('This is happening')
        with ThreadPoolExecutor(max_workers=4) as pool:
            try:
                #print('Is this happening?')
                for row in csvfile:
                    #print('what seems to be the problem?')
                    #download_task = progress.add_task("download", start=False)
                    pool.submit(client.send_request, master_task, row)
            except Exception:
                console.print_exception()

def get_total_file_size(input_csv):
    '''Gets the total file size of the files to be downloaded.
    NOTE: using this requires using the report from AS, which
    limits utility for downloading Preservation manifestations,
    since that data will not be in AS. BUT it wopuld be in any report
    that I run for folks'''
    #master_task = 
    with open(input_csv, encoding='utf8') as csvfile:
        csv_reader = csv.reader(csvfile)
        #skips the 
        for _ in range(4):
            next(csv_reader)
        return sum(int(row[5]) for row in csv_reader)


def main():
    welcome()
    cfg = json.load(open('config.json'))
    csvfile, rowcount, input_csv = opencsvdict(cfg.get('input_csv'))
    total_file_size = get_total_file_size(input_csv)
    #chunks = int(rowcount/os.cpu_count())
    #download_task = progress.add_task("download", start=False)
    try:
        client = PreservicaDownloader(configure(cfg, 'output_folder'), configure(cfg, 'preservica_username'), configure_password(cfg), configure(cfg, 'tenant'), configure(cfg, 'preservica_api_url'))
        #run_multiprocess(client, csvfile, chunks, rowcount)
        run_thread_pool_executor(client, csvfile, total_file_size)
    except (KeyboardInterrupt, SystemExit):
        console.print('[bold red]Aborted![/bold red]')
    except Exception:
        console.print_exception()
        console.log(traceback.format_exc())
    finally:
        wrap_up()
        


if __name__ == "__main__":
    main()



