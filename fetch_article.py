import requests
from requests import Response, RequestException

from bs4 import BeautifulSoup

def fetch_article(url : str) -> Response | RequestException:
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except RequestException as e:
        return e
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        body = soup.find_all('section', id='post-body')

        print(f"Found {len(body)} <p> text")
        for text in body:
            print(text.get_text(separator='\n', strip=True))

    return response


def main():
    print(fetch_article('https://addyosmani.com/blog/factory-model/'))

if __name__ == "__main__":
    main()