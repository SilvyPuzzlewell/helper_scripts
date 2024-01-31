import sys
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


import importlib

if __name__ == "__main__":
    module = sys.argv[1]
    func = sys.argv[2]

    module = importlib.import_module(f".{module}", package="nrdocs")
    function_to_call = getattr(module, func)

    # Call the function if it exists
    if callable(function_to_call):
        function_to_call(*sys.argv[3:])