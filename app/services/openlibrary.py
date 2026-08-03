import requests
from typing import Optional, Dict

def fetch_book_by_isbn(isbn: str) -> Optional[Dict]:
    """
    Fetches book metadata from Open Library API by ISBN.
    Auto-fills: Title, Author, Publisher, Pub Year, Pages, Cover URL.
    """
    clean_isbn = isbn.strip().replace("-", "").replace(" ", "")
    if not clean_isbn:
        return None
    
    url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{clean_isbn}&jscmd=data&format=json"
    try:
        res = requests.get(url, timeout=4)
        if res.status_code == 200:
            data = res.json()
            key = f"ISBN:{clean_isbn}"
            if key in data:
                item = data[key]
                title = item.get("title", "Unknown Title")
                
                authors_list = item.get("authors", [])
                author = ", ".join([a.get("name") for a in authors_list]) if authors_list else "Unknown Author"
                
                publishers_list = item.get("publishers", [])
                publisher = publishers_list[0].get("name") if publishers_list else "Unknown Publisher"
                
                pub_date = item.get("publish_date", "")
                pub_year = None
                if pub_date:
                    for token in pub_date.split():
                        if token.isdigit() and len(token) == 4:
                            pub_year = int(token)
                            break
                
                pages = item.get("number_of_pages", None)
                
                cover_dict = item.get("cover", {})
                cover_url = cover_dict.get("medium") or cover_dict.get("large") or cover_dict.get("small") or None
                
                return {
                    "title": title,
                    "author": author,
                    "isbn": clean_isbn,
                    "publisher": publisher,
                    "pub_year": pub_year,
                    "pages": pages,
                    "cover_url": cover_url,
                    "category": "General Literature"
                }
    except Exception as e:
        print(f"[OPENLIBRARY API ERROR] {e}")
    
    return None
