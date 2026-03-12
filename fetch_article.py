import requests
from requests import Response, RequestException

from bs4 import BeautifulSoup

def fetch_article(url : str) -> str | None:
    print(f"URL: {url}\n")

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except RequestException as e:
        print(f"Caught Request Exception {e}")
        return None
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        noise_tags = ['nav', 'footer', 'header', 'aside', 'script', 'meta', 'style', 'form']

        #print(f"BEFORE:\n {soup.get_text(separator='\n', strip=True)}")

        noise = soup.find_all(noise_tags)
        if noise:
            for n in noise:
                n.decompose()
        #print(f"AFTER:\n {soup.get_text(separator='\n', strip=True)}")

        content = soup.find('article') or soup.find('main') or soup.find('body')
        if content:
            print(f"CONTENT:\n {content.get_text(separator='\n', strip=True)}")

        if content:
            return content.get_text(separator='\n', strip=True)
        else:
            return None


def main():
    fetch_article('https://www.anthropic.com/engineering/building-c-compiler')
    fetch_article('https://github.com/jrswab/axe')
    fetch_article('https://kubernetes.io/blog/2026/03/09/announcing-ai-gateway-wg/')
    fetch_article('https://huggingface.co/blog/ibm-granite/granite-4-speech')

if __name__ == "__main__":
    main()