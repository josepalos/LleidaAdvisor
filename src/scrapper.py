#!/usr/bin/env python3
import csv
import datetime
import functools
import multiprocessing
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
RESTAURANT_DETAILS_NAME_CLASS_TOP = "restaurants-detail-overview-cards-DetailsSectionOverviewCard__categoryTitle--2RJP_"
RESTAURANT_DETAILS_CONTENT_CLASS_TOP = "restaurants-detail-overview-cards-DetailsSectionOverviewCard__tagText--1OH6h"
RESTAURANT_DETAILS_NAME_CLASS_BOTTOM = "restaurants-details-card-TagCategories__categoryTitle--28rB6"
RESTAURANT_DETAILS_CONTENT_CLASS_BOTTOM = "restaurants-details-card-TagCategories__tagText--Yt3iG"
RESTAURANT_DIRECTION_SPAN = "restaurants-detail-overview-cards-LocationOverviewCard__detailLinkText--co3ei"
RESTAURANT_SCORE_SPAN = "restaurants-detail-overview-cards-RatingsOverviewCard__overallRating--nohTl"
RESTAURANT_SCORES_DIV = "restaurants-detail-overview-cards-RatingsOverviewCard__ratingQuestionRow--5nPGK"

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
        self.cuisine_details = cuisine_details
        self.excellency_certificate = excellency_certificate

    @staticmethod
    def get_csv_headers() -> typing.List:
        return ["name", "direction", "phone", "score", "score_food",
                "score_service", "score_price", "score_ambient",
                "prices", "cuisine_details", "excellency_certificate"]

    def to_csv_row(self) -> typing.List:
        return [self.name, self.direction, self.phone, self.score,
                self.score_food, self.score_service, self.score_price,
                self.score_ambient, self.prices, self.cuisine_details,
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
               f"{self.visit_date_text} with score {self.score}"

    @property
    def visit_date_text(self):
        return self.visit_date.strftime("%Y-%m")

    @staticmethod
    def get_csv_headers() -> typing.List:
        return ["restaurant_id", "user", "title", "text", "visit_date",
                "score", "response"]

    def to_csv_row(self) -> typing.List:
        text = self.text.replace("\n", "\\n") if self.text else None
        response = self.response.replace("\n", "\\n") if self.response else None

        return [self.restaurant.name, self.user, self.title, text,
                self.visit_date_text, self.score, response]


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

    # Get address and phone
    direction = utils.get_text_elem(bs, "span", "class", RESTAURANT_DIRECTION_SPAN).text
    phone = utils.get_text_elem(bs, "div", "data-blcontact", "PHONE").text

    score_food = None
    score_service = None
    score_price = None
    score_ambient = None
    prices = None
    cuisine_details = None

    excellency_certificate = False

    # Get score
    score = float(utils.get_text_elem(bs, "span", "class", RESTAURANT_SCORE_SPAN).text.replace(',', '.'))

    all_scores = utils.get_text_all_elems(bs, "div", "class", RESTAURANT_SCORES_DIV)
    all_scores_len = len(all_scores)

    # Get all scores

    if all_scores_len != 0:
        score_food = int(
            utils.get_bubble_score(str(utils.get_text_elem(all_scores[0], "span", "class", "ui_bubble_rating")))) / 10
        score_service = int(
            utils.get_bubble_score(str(utils.get_text_elem(all_scores[1], "span", "class", "ui_bubble_rating")))) / 10
        score_price = int(
            utils.get_bubble_score(str(utils.get_text_elem(all_scores[2], "span", "class", "ui_bubble_rating")))) / 10

        if all_scores_len == 4:
            score_ambient = int(utils.get_bubble_score(
                str(utils.get_text_elem(all_scores[3], "span", "class", "ui_bubble_rating")))) / 10
        else:
            score_ambient = None

    # Get restaurant details and prices

    restaurant_details_top = utils.get_text_elem(bs, "div", "class",
                                                 "restaurants-detail-overview-cards-DetailsSectionOverviewCard__detailsSummary--evhlS")
    restaurant_details_bottom = utils.get_text_elem(bs, "div", "data-tab", "TABS_DETAILS")

    if not restaurant_details_top and restaurant_details_bottom:

        cols = utils.get_text_all_elems(restaurant_details_bottom, "div", "class", "ui_column")
        # list_cols = []
        dict = {}
        cuisine_details = ""

        for col in cols:
            dict.update(parse_restaurant_details(col, "BOTTOM"))

        # col1 = list_cols[0]
        # col2 = list_cols[1]
        # col3 = list_cols[2]

        # dict = {**col1, **col2, **col3}

        prices = dict.get("PRICE RANGE", None)

        if "CUISINES" in dict:
            cuisine_details += dict["CUISINES"] + ", "

        if "Special Diets" in dict:
            cuisine_details += dict["Special Diets"]


    elif not restaurant_details_bottom and restaurant_details_top:

        details = parse_restaurant_details(restaurant_details_top, "TOP")
        cuisine_details = ""

        prices = details.get("PRICE RANGE", None)

        if "CUISINES" in details:
            cuisine_details += details["CUISINES"] + ", "

        if "Special Diets" in details:
            cuisine_details += details["Special Diets"]

    # Get excellency certificate

    if utils.get_text_elem(bs, "div", "class", "restaurants-detail-overview-cards-RatingsOverviewCard__award--31yzt"):
        excellency_certificate = True

    print(
        "- Name:", name,
        "- Direction:", direction,
        "- Phone:", phone,
        "- Score:", score,
        "- Score ambient:", score_food,
        "- Score service:", score_service,
        "- Score price:", score_price,
        "- Prices:", prices,
        "- Score ambient:", score_ambient,
        "- Cuisine details:", cuisine_details,
        "- Excelency:", excellency_certificate
    )

    return Restaurant(
        name,
        direction,
        phone,
        score,
        score_food,
        score_service,
        score_price,
        prices,
        score_ambient,
        cuisine_details,
        excellency_certificate
    )


def parse_restaurant_details(categories_element: Tag, pos) -> dict:
    categories = dict()
    name = ""
    content = ""
    categories_divs = categories_element.children
    for category in categories_divs:

        if pos == "TOP":
            name = category.find(class_=RESTAURANT_DETAILS_NAME_CLASS_TOP).text
            content = category.find(class_=RESTAURANT_DETAILS_CONTENT_CLASS_TOP).text
        elif pos == "BOTTOM":
            name = category.find(class_=RESTAURANT_DETAILS_NAME_CLASS_BOTTOM).text
            content = category.find(class_=RESTAURANT_DETAILS_CONTENT_CLASS_BOTTOM).text
        categories[name] = content
    return categories


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
    print(f"Parsing review {review_id}")
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

    text = utils.get_text_with_breaks(page.find("p", class_="partial_entry"))

    visit_date_span = page.find(class_="prw_rup prw_reviews_stay_date_hsx")
    visit_date_text = visit_date_span.contents[1].strip()
    date = datetime.datetime.strptime(visit_date_text, '%B %Y').date()

    response_div = page.find(class_="mgrRspnInline")
    if response_div:
        response_element = response_div.find(class_="partial_entry")
        response = utils.get_text_with_breaks(response_element)
    else:
        response = None

    return Review(restaurant=restaurant,
                  user=username,
                  title=title,
                  text=text,
                  visit_date=date,
                  score=score,
                  response=response)


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




def get_restaurant(data):
    name, url = data
    return fetch_restaurant_info(name, url), url


def get_reviews(data, since):
    restaurant, url = data
    reviews = fetch_restaurant_reviews(restaurant, url, since=since)
    print("Reviews found:")
    for review in reviews:
        print(review)
        print(review.text)
        print(review.response)
        print("")
    return reviews


def main():
    number_of_restaurants = int(sys.argv[1])
    days_before = int(sys.argv[2])

    since = datetime.date.today() - datetime.timedelta(days=days_before)

    restaurants_divs = list()
    restaurant_offset = 0
    while len(restaurants_divs) < number_of_restaurants:
        restaurants_divs.extend(get_restaurants_list(GEO_LLEIDA,
                                                     restaurant_offset))
        restaurant_offset += RESTAURANT_PAGE_SIZE

    restaurants_divs = restaurants_divs[:number_of_restaurants]

    restaurants_data = (parse_div(restaurant)
                        for restaurant in restaurants_divs)

    with multiprocessing.Pool(10) as pool:
        restaurants = pool.map(get_restaurant, restaurants_data)
        pool.terminate()
        pool.join()

    with open("restaurants_lleida.csv", "w") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(Restaurant.get_csv_headers())
        for restaurant, _ in restaurants:
            writer.writerow(restaurant.to_csv_row())

    with multiprocessing.Pool(20) as pool:
        f = functools.partial(get_reviews, since=since)
        reviews = pool.map(f, restaurants)
        pool.terminate()
        pool.join()

    # Flat the reviews list
    reviews = [item for sublist in reviews for item in sublist]

    with open("reviews.csv", "w") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(Review.get_csv_headers())
        for review in reviews:
            writer.writerow(review.to_csv_row())

    print(f"Fetched {len(restaurants)} restaurants")
    print(f"Fetched {len(reviews)} reviews")


if __name__ == "__main__":
    main()
