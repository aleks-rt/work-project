import os
from dotenv import load_dotenv
from .hh import HHScraper
from .getmatch import GetMatchScraper
from .habr import HabrCareerScraper
from .superjob import SuperjobScraper
from .linkedin import LinkedInScraper

load_dotenv("credentials.env")

_ALL = [
    ("SITE_HH", HHScraper),
    ("SITE_HABR", HabrCareerScraper),
    ("SITE_GETMATCH", GetMatchScraper),
    ("SITE_SUPERJOB", SuperjobScraper),
    ("SITE_LINKEDIN", LinkedInScraper),
]

ALL_SCRAPERS = [
    cls for key, cls in _ALL
    if os.getenv(key, "true").strip().lower() == "true"
]
