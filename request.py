import requests

def safe_get(d, *keys, default=""):
    """
    Accede de forma segura a claves anidadas en un diccionario.
    Devuelve 'default' si alguna clave intermedia es None o no existe.
    """
    for key in keys:
        if isinstance(d, dict):
            d = d.get(key, None)
        else:
            return default
    return d if d is not None else default

def get_orcid_titles_and_dois(orcid_id):
    url = f"https://pub.orcid.org/v3.0/{orcid_id}/works"
    headers = {
        "Accept": "application/json"
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        works = response.json().get("group", [])
        for i, work in enumerate(works, 1):
            work_summary = work.get("work-summary", [])
            if not work_summary:
                continue

            ws = work_summary[0]
            title = safe_get(ws, "title", "title", "value", default="Sin título")

            doi = ""
            external_ids = ws.get("external-ids", {}).get("external-id", [])
            for eid in external_ids:
                if eid.get("external-id-type") == "doi":
                    doi = eid.get("external-id-value", "")
                    break  # Solo queremos un DOI por publicación

            print(f"{i}. {title}\n   DOI: {doi if doi else 'No disponible'}")
    else:
        print(f"Failed to fetch data. Status code: {response.status_code}")

# Ejemplo de uso
example_orcid_id = "0000-0002-3261-5005"
get_orcid_titles_and_dois(example_orcid_id)