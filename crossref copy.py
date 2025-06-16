import csv
import requests
import time
import urllib.parse
from rapidfuzz import fuzz
import traceback
from pybliometrics.scopus import ScopusSearch, AbstractRetrieval

import csv
import requests
import time
import urllib.parse
from rapidfuzz import fuzz
import os
import traceback
from configparser import ConfigParser


# Asegurar imports disponibles si pybliometrics falla
try:
    from pybliometrics.scopus import ScopusSearch, AbstractRetrieval
    PYBLIOMETRICS_AVAILABLE = True
except ImportError:
    PYBLIOMETRICS_AVAILABLE = False

# === NUEVO fallback para Scopus vía requests ===
def search_scopus_via_requests(api_key, query, count=5):
    url = "https://api.elsevier.com/content/search/scopus"
    params = {
        "query": query,
        "apiKey": api_key,
        "count": count,
        "view": "STANDARD"
    }
    headers = {"Accept": "application/json"}

    resp = requests.get(url, headers=headers, params=params)

    if resp.status_code == 200:
        data = resp.json()
        entries = data.get("search-results", {}).get("entry", [])
        print(f"✅ Resultados encontrados: {len(entries)}")
        publicaciones = []
        for item in entries:
            titulo = item.get("dc:title")
            if not titulo:
                continue  # Evita publicaciones sin título (clave requerida)
            publicaciones.append({
                "titulo": titulo,
                "autores": item.get("dc:creator"),
                "año": item.get("prism:coverDate", "").split("-")[0],
                "mes": item.get("prism:coverDate", "").split("-")[1] if '-' in item.get("prism:coverDate", "") else "",
                "dia": item.get("prism:coverDate", "").split("-")[2] if '-' in item.get("prism:coverDate", "") else "",
                "revista": item.get("prism:publicationName", ""),
                "doi": item.get("prism:doi", ""),
                "tipo": "article",
                "fuente": "scopus_requests"
            })
        return publicaciones
    else:
        print(f"❌ Error {resp.status_code}: {resp.text}")
        return []

def get_scopus_publications_by_orcid(orcid_id, api_key):
    query = f"AU-ID({orcid_id})"

    if PYBLIOMETRICS_AVAILABLE:
        try:
            search = ScopusSearch(query, refresh=True)
            if not search.get_eids():
                raise RuntimeError("No EIDs returned")
        except Exception as e:
            print(f"⚠️ Error buscando Scopus para {orcid_id}, usando fallback con requests: {e}")
            try:
                results = search_scopus_via_requests(api_key, query)
                if isinstance(results, list):
                    return [r for r in results if r and isinstance(r, dict) and r.get("titulo")]
                else:
                    print("❌ Fallback devolvió un valor inesperado (no es lista).")
                    return []
            except Exception as e2:
                print(f"❌ Fallback con requests también falló: {e2}")
                return []

        publications = []
        for eid in search.get_eids():
            try:
                abstract = AbstractRetrieval(eid, view="FULL")
                authors = ["{} {}".format(a.given_name, a.surname).strip() for a in abstract.authors or []]

                pub = {
                    "titulo": abstract.title or "",
                    "revista": abstract.publicationName or "",
                    "tipo": abstract.subtypeDescription or "",
                    "autores": ";".join(authors),
                    "año": abstract.coverDate.split("-")[0] if abstract.coverDate else "",
                    "mes": abstract.coverDate.split("-")[1] if abstract.coverDate else "",
                    "dia": abstract.coverDate.split("-")[2] if abstract.coverDate else "",
                    "doi": abstract.doi or "",
                    "fuente": "scopus"
                }
                publications.append(pub)
            except Exception as e:
                print(f"  ❌ Error al recuperar {eid}: {e}")
                traceback.print_exc()
        return publications
    else:
        print(f"⚠️ pybliometrics no está disponible. Usando fallback con requests para {orcid_id}.")
        try:
            results = search_scopus_via_requests(api_key, query)
            return [r for r in results if r and r.get("titulo")]
        except Exception as e:
            print(f"❌ Fallback con requests también falló: {e}")
            return []

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

            # ❌ Filtrar si no hay autores
            if not authors:
                print("    ❌ Match found but has no authors, skipping.")
                if log_discards is not None:
                    log_discards.append({"codigo": "", "titulo": title, "motivo": "sin_autores"})
                return {}

            # ❌ Filtrar si falta título, año o revista
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

def procesar_orcid_desde_csv(input_csv="00_datos.csv", output_csv="05_publicaciones.csv"):
    with open(input_csv, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        publicaciones = []
        descartados = []
        seen_keys = set()  # Para evitar duplicados

        for row in reader:
            print(row["nombre"])
            codigo = row["codigo"]
            orcid = row["orcid"]
            if orcid == "00" or not orcid.strip():
                print("⚠️ ORCID no válido, se omite.")
                continue
            print(f"🔍 Procesando ORCID {orcid}...")

            # === ORCID + CrossRef ===
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

            # === Scopus ===
            scopus_pubs = get_scopus_publications_by_orcid(orcid,api_key)
            for pub in scopus_pubs:
                pub["codigo"] = codigo
                key = normalize_pub_key(pub)
                if key not in seen_keys:
                    seen_keys.add(key)
                    publicaciones.append(pub)

    # Escribir publicaciones
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
        print(f"\n⚠️ {len(descartados)} publicaciones descartadas exportadas a 05_publicaciones_descartadas.csv")
    else:
        print("\n✅ No hubo publicaciones descartadas.")

api_key = "cd8faa5492300e4e2edce53cfc63f1f8"  # usa tu clave real

procesar_orcid_desde_csv()

