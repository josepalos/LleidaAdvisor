import requests
import bs4


def get_bs(url, *args, **kwargs):
    response = requests.get(url)
    response.raise_for_status()
    return bs4.BeautifulSoup(response.text, 'html.parser')
