import requests
from requests import Response, RequestException

from bs4 import BeautifulSoup

def fetch_article(url : str) -> str | None:
    """Requests a page from URL via HTTP"""

    print(f"Fetching URL: {url}\n")

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        content_type = response.headers.get('Content-Type', '')
    except RequestException as e:
        print(f"Caught Request Exception {e}")
        return None
    
    if response.status_code == 200 and "text/html" in content_type:
        return parse_article(response)
    else:
        return None
       

def parse_article(response: Response) -> str | None:
    """Parses page to extract text content."""

    soup = BeautifulSoup(response.content, 'html.parser')
    noise_tags = [
        'nav', 'footer', 'header', 'aside',
        'script', 'meta', 'style', 'form',
        'svg', 'noscript', 'iframe', 'button',
    ]

    noise_selectors = [
    '[role="navigation"]',
    '[role="complementary"]',
    '[role="banner"]',
    '.comments', '.comment-section', '#comments',
    '.sidebar', '#sidebar',
    '.social-share', '.share-buttons', '.sharing',
    '.related-posts', '.recommended', '.read-next',
    '.newsletter-signup', '.subscribe',
    '.cookie-banner', '.cookie-consent',
    '.author-bio', '.author-card',
    '.table-of-contents', '.toc',
    '.breadcrumb', '.breadcrumbs',
    '.pagination',
    '.ad', '.advertisement', '.sponsored',
    ]

    for selector in noise_selectors:
        for el in soup.select(selector):
            el.decompose()

    for tag_noise in soup.find_all(noise_tags):
        tag_noise.decompose()

    content = soup.find('article') or soup.find('main') or soup.find('body')

    if content:
        text = content.get_text(separator='\n', strip=True)
        if len(text) < 200:
            return None

        return text


def main():
    fetch_article('https://www.anthropic.com/engineering/building-c-compiler')
    fetch_article('https://github.com/jrswab/axe')
    fetch_article('https://kubernetes.io/blog/2026/03/09/announcing-ai-gateway-wg/')
    fetch_article('https://huggingface.co/blog/ibm-granite/granite-4-speech')

if __name__ == "__main__":
    main()