import requests

def get_ieee_metadata_from_crossref(doi):
    """
    Dado un DOI, consulta Crossref y devuelve un diccionario con los metadatos
    necesarios para una cita en formato IEEE.
    """
    url = f"https://api.crossref.org/works/{doi}"
    headers = {
        "Accept": "application/json"
    }

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        return {"doi": doi, "error": f"Error {response.status_code}"}

    message = response.json().get("message", {})

    # Obtener autores formateados como lista de "Iniciales Apellido"
    authors = message.get("author", [])
    formatted_authors = []
    for author in authors:
        given = author.get("given", "")
        family = author.get("family", "")
        initials = ''.join([n[0] + '.' for n in given.split()]) if given else ''
        formatted_name = f"{initials} {family}".strip()
        formatted_authors.append(formatted_name)

    return {
        "doi": doi,
        "authors": formatted_authors,  # lista de autores
        "title": message.get("title", [""])[0],
        "container": message.get("container-title", [""])[0],  # revista o conferencia
        "volume": message.get("volume", ""),
        "issue": message.get("issue", ""),
        "pages": message.get("page", ""),
        "year": message.get("issued", {}).get("date-parts", [[None]])[0][0]
    }

doi = "10.18845/tm.v37i3.6833"
metadata = get_ieee_metadata_from_crossref(doi)

print(metadata)
