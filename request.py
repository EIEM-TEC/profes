import requests

def get_orcid_works(orcid_id):
    url = f"https://pub.orcid.org/v3.0/{orcid_id}/works"
    headers = {
        "Accept": "application/json"
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        works = response.json().get("group", [])
        for i, work in enumerate(works, 1):
            work_summary = work.get("work-summary", [])
            if work_summary:
                title = work_summary[0].get("title", {}).get("title", {}).get("value", "No title")
                pub_year = work_summary[0].get("publication-date", {}).get("year", {}).get("value", "N/A")
                print(f"{i}. {title} ({pub_year})")
    else:
        print(f"Failed to fetch data. Status code: {response.status_code}")

# Example ORCID iD (belongs to Dr. José Luis Hernández Garciadiego)
example_orcid_id = "0000-0002-3261-5005"
get_orcid_works(example_orcid_id)