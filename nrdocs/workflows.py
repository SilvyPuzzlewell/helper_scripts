import time
import requests
from nrdocs.repo_requests import create_record, create_record_in_community
from nrdocs.utils import authorization_header, BASE_URL, nrdocs_sample_metadata, _find_request_from_search_by_type, \
    create_request_on_record, upload_file, _find_request_by_type_id

COMMUNITY_DICT = {
        "access": {
            "visibility": "public",
            "record_policy": "open",
        },
        "slug": "praguecommune",
        "metadata": {
            "title": "prague commune",
        },
    }

COMMUNITY_DICT2 = {
        "access": {
            "visibility": "public",
            "record_policy": "open",
        },
        "slug": "pilsencommune",
        "metadata": {
            "title": "pilsen commune",
        },
    }

COMMUNITY_DICT3 = {
        "access": {
            "visibility": "public",
            "record_policy": "open",
        },
        "slug": "brnocommune",
        "metadata": {
            "title": "brno commune",
        },
    }
def invite(user_id, community_id, role, owner_token, reader_token):
    """Add/invite a user to a community with a specific role."""
    invitation_data = {
        "members": [{"type": "user", "id": user_id}],
        "role": role,
        "message": "Welcome to the club!",

    }

    r = requests.get(
        f"{BASE_URL}/api/communities/{community_id}/members",
        headers=authorization_header(owner_token),
        verify=False
    )
    if len(r.json()["hits"]["hits"]) > 1:
        return

    r = requests.post(
        f"{BASE_URL}/api/communities/{community_id}/invitations",
        headers=authorization_header(owner_token),
        json=invitation_data,
        verify=False,
    )
    if not (r.status_code == 400 and r.json()["message"] == 'A member was already added or invited.'):
        assert r.status_code == 204
        time.sleep(5) #index refresh?

    #with app.app_context():
    #    Request.index.refresh()

    reader_requests = requests.get(f"{BASE_URL}/api/user/requests", headers=authorization_header(reader_token), verify=False)
    request = _find_request_from_search_by_type(reader_requests, "community-invitation", topic={'community': community_id})
    accept = requests.post(request["links"]["actions"]["accept"], headers=authorization_header(reader_token), verify=False)
    r = requests.get(
        f"{BASE_URL}/api/communities/{community_id}/members",
        headers=authorization_header(owner_token),
        verify=False
    )
    return r
def publish_request_data(draft_id):
    return {'request_type': 'publish_draft', 'topic': {'documents_draft': draft_id}}

def get_community_from_results(result_response, slug):
    hits = result_response.json()["hits"]["hits"]
    for hit in hits:
        if hit["slug"] == slug:
            return hit
    return None
def create_community(creator_token, community_dict=None):
    if not community_dict:
        community_dict = COMMUNITY_DICT
    user_communities = requests.get(f"{BASE_URL}/api/user/communities", headers=authorization_header(creator_token), verify=False)
    existing_comm = get_community_from_results(user_communities, community_dict["slug"])
    if not existing_comm:
        comm = requests.post(f"{BASE_URL}/api/communities", headers=authorization_header(creator_token), json=community_dict, verify=False).json()
    else:
        comm = existing_comm
    comm = comm | {"custom_fields": {"workflow": "default"}}
    result = requests.put(f"{BASE_URL}/api/communities/{comm['id']}",
                  headers=authorization_header(creator_token), json=comm, verify=False)
    return comm

def invite_reader():
    """"""

def do_request(receiver_token, creator_token, record_id, type, payload=None, is_draft=False, create_forbidden=False):
    record_url = f"{BASE_URL}/api/docs/{record_id}/draft?expand=true" if is_draft else f"{BASE_URL}/api/docs/{record_id}?expand=true"
    record_resp = requests.get(record_url, headers=authorization_header(creator_token), verify=False)
    #todo CommunityAlreadyIncludedException should throw 500 (400 instead)??
    if create_forbidden:
        request = _find_request_by_type_id(record_resp.json()["expanded"]["request_types"], type)
        assert request is None
        return
    request = create_request_on_record(record_resp, type, creator_token, data=payload)
    assert request.status_code == 201
    submit = requests.post(request.json()["links"]["actions"]["submit"],
                           headers=authorization_header(creator_token), verify=False)
    assert submit.status_code == 200
    # todo permissions specifically for request receiver
    request_receiver = requests.get(f"{BASE_URL}/api/requests/{submit.json()['id']}", headers=authorization_header(receiver_token), verify=False)
    accept = requests.post(request_receiver.json()["links"]["actions"]["accept"],
                           headers=authorization_header(receiver_token), verify=False)
    assert accept.status_code == 200

def change_workflow_test(token, community_id, community_data):
    result_default = requests.put(f"{BASE_URL}/api/communities/{community_id}", headers=authorization_header(token), json=community_data|{"custom_fields": {"workflow": "default"}}, verify=False)
    result_nonexistent = requests.put(f"{BASE_URL}/api/communities/{community_id}", headers=authorization_header(token),
                          json=community_data | {"custom_fields": {"workflow": "nonexistent"}}, verify=False)
    # todo handling nonexisting workflows, endpoint to get workflow
    #non_existing_workflow_create = create_record_in_community(BASE_URL, sample_record, token, community_id, repo="docs")
    #assert non_existing_workflow_create.status_code == 400
    #backchange = requests.put(f"{BASE_URL}/api/communities/{community_id}", headers=authorization_header(token), json=community_data["data"]|{"custom_fields": {"workflow": "default"}}, verify=False)
    #r = create_record_in_community(BASE_URL, sample_record, token, community_id, repo="docs")
    assert result_default.status_code == 200
    assert result_nonexistent.status_code == 400
    return

def script(owner_token, curator_token, *args, **kwargs):
    community_id = create_community(owner_token)["id"]
    invite('2', community_id, "curator", owner_token, curator_token)
    community2_id =create_community(owner_token, community_dict=COMMUNITY_DICT2)["id"]
    invite('2', community2_id, "curator", owner_token, curator_token)
    community3_id =create_community(owner_token, community_dict=COMMUNITY_DICT3)["id"]
    invite('2', community3_id, "curator", owner_token, curator_token)

    sample_record = {"metadata": nrdocs_sample_metadata()}

    # create is temporarily auth user
    # test direct create disabled
    resp_record = create_record(BASE_URL, sample_record, owner_token)
    assert resp_record.status_code == 400
    # test direct create in community allowed
    resp_record = create_record(BASE_URL, sample_record|{"parent":{"communities": {"default": community_id}}}, owner_token)
    assert resp_record.status_code == 201

    change_workflow_test(owner_token, community_id, requests.get(f"{BASE_URL}/api/communities/{community_id}", headers=authorization_header(owner_token), verify=False).json())
    resp_record = create_record_in_community(BASE_URL, sample_record, token=curator_token, community_id=community_id, repo="docs")
    assert resp_record.status_code == 201
    do_request(receiver_token=curator_token, creator_token=owner_token, record_id=resp_record.json()["id"], type='publish_draft', is_draft=True, create_forbidden=True)

    resp_record = create_record_in_community(BASE_URL, sample_record, token=owner_token, community_id=community_id, repo="docs")
    record_id = resp_record.json()["id"]
    upload_file(resp_record.json(), owner_token)
    time.sleep(2)
    #only owner is also record owner and curator is allowed
    do_request(receiver_token=curator_token, creator_token=owner_token, record_id=record_id, type='publish_draft', is_draft=True)
    """
    #test submit secondary
    time.sleep(2)
    payload = {'payload': {'community': community2_id}}
    do_request(owner_token, curator_token, record_id, "secondary_community_submission", payload)

    #test migrate
    payload = {'payload': {'community': community3_id}}
    do_request(owner_token, curator_token, record_id, "community_migration", payload)

    time.sleep(2)
    record = requests.get(f"{BASE_URL}/api/docs/{record_id}", headers=authorization_header(curator_token), verify=False).json()
    record_communities = record["parent"]["communities"]
    assert set(record_communities["ids"]) == {community2_id, community3_id}
    assert record_communities["default"] == community3_id

    # todo global search service bug - thesis service added twice from eps!!
    # should be docs instead of documents i guess
    record_communities_search = requests.get(f"{BASE_URL}/api/documents/{record_id}/communities", headers=authorization_header(curator_token), verify=False)
    community_records = requests.get(f"{BASE_URL}/api/communities/{community_id}/records", headers=authorization_header(curator_token), verify=False)
    assert record_communities_search.status_code == 200
    assert len(record_communities_search.json()["hits"]["hits"]) == 2
    assert community_records.status_code == 200

    #test remove secondary
    payload = {'payload': {'community': community2_id}}
    do_request(owner_token, curator_token, record_id, "remove_secondary_community", payload)

    time.sleep(2)
    record = requests.get(f"{BASE_URL}/api/docs/{record_id}", headers=authorization_header(curator_token), verify=False).json()
    record_communities = record["parent"]["communities"]
    assert set(record_communities["ids"]) == {community3_id}
    # test edit autoapprove

    """
    #test delete record
    delete_directly = requests.delete(f"{BASE_URL}/api/docs/{record_id}", headers=authorization_header(owner_token), verify=False)
    assert delete_directly.status_code == 403

    do_request(receiver_token=curator_token, creator_token=owner_token, record_id=record_id, type='delete_published_record') # todo implement access field to not crash IfRestricted generator
    time.sleep(2)
    record_resp = requests.get(f"{BASE_URL}/api/docs/{record_id}", headers=authorization_header(curator_token), verify=False)
    assert record_resp.status_code == 410