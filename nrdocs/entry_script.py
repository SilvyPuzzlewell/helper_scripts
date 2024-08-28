import sys
from pathlib import Path

import urllib3
import argparse
import glob
from nrdocs import new_with_requests, mbdb, communities, workflows

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


import importlib

def current_function():
    return workflows.script

def read_tokens():
    path = Path(__file__).parent.parent
    token_files = glob.glob(f"{str(path)}/current_token_*")
    token_files.sort()
    ret = []
    for file in token_files:
        ret.append(str(open(file, 'r').read()).replace("\n", ""))
    return ret

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
    tokens = read_tokens()
    # Call the function if it exists
    if callable(function_to_call):
        function_to_call(*tokens, *sys.argv[1:])