import requests
import bs4
from bs4 import Tag

from scrapper import generate_reviews_url


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


def request_reviews(restaurant_url: str, page: int) -> bs4.BeautifulSoup:
    headers = {
        "x-requested-with": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "filterLang": "ALL",
        "filterSafety": "FALSE",
        "reqNum": 1,
        "paramSeqId": 6,
        "changeSet": "REVIEW_LIST",
    }
    url = generate_reviews_url(restaurant_url, page)
    bs = post_bs(url, headers=headers, data=data)
    return bs


def get_rating(tag: Tag) -> int:
    classes = tag.find(class_="ui_bubble_rating")['class']
    for class_ in classes:
        if class_.startswith("bubble_"):
            score = class_.replace("bubble_", "")
            return int(int(score) / 10)