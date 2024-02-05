import json


def authorization_header(token):
    return {
        'Authorization': f'Bearer {token}'
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
