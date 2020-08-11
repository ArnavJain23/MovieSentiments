import grequests
import pandas as pd
import requests
from bs4 import BeautifulSoup

from RottenTomatoesScraper import RottenTomatoesScraper

safari_header = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1 Safari/605.1.15",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Charset": "ISO-8859-1,utf-8;q=0.7,*;q=0.3",
    "Accept-Encoding": "none",
    "Accept-Language": "en-CA,en;q=0.8",
    "Connection": "keep-alive",
}
firefox_header = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.6; rv:16.0) Gecko/20100101 Firefox/16.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Charset": "ISO-8859-1,utf-8;q=0.7,*;q=0.3",
    "Accept-Encoding": "none",
    "Accept-Language": "en-CA,en;q=0.8",
    "Connection": "keep-alive",
}
RT_url = "https://www.rottentomatoes.com"


def get_top_100_movie_tags(year=2017, headers: dict = None):
    """Get HTML tags from top 100 movies page on Rotten Tomatoes.

    Args:
        year (int, optional): Top 100 movies of which year. Defaults to 2019.
        headers (dict, optional): User-Agent headers for requests. 
        Defaults to Macbook-Safari.

    Returns:
        bs4.element.ResultSet: Top 100 movies HTML tags.
    """
    if not headers:
        headers = safari_header
    top_movies_page = f"/top/bestofrt/?year={year}"
    print(f"Requesting top 100 movies' tags from year: {year}", end="  ->  ")
    src = requests.get(f"{RT_url}{top_movies_page}", headers=headers)
    src.raise_for_status()
    print("Succesfully got response from Rotten Tomatoes.")
    content = src.content
    soup = BeautifulSoup(content, "lxml")
    movie_tags = soup.find_all("tr", class_=None)
    if not movie_tags:
        raise AttributeError("No movie tags were found, check URL?")
    print("  Succesfully gathered movie tags.")
    return movie_tags


def get_user_review_urls_from_tags(movie_tags) -> list:
    """Get URL's of movie user reviews from HTML tags.

    Args:
        movie_tags (bs4.element.ResultSet): Top 100 movies HTML tags.

    Returns:
        list: List of URL's.
    """
    user_review_page = "/reviews?type=user"
    urls = []
    for tag in movie_tags:
        try:
            movie_path = tag.a["href"]
        except TypeError:
            print("    Skipping invalid HTML element.")
            continue
        url = f"{RT_url}{movie_path}{user_review_page}"
        urls.append(url)
    print("  Succesfully gathered all user review URL's.")
    return urls


def get_responses(urls, headers: dict = None, retry=False):
    """Asynchronously get responses from URL's.

    Args:
        urls (list): List of URL's.
        headers (dict): User-Agent headers for requests. 
        Defaults to Macbook-Safari.
    
    Returns:
        responses
    """
    if not headers:
        headers = safari_header
    print("Fetching responses...", end="  ->  ")
    reqs = (grequests.get(url, headers=headers) for url in urls)
    handler = lambda request, exception: print(f"Request failed:\n{exception}")
    responses = grequests.map(reqs, size=10, exception_handler=handler)
    time = 0
    for response in responses:
        time += int(response.elapsed.total_seconds())
        if response.status_code == 403:
            if not retry:
                print(
                    "\033[1mReceived 403 forbidden error;\nRetrying with different headers:\033[0m"
                )
                responses = get_responses(urls, firefox_header, retry=True)
                return responses
            else:
                raise requests.exceptions.HTTPError(
                    "Received 403 error again: check size, headers, and URL's"
                )

    if not responses:
        raise AttributeError("No responses were recieved")
    else:
        print(f"Recieved responses succesfully in {time} seconds")
    return responses


def generate_df(responses) -> pd.DataFrame:
    """Create pandas dataframe from grequest's responses.

    Args:
        responses

    Returns:
        pd.DataFrame: Dataframe including movie title, review text and scores
    """
    df = pd.DataFrame()
    titles = []
    review_text = []
    review_scores = []
    print("Parsing user reviews...")
    for response in responses:
        movie_data = RottenTomatoesScraper(response.content)
        titles.extend(movie_data.titles)
        review_text.extend(movie_data.review_text)
        review_scores.extend(movie_data.review_scores)
        response.close()
    data = {"Title": titles, "Review Text": review_text, "Review Score": review_scores}
    df = pd.DataFrame.from_dict(data)
    return df


if __name__ == "__main__":
    movie_tags_2019 = get_top_100_movie_tags(year=2017)
    urls = get_user_review_urls_from_tags(movie_tags_2019)
    responses = get_responses(urls)
    df: pd.DataFrame = generate_df(responses)
    df.to_csv("movie_reviews.csv")
