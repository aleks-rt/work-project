import os
from dotenv import load_dotenv
from .hh import HHScraper
from .getmatch import GetMatchScraper
from .habr import HabrCareerScraper
from .superjob import SuperjobScraper
from .linkedin import LinkedInScraper
from .trudvsem import TrudvsemScraper
from .rabota import RabotaScraper

load_dotenv("credentials.env")

_ALL = [
    ("SITE_HH", HHScraper),
    ("SITE_HABR", HabrCareerScraper),
    ("SITE_GETMATCH", GetMatchScraper),
    ("SITE_SUPERJOB", SuperjobScraper),
    ("SITE_LINKEDIN", LinkedInScraper),
    ("SITE_TRUDVSEM", TrudvsemScraper),
    ("SITE_RABOTA", RabotaScraper),
]

ALL_SCRAPERS = [
    cls for key, cls in _ALL
    if os.getenv(key, "true").strip().lower() == "true"
]
