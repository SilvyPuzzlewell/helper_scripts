import sys
import urllib3
import argparse

from nrdocs import new_with_requests, mbdb

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


import importlib

def current_function():
    return new_with_requests.script

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--module')
    parser.add_argument('--func')

    if hasattr(parser, "module") and hasattr(parser, "func"):
        module = parser.module
        func = parser.func
        module = importlib.import_module(f".{module}", package="nrdocs")
        function_to_call = getattr(module, func)
    else:
        function_to_call = current_function()

    # Call the function if it exists
    if callable(function_to_call):
        function_to_call(*sys.argv[1:])