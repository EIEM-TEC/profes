import requests

def get_orcid_dois(orcid_id):
    url = f"https://pub.orcid.org/v3.0/{orcid_id}/works"
    headers = {
        "Accept": "application/json"
    }

    response = requests.get(url, headers=headers)

    dois = []

    if response.status_code == 200:
        works = response.json().get("group", [])
        for work in works:
            work_summary = work.get("work-summary", [])
            if not work_summary:
                continue

            ws = work_summary[0]
            external_ids = ws.get("external-ids", {}).get("external-id", [])
            for eid in external_ids:
                if eid.get("external-id-type") == "doi":
                    doi = eid.get("external-id-value", "")
                    if doi:
                        dois.append(doi)
    else:
        print(f"Failed to fetch data. Status code: {response.status_code}")

    return dois

# Ejemplo de uso:
example_orcid_id = "0000-0002-3261-5005"
for doi in get_orcid_dois(example_orcid_id):
    print(doi)
    