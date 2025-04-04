import os
import requests
import json
import csv
import argparse
from urllib.parse import urlencode
import xml.etree.ElementTree as ET

# Base URL for PubMed E-utilities API
BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

# Base parameters for the PubMed API request
BASE_PARAMS = {
    "db": "pubmed",
}

def get_search_url(term, max_results=20):
    params = {**BASE_PARAMS, "retmode": "json", "term": term, "retmax": max_results}
    encoded = urlencode(params)
    return f"{BASE_URL}/esearch.fcgi?{encoded}"

def fetch_article_ids(search_url):
    response = requests.get(search_url)
    response.raise_for_status()
    data = response.json()
    return data.get("esearchresult", {}).get("idlist", [])

def parse_pub_date(pub_date_elem):
    if pub_date_elem is None:
        return ""
    medline_date = pub_date_elem.findtext('MedlineDate', '')
    if medline_date:
        return medline_date
    year = pub_date_elem.findtext('Year', '')
    month = pub_date_elem.findtext('Month', '')
    day = pub_date_elem.findtext('Day', '')
    if year:
        return f"{year}-{month}-{day}" if month or day else year
    return ""

def fetch_full_article_details(id_list):
    if not id_list:
        return []
    ids = ",".join(id_list)
    params = {
        **BASE_PARAMS,
        "id": ids,
        "retmode": "xml"
    }
    response = requests.get(f"{BASE_URL}/efetch.fcgi", params=params)
    response.raise_for_status()
    xml_data = response.text

    root = ET.fromstring(xml_data)
    articles = []

    for pubmed_article in root.findall('.//PubmedArticle'):
        medline = pubmed_article.find('MedlineCitation')
        if medline is None:
            continue

        pmid = medline.findtext('PMID', default="")

        article_elem = medline.find('Article')
        if article_elem is None:
            continue

        title = article_elem.findtext('ArticleTitle', default="No Title")

        abstract_text = ""
        abstract_elem = article_elem.find('Abstract')
        if abstract_elem is not None:
            texts = []
            for abstract_part in abstract_elem.findall('AbstractText'):
                if abstract_part.text:
                    texts.append(abstract_part.text.strip())
            abstract_text = " ".join(texts)

        journal_title = ""
        publication_date = ""
        journal_elem = article_elem.find('Journal')
        if journal_elem is not None:
            journal_title = journal_elem.findtext('Title', default="")
            journal_issue = journal_elem.find('JournalIssue')
            if journal_issue is not None:
                pub_date_elem = journal_issue.find('PubDate')
                publication_date = parse_pub_date(pub_date_elem)

        doi = ""
        for elem in article_elem.findall('ELocationID'):
            if elem.get('EIdType') == 'doi':
                doi = elem.text.strip() if elem.text else ""
                break

        authors = []
        author_list = article_elem.find('AuthorList')
        if author_list is not None:
            for author in author_list.findall('Author'):
                last_name = author.findtext('LastName')
                fore_name = author.findtext('ForeName')
                if fore_name and last_name:
                    authors.append(f"{fore_name} {last_name}")
                elif last_name:
                    authors.append(last_name)

        mesh_headings = []
        mesh_heading_list = medline.find('MeshHeadingList')
        if mesh_heading_list is not None:
            for mesh_heading in mesh_heading_list.findall('MeshHeading'):
                descriptor = mesh_heading.find('DescriptorName')
                if descriptor is not None and descriptor.text:
                    mesh_headings.append(descriptor.text.strip())

        record = {
            "pmid": pmid,
            "title": title,
            "abstract": abstract_text,
            "journal": journal_title,
            "publication_date": publication_date,
            "doi": doi,
            "authors": authors,
            "mesh_headings": mesh_headings,
        }
        articles.append(record)
    return articles

def save_to_jsonl(file_path, articles):
    with open(file_path, 'w', encoding='utf-8') as f:
        for article in articles:
            f.write(json.dumps(article) + '\n')

def save_to_csv(file_path, articles):
    if not articles:
        print("No articles to save.")
        return
    fieldnames = ["pmid", "title", "abstract", "journal", "publication_date", "doi", "authors", "mesh_headings"]
    with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for article in articles:
            article_copy = article.copy()
            article_copy["authors"] = "; ".join(article_copy.get("authors", []))
            article_copy["mesh_headings"] = "; ".join(article_copy.get("mesh_headings", []))
            writer.writerow(article_copy)

def main(search_term, data_dir):
    search_url = get_search_url(search_term)
    print(f"Searching PubMed with URL:\n{search_url}\n")

    try:
        id_list = fetch_article_ids(search_url)
    except requests.HTTPError as e:
        print(f"Error during PubMed search: {e}")
        return

    if not id_list:
        print("No articles found.")
        return

    print(f"Found {len(id_list)} article IDs.")

    try:
        articles = fetch_full_article_details(id_list)
    except requests.HTTPError as e:
        print(f"Error fetching article details: {e}")
        return

    os.makedirs(data_dir, exist_ok=True)

    jsonl_path = os.path.join(data_dir, "pubmed_full_articles.jsonl")
    save_to_jsonl(jsonl_path, articles)
    print(f"Article details saved to JSONL: {jsonl_path}")

    csv_path = os.path.join(data_dir, "pubmed_full_articles.csv")
    save_to_csv(csv_path, articles)
    print(f"Article details saved to CSV: {csv_path}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Fetch and save PubMed articles.")
    parser.add_argument('--search_term', type=str, required=True, help='Search term for PubMed')
    parser.add_argument('--data_dir', type=str, default='.', help='Directory to save the output files')
    args = parser.parse_args()

    main(args.search_term, args.data_dir)
