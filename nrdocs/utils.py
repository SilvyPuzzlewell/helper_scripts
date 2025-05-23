import json
import requests


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
    return json.load(open("sample_record_affiliations_new.json", 'r'))

def nrdocs_sample_metadata():
    return json.load(open("sample_record_affiliations_new.json", 'r'))["metadata"]

def nrdocs_sample_metadata_custom(filename):
    return json.load(open(filename, 'r'))["metadata"]

def nrdocs_sample_matadata_missing_required_fields():
    return json.load(open("broken_sample_record.json", 'r'))["metadata"]

BASE_URL = "https://127.0.0.1:5000"

def mbdb_sample_metadata():
    return {
        "bli": json.load(open("/home/ron/prace/mbdb-app/sample_data/bli/BLI.json", 'r')),
        "mst": json.load(open("/home/ron/prace/mbdb-app/sample_data/mst/MST.json", 'r')),
        "spr": json.load(open("/home/ron/prace/mbdb-app/sample_data/spr/SPR.json", 'r')),
    }


def _find_request_from_search(search_response, queried_id):
    hits = search_response.json()["hits"]["hits"]
    for hit in hits:
        if hit["id"] == queried_id:
            return hit
    return None

def _find_request_from_search_by_type(search_response, type, topic=None):
    hits = search_response.json()["hits"]["hits"]
    for hit in hits:
        if hit["type"] == type:
            if topic is not None and hit["topic"] == topic:
                return hit
            elif topic is None:
                return hit
    return None

def _find_request_by_type_id(request_types, type_id, custom_key=""):
    for type in request_types:
        if not custom_key:
            if type["type_id"] == type_id:
                return type
        else:
            if type[custom_key] == type_id:
                return type
    return None

def create_request_on_record(applicable_requests, request_type, token, data=None):
    if data:
        request = requests.post(_find_request_by_type_id(applicable_requests, request_type)["links"]["actions"]["create"],
                                    headers=authorization_header(token), json=data, verify=False)
    else:
        request = requests.post(
        _find_request_by_type_id(applicable_requests, request_type)["links"]["actions"]["create"],
        headers=authorization_header(token), json=data, verify=False)
    return request


def upload_file(record_data, token):
    data_json = [
    {
        "metadata": {
            "title": "blabla"
        },
        "key": "file.jpg"
    }
]
    file_path = "file.jpg"
    file = open(file_path, 'rb')
    files = {'file': file}
    initiate_upload = requests.post(record_data["links"]["files"], headers=authorization_header(token), json=data_json, verify=False)
    upload_link = initiate_upload.json()['entries'][0]['links']['content']
    commit_link = initiate_upload.json()['entries'][0]['links']['commit']
    upload = requests.put(upload_link, headers=authorization_header(token)|file_content_header(), files=files, verify=False)
    commit = requests.post(commit_link, headers=authorization_header(token), verify=False)
    response = requests.get(upload_link, stream=True, headers=authorization_header(token), verify=False)
    #response2 = requests.get(response.raw.data.decode('utf-8'), stream=True, headers=authorization_header(token), verify=False)
    #with open('check_img.png', 'wb') as out_file:
    #    shutil.copyfileobj(response.raw, out_file)
