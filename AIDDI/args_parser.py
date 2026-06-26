# args_parser.py
import os
import argparse
from dotenv import load_dotenv


def parse_args():
    # Create the parser and add arguments
    parser = argparse.ArgumentParser(description='Load a specific .env file.', add_help=False)
    parser.add_argument('-e', '--envfile', default='.env', help='the .env file to load')
    parser.add_argument('-h', '--help', action='store_true', help='Show this help message and exit')

    # Parse the arguments
    args = parser.parse_args()

    # If help argument is passed, print help text and exit
    if args.help:
        print("""
        This script loads environment variables from a .env file.

        Usage:
        python your_script.py --envfile .env

        Options:
        -e, --envfile: Specify the .env file to load. If not provided, the default .env file will be loaded.
        """)
        exit()

    # Load the .env file
    load_dotenv(os.path.join(os.getcwd(), args.envfile))
