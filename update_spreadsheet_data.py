#!/usr/bin/python3

import get_spreadsheet_data as gsd

def main():
	cfg = json.load(open('config/config.json', 'r', encoding='utf-8'))
	update_data(cfg)


if __name__ == "__main__":
	main()
