import requests
import bs4


def get_bs(url, *args, **kwargs):
    response = requests.get(url)
    response.raise_for_status()
    return bs4.BeautifulSoup(response.text, 'html.parser')


def post_bs(url, *args, **kwargs):
    response = requests.post(url, *args, **kwargs)
    response.raise_for_status()
    return bs4.BeautifulSoup(response.text, "html.parser")


def get_text_elem(elem, tag, a , argument):
    return elem.find(tag, attrs={a:argument})

def get_text_all_elems(elem, tag, a , argument):
    return elem.findAll(tag, attrs={a: argument})

def get_bubble_score(str):
    return str[37:-9]
