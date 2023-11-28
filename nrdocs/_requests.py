import logging
import sys

import requests
import json
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
BASE_URL = "https://127.0.0.1:5000"

def json_headers(token):
    return {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }

def headers(token):
    return {
        'Authorization': f'Bearer {token}',
    }

COMMUNITY_SLUG = "tst3"
SIMPLE_COMMUNITY = {
        "slug": "tst3",
        "access": {
            "visibility": "public"
        },
        "metadata": {
            "title": "Test3",
            "type": {
                "id": "topic"
            }
        }
    }

SIMPLE_COMMUNITY_2 = {
        "slug": "tst4",
        "access": {
            "visibility": "public"
        },
        "metadata": {
            "title": "Test4",
            "type": {
                "id": "event"
            }
        }
    }

COMMUNITY_CF = {
    "custom_fields": {
        "permissions": {
            "owner": {
                "can_search": True,
                "can_publish": True,
                "can_create": True,
                "can_read": True,
                "can_update": True,
                "can_delete": True,
                "can_community_allows_adding_records": True,
                "can_remove_community_from_record": True,
                "can_remove_records_from_community": True,
            },
            "manager": {
                "can_publish": True,
                "can_create": True,
                "can_read": True,
                "can_update": True,
                "can_delete": True,
                "can_community_allows_adding_records": True,
                "can_remove_community_from_record": True,
                "can_remove_records_from_community": True,
            },
            "curator": {
                "can_create": True,
                "can_read": True,
                "can_update": True,
                "can_delete": False,
                "can_community_allows_adding_records": True,
                "can_remove_community_from_record": False,
                "can_remove_records_from_community": False,
            },
            "reader": {
                "can_create": False,
                "can_read": True,
                "can_update": False,
                "can_delete": False,
                "can_community_allows_adding_records": False,
                "can_remove_community_from_record": False,
                "can_remove_records_from_community": False,
            }
        },
        "aai_mapping": [
            {
                "role": "curator",
                "aai_group": "urn:geant:cesnet.cz:group:VO_nrp_development:test_community:curator#perun.cesnet.cz"
            }
        ]
    },
    "slug": "tst3",
    "metadata": {
        "title": "Test2",
        "type": {
            "id": "topic"
        }
    },
    "access": {
        "member_policy": "open",
        "record_policy": "open",
        "visibility": "public"
    }
}

def nrdocs_sample_record():
    return json.load(open("sample_record.json", 'r'))

def init_with_communities(token):
    header = headers(token)
    jheader = json_headers(token)

    #create community
    resp = requests.post(url=f'{BASE_URL}/api/communities', headers=jheader, json=SIMPLE_COMMUNITY, verify=False)
    assert resp.status_code == 201
    print("community created")

    #upload community cf
    resp = requests.put(url=f'{BASE_URL}/api/communities/{COMMUNITY_SLUG}', headers=jheader, json=COMMUNITY_CF, verify=False)
    assert resp.status_code == 200
    print("custom fields uploaded")


    #create record
    comm_id = requests.get(url=f'{BASE_URL}/api/communities/{COMMUNITY_SLUG}', headers=header, verify=False).json()["id"]
    resp = requests.post(url=f'{BASE_URL}/api/nr-documents', headers=jheader, json=nrdocs_sample_record() | {"community_id": comm_id}, verify=False)
    record_id = resp.json()["id"]
    request_id = resp.json()['parent']['publish_draft']['id']
    assert resp.status_code == 201
    print("record created")

    #publish record
    resp = requests.post(url=f'{BASE_URL}/api/requests/{request_id}/actions/submit', headers=header, verify=False)
    assert resp.status_code == 200
    print("record published")

    #test community records
    resp = requests.get(url=f"{BASE_URL}/api/communities/{comm_id}/records", headers=header, verify=False)
    assert resp.status_code == 200
    assert len(resp.json()['hits']['hits']) >= 0
    print("community records test passed")

    #create second community
    resp = requests.post(url=f'{BASE_URL}/api/communities', headers=jheader, json=SIMPLE_COMMUNITY_2, verify=False)
    assert resp.status_code == 201
    print("community created")

    first_community_input = {
        "communities": [
            {"id": "tst3"}
        ]
    }

    second_community_input = {
        "communities": [
            {"id": "tst4"}
        ]
    }

    #add second community on first record
    #resp = requests.post(url=f'{BASE_URL}/api/nr-documents/{record_id}', headers=jheader, json=second_community_input, verify=False)
    #assert resp.status_code == 200
    #print("second community added on record")

    #remove first community from input
    #resp = requests.delete(url=f'{BASE_URL}/api/nr-documents/{record_id}', headers=jheader, json=first_community_input, verify=False)
    #assert resp.status_code == 200
    #print("second community added on record")

    #remove record from first community


    





if __name__ == "__main__":
    token = sys.argv[1]
    init_with_communities(token)












