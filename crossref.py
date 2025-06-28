import csv
import requests
import time
import urllib.parse
from rapidfuzz import fuzz
import unicodedata

def limpiar_texto(texto):
    if not texto:
        return ""
    texto = unicodedata.normalize("NFKC", texto)
    texto = texto.replace("´a", "á").replace("´e", "é").replace("´i", "í").replace("´o", "ó").replace("´u", "ú")
    texto = texto.replace("`a", "á").replace("`e", "é").replace("`i", "í").replace("`o", "ó").replace("`u", "ú")
    texto = texto.replace("´A", "Á").replace("´E", "É").replace("´I", "Í").replace("´O", "Ó").replace("´U", "Ú")
    texto = texto.replace("`A", "Á").replace("`E", "É").replace("`I", "Í").replace("`O", "Ó").replace("`U", "Ú")
    texto = texto.replace("´n", "ñ").replace("´N", "Ñ")
    texto = texto.replace("´", "")  # elimina comillas sueltas si quedan
    return texto

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

def normalize_pub_key(pub):
    doi = pub.get("doi", "").strip().lower()
    if doi:
        return f"doi::{doi}"
    else:
        # Normalizar título
        title = pub.get("titulo", "").strip().lower()
        return f"title::{title}"

def search_crossref_by_title(title, max_results=3, threshold=85, log_discards=None):
    query = urllib.parse.quote(title)
    url = f"https://api.crossref.org/works?query.title={query}&rows={max_results}"
    response = requests.get(url)

    if response.status_code == 200:
        items = response.json().get("message", {}).get("items", [])
        best_match = None
        best_score = 0

        for item in items:
            candidate_title = item.get("title", [""])[0]
            score = fuzz.token_sort_ratio(candidate_title.lower(), title.lower())
            if score > best_score and score >= threshold:
                best_score = score
                best_match = item

        if best_match:
            data = best_match
            authors = ["{} {}".format(a.get("given", ""), a.get("family", "")).strip()
                       for a in data.get("author", []) if "given" in a or "family" in a]

            if not authors:
                print("    ❌ Match found but has no authors, skipping.")
                if log_discards is not None:
                    log_discards.append({"codigo": "", "titulo": title, "motivo": "sin_autores"})
                return {}

            title_final = data.get("title", [""])[0] if data.get("title") else ""
            revista = data.get("container-title", [""])[0] if data.get("container-title") else ""
            date_parts = get_first_date(data)
            year = date_parts[0] if len(date_parts) > 0 else ""

            if not title_final or not revista or not year:
                print("    ❌ Match found but missing title, journal, or year. Skipping.")
                if log_discards is not None:
                    log_discards.append({"codigo": "", "titulo": title, "motivo": "faltan_datos"})
                return {}

            month = date_parts[1] if len(date_parts) > 1 else ""
            day = date_parts[2] if len(date_parts) > 2 else ""

            return {
                "titulo": title_final,
                "revista": revista,
                "tipo": data.get("type", ""),
                "autores": ";".join(authors),
                "año": year,
                "mes": month,
                "dia": day,
                "doi": data.get("DOI", "")
            }

    return {}

def procesar_orcid_desde_csv(input_csv="00_datos.csv", output_csv="06_publicaciones.csv"):
    with open(input_csv, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        publicaciones = []
        descartados = []
        seen_keys = set()

        for row in reader:
            print(row["nombre"])
            codigo = row["codigo"]
            orcid = row["orcid"]
            if orcid == "00" or not orcid.strip():
                print("⚠️ ORCID no válido, se omite.")
                continue
            print(f"🔍 Procesando ORCID {orcid}...")

            works = get_orcid_dois_with_paths(orcid)
            for work in works:
                doi = work["doi"]
                put_code = work["put_code"]
                metadata = None

                if doi:
                    print(f"  DOI encontrado: {doi}")
                    metadata = get_ieee_metadata_from_crossref(doi)
                    if metadata:
                        metadata["fuente"] = "crossref_doi"
                else:
                    print(f"  Sin DOI, usando ORCID work {put_code}")
                    orcid_metadata = get_metadata_from_orcid_work(orcid, put_code)
                    if orcid_metadata:
                        enriched = search_crossref_by_title(orcid_metadata["titulo"])
                        if enriched:
                            metadata = enriched
                            metadata["fuente"] = "crossref_title"
                        else:
                            print(f"    ❌ No good match found for title: {orcid_metadata['titulo']}")
                            descartados.append({
                                "codigo": codigo,
                                "titulo": orcid_metadata["titulo"],
                                "motivo": "sin_coincidencia"
                            })

                if metadata:
                    metadata["codigo"] = codigo
                    key = normalize_pub_key(metadata)
                    if key not in seen_keys:
                        seen_keys.add(key)
                        publicaciones.append(metadata)

                time.sleep(0.1)

    for pub in publicaciones:
        for key in pub:
            if isinstance(pub[key], str):
                pub[key] = limpiar_texto(pub[key])

    with open(output_csv, mode="w", newline="", encoding="utf-8") as f:
        fieldnames = ["codigo", "titulo", "revista", "tipo", "autores", "año", "mes", "dia", "doi", "fuente"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(publicaciones)
    print(f"\n✅ Publicaciones exportadas a {output_csv}")

    if descartados:
        with open("05_publicaciones_descartadas.csv", mode="w", newline="", encoding="utf-8") as f:
            fieldnames = ["codigo", "titulo", "motivo"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(descartados)
        print(f"\n⚠️ {len(descartados)} publicaciones descartadas exportadas a 06_publicaciones_descartadas.csv")
    else:
        print("\n✅ No hubo publicaciones descartadas.")

procesar_orcid_desde_csv()
