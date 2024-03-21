import json


def authorization_header(token):
    return {
        'Authorization': f'Bearer {token}'
    }

def file_content_header():
    return {
        'Content-Type': 'application/octet-stream'
    }

def ui_serialization_header():
    return {
        'Accept': 'application/vnd.inveniordm.v1+json'
    }

def nrdocs_sample_record():
    return json.load(open("sample_record.json", 'r'))

def nrdocs_sample_metadata():
    return json.load(open("sample_record.json", 'r'))["metadata"]
BASE_URL = "https://127.0.0.1:5000"


def mbdb_sample_metadata():
    return {
        "bli": json.load(open("/home/ron/prace/mbdb-app/sample_data/bli/BLI.json", 'r')),
        "mst": json.load(open("/home/ron/prace/mbdb-app/sample_data/mst/MST.json", 'r')),
        "spr": json.load(open("/home/ron/prace/mbdb-app/sample_data/spr/SPR.json", 'r')),
    }
