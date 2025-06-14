import csv
import requests
import time

def safe_get(d, *keys, default=""):
    for key in keys:
        if isinstance(d, dict):
            d = d.get(key)
        else:
            return default
    return d if d is not None else default

def get_first_date(data, keys=("published", "published-online", "published-print")):
    for key in keys:
        parts = safe_get(data, key, "date-parts", default=[])
        if isinstance(parts, list) and len(parts) > 0 and isinstance(parts[0], list):
            return parts[0]  # [year, month, day...]
    return ["", "", ""]

def get_orcid_dois_with_paths(orcid_id):
    url = f"https://pub.orcid.org/v3.0/{orcid_id}/works"
    headers = {"Accept": "application/json"}
    response = requests.get(url, headers=headers)

    result = []
    if response.status_code == 200:
        works = response.json().get("group", [])
        for work in works:
            summaries = work.get("work-summary", [])
            if summaries:
                summary = summaries[0]
                put_code = summary.get("put-code")
                doi = ""
                for ext_id in summary.get("external-ids", {}).get("external-id", []):
                    if ext_id.get("external-id-type", "").lower() == "doi":
                        doi = ext_id.get("external-id-value", "")
                        break
                result.append({"doi": doi, "put_code": put_code})
    return result

def get_ieee_metadata_from_crossref(doi):
    url = f"https://api.crossref.org/works/{doi}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json().get("message", {})
        authors = ["{} {}".format(a.get("given", ""), a.get("family", "")).strip()
                   for a in data.get("author", [])]
        date_parts = get_first_date(data)
        year = date_parts[0] if len(date_parts) > 0 else ""
        month = date_parts[1] if len(date_parts) > 1 else ""
        day = date_parts[2] if len(date_parts) > 2 else ""
        return {
            "titulo": data.get("title", [""])[0],
            "revista": data.get("container-title", [""])[0] if data.get("container-title") else "",
            "tipo": data.get("type", ""),
            "autores": ";".join(authors),
            "año": year,
            "mes": month,
            "dia": day,
            "doi": doi
        }
    return {}

def get_metadata_from_orcid_work(orcid_id, put_code):
    url = f"https://pub.orcid.org/v3.0/{orcid_id}/work/{put_code}"
    headers = {"Accept": "application/json"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        title = safe_get(data, "title", "title", "value")
        tipo = data.get("type", "")
        revista = safe_get(data, "journal-title", "value")
        pub_date = data.get("publication-date", {})
        year = safe_get(pub_date, "year", "value")
        month = safe_get(pub_date, "month", "value")
        day = safe_get(pub_date, "day", "value")
        return {
            "titulo": title,
            "revista": revista,
            "tipo": tipo,
            "autores": "",  # ORCID no provee autores desde esta ruta
            "año": year,
            "mes": month,
            "dia": day,
            "doi": ""
        }
    return {}

def procesar_orcid_desde_csv(input_csv="00_datos.csv", output_csv="05_publicaciones.csv"):
    with open(input_csv, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        publicaciones = []

        for row in reader:
            print(row["nombre"])
            codigo = row["codigo"]
            orcid = row["orcid"]
            print(f"Procesando ORCID {orcid}...")

            works = get_orcid_dois_with_paths(orcid)
            for work in works:
                doi = work["doi"]
                put_code = work["put_code"]

                if doi:
                    print(f"  DOI encontrado: {doi}")
                    metadata = get_ieee_metadata_from_crossref(doi)
                else:
                    print(f"  Sin DOI, usando ORCID work {put_code}")
                    metadata = get_metadata_from_orcid_work(orcid, put_code)

                if metadata:
                    metadata["codigo"] = codigo
                    publicaciones.append(metadata)

                time.sleep(0.2)  # Respetar límite de peticiones

    # Escribir el CSV de salida
    with open(output_csv, mode="w", newline="", encoding="utf-8") as f:
        fieldnames = ["codigo", "titulo", "revista", "tipo", "autores", "año", "mes", "dia", "doi"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(publicaciones)
    print(f"\nPublicaciones exportadas a {output_csv}")

# Ejecutar
procesar_orcid_desde_csv()

