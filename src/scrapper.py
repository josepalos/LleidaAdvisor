#!/usr/bin/env python3
import datetime
import functools
import typing

import requests_cache
from bs4 import Tag, BeautifulSoup

import utils
import sys

BASE_URL = "https://www.tripadvisor.com"
RESTAURANT_PAGINATION_URL = BASE_URL + "/RestaurantSearch?" \
                                       "&geo={geo}" \
                                       "&sortOrder=relevance" \
                                       "&o=a{offset}"
REVIEW_URL = BASE_URL + "/OverlayWidgetAjax?" \
                        "Mode=EXPANDED_HOTEL_REVIEWS&" \
                        "metaReferer=ShowUserReviewsRestaurants"
RESTAURANT_PAGE_SIZE = 30

GEO_LLEIDA = 187500
RESTAURANT_DIV_CLASS = "restaurants-list-ListCell__cellContainer--2mpJS"
RESTAURANT_NAME_CLASS = "restaurants-list-ListCell__restaurantName--2aSdo"


requests_cache.configure()


class Restaurant:
    def __init__(self,
                 name: str,
                 direction: str,
                 phone: str,
                 score: float,
                 score_food: float,
                 score_service: float,
                 score_price: float,
                 prices: str,
                 score_ambient: float,
                 opening_hours: str,  # TODO review
                 cuisine_details: str,
                 excellency_certificate: bool):
        self.name = name
        self.direction = direction
        self.phone = phone
        self.score = score
        self.score_food = score_food
        self.score_service = score_service
        self.score_price = score_price
        self.score_ambient = score_ambient
        self.prices = prices
        self.opening_hours = opening_hours
        self.cuisine_details = cuisine_details
        self.excellency_certificate = excellency_certificate

    @staticmethod
    def get_csv_headers() -> typing.List:
        return ["name", "direction", "phone", "score", "score_food",
                "score_service", "score_price", "score_ambient",
                "opening_hours", "cuisine_details", "excellency_certificate"]

    def to_csv_row(self) -> typing.List:
        return [self.name, self.direction, self.phone, self.score,
                self.score_food, self.score_service, self.score_price,
                self.score_ambient, self.opening_hours, self.cuisine_details,
                self.excellency_certificate]


class Review:
    def __init__(self,
                 restaurant: Restaurant,
                 user: str,
                 title: str,
                 text: str,
                 visit_date: datetime.date,
                 score: int,
                 response: typing.Optional[str]):
        self.restaurant = restaurant
        self.user = user
        self.title = title
        self.text = text
        self.visit_date = visit_date
        self.score = score
        self.response = response

    def __repr__(self):
        return f"Review by {self.user} at " \
               f"{self.visit_date_text} with score {self.score}: " \
               f"{self.title} -> {self.text}"

    @property
    def visit_date_text(self):
        return self.visit_date.strftime("%Y-%m")

    @staticmethod
    def get_csv_headers() -> typing.List:
        return ["restaurant_id", "user", "title", "text", "visit_date", "score",
                "response"]

    def to_csv_row(self) -> typing.List:
        return [self.restaurant.name, self.user, self.title, self.text,
                self.visit_date_text, self.score, self.response]


def get_restaurants_list(geolocation, offset):
    bs = utils.get_bs(generate_page_url(geolocation, offset))
    return bs.find_all(class_=RESTAURANT_DIV_CLASS)


def generate_page_url(geolocation, offset):
    return RESTAURANT_PAGINATION_URL.format(geo=geolocation, offset=offset)


def generate_reviews_url(restaurant_url: str, page: int) -> str:
    """
    To change the reviews page, change the "[...]-Reviews-[...]" part of the
    request to "[...]-Reviews-or<N>-[...]", where N is a multiple of 10 that
    refers to the offset of the reviews.
    :param restaurant_url: The relative url to the restaurant
    :param page: The page number to retrieve
    :return: The url of the reviews page
    """
    offset = page * 10
    page_url = restaurant_url.replace("-Reviews-", f"-Reviews-or{offset}-")
    return BASE_URL + page_url


def parse_div(restaurant_div):
    name_div = restaurant_div.find(class_=RESTAURANT_NAME_CLASS)
    name = name_div.text
    url = name_div.attrs["href"]
    return name, url


def fetch_restaurant_info(name: str, restaurant_url: str) -> Restaurant:

    bs = utils.get_bs(BASE_URL + restaurant_url)
    print(restaurant_url)
    direction = utils.get_text_elem(bs, "span", "class", "restaurants-detail-overview-cards-LocationOverviewCard__detailLinkText--co3ei").text
    phone = utils.get_text_elem(bs, "div", "data-blcontact", "PHONE").text

    # Canviar a float
    score = utils.get_text_elem(bs, "span", "class", "restaurants-detail-overview-cards-RatingsOverviewCard__overallRating--nohTl").text

    all_scores = utils.get_text_all_elems(bs, "div", "class", "restaurants-detail-overview-cards-RatingsOverviewCard__ratingQuestionRow--5nPGK")

    if(len(all_scores)==0):
        score_food = None
        score_service = None
        score_price = None
    else:
        score_food = int(utils.get_bubble_score(str(utils.get_text_elem(all_scores[0], "span", "class", "ui_bubble_rating"))))/10
        score_service = int(utils.get_bubble_score(str(utils.get_text_elem(all_scores[1], "span", "class", "ui_bubble_rating"))))/10
        score_price = int(utils.get_bubble_score(str(utils.get_text_elem(all_scores[2], "span", "class", "ui_bubble_rating"))))/10

    restaurant_details = utils.get_text_all_elems(bs, "div", "class", "restaurants-detail-overview-cards-DetailsSectionOverviewCard__tagText--1OH6h");
    print(len(restaurant_details))

    # prices = utils.get_text_elem(bs, "div", "class", "restaurants-detail-overview-cards-DetailsSectionOverviewCard__tagText--1OH6h").text

    # score_ambient: float,
    # opening_hours = utils.get_text_elem(bs, "div", "class", "public-location-hours-LocationHours__hoursPopover--2h1HP")
    # cuisine_details = utils.get_text_elem(bs, "div", "class", "restaurants-detail-overview-cards-DetailsSectionOverviewCard__tagText--1OH6h")

    excellency_certificate = False

    if(utils.get_text_elem(bs, "div", "class", "restaurants-detail-overview-cards-RatingsOverviewCard__award--31yzt")):
        excellency_certificate = True



    print(name + " " + direction + " " + phone + " " + " Score: " + score + " Score food: " + str(score_food) + " Score service: " + str(score_service) + " Score price: " + str(score_price) + " " + str(excellency_certificate))

    return None


def fetch_restaurant_reviews_page(restaurant: Restaurant,
                                  restaurant_url: str,
                                  page: int
                                  ) -> typing.List[Review]:
    """
    Fetch the reviews for the current specified page
    :param restaurant: The Restaurant object this reviews will refer
    :param restaurant_url: The restaurant url
    :param page: The page to scrap
    :return: A list with all the reviews found for this restaurant in this page
    """
    bs = utils.request_reviews(restaurant_url, page)

    reviews_div = bs.find(id="taplc_location_reviews_list_resp_rr_resp_0")
    reviews_containers = reviews_div.find_all(class_="review-container")

    # Fetch the entire page instead of parsing the container to avoid problems
    # such as large reviews partially shown.
    reviews_pages = (get_review_page(review_container)
                     for review_container in reviews_containers)

    wrapper = functools.partial(parse_review_page, restaurant)
    return [wrapper(page) for page in reviews_pages]


def get_review_page(review_container: Tag) -> BeautifulSoup:
    review_id = review_container.attrs["data-reviewid"]
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Requested-With": "XMLHttpRequest",
    }
    data = {
        "reviews": review_id
    }
    return utils.post_bs(REVIEW_URL, headers=headers, data=data)


def parse_review_page(restaurant: Restaurant, page: BeautifulSoup) -> Review:
    title = page.find("div", class_="quote").text.strip()
    score = utils.get_rating(page)

    username = page.find(class_="member_info").find(class_="username").text

    text = page.find("p", class_="partial_entry").text

    visit_date_span = page.find(class_="prw_rup prw_reviews_stay_date_hsx")
    visit_date_text = visit_date_span.contents[1].strip()
    date = datetime.datetime.strptime(visit_date_text, '%B %Y').date()

    return Review(restaurant=restaurant,
                  user=username,
                  title=title,
                  text=text,
                  visit_date=date,
                  score=score,
                  response=None)


def remove_older(reviews: typing.List[Review], since: datetime.date
                 ) -> typing.List[Review]:
    """
    Having a list of reviews, remove the reviews older than the "since" date.
    :param reviews: The list of the reviews to clean
    :param since: The date that will be applied as a removing criteria
    :return: The list without the old reviews
    """
    return [review for review in reviews if review.visit_date >= since]


def fetch_restaurant_reviews(restaurant: Restaurant,
                             restaurant_url: str,
                             since: datetime.date
                             ) -> typing.List[Review]:
    """
    Fetch all the reviews for a restaurant since a specified date.
    :param restaurant: The restaurant this reviews will refer
    :param restaurant_url: The url of the restaurant to scrap
    :param since: The date that sets the limit of the reviews to scrap
    :return: A list with all the requests found
    """
    all_reviews = list()
    current_page = 0
    while True:
        reviews = fetch_restaurant_reviews_page(restaurant, restaurant_url,
                                                current_page)
        reviews = remove_older(reviews, since)
        if not reviews:
            break
        all_reviews.extend(reviews)
        current_page += 1

    return all_reviews


if __name__ == "__main__":
    restaurant_offset = sys.argv[1]
    restaurants_divs = get_restaurants_list(GEO_LLEIDA, restaurant_offset)
    restaurants_urls = (parse_div(restaurant)
                        for restaurant in restaurants_divs)

    # restaurants = [fetch_restaurant_info(name, restaurant)
    #                for name, restaurant in restaurants_urls]

    two_years = datetime.date.today() - datetime.timedelta(days=365)
    print(f"Retrieving reviews since {two_years}")
    restaurant = None
    restaurant_url = "/Restaurant_Review-g187500-d995334-Reviews-Xalet_Suis-Lleida_Province_of_Lleida_Catalonia.html"
    reviews = fetch_restaurant_reviews(restaurant, restaurant_url, since=two_years)

    print("Reviews found:")
    for review in reviews:
        print(review)
        print("")
