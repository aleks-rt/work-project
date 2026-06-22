from .hh import HHScraper
from .getmatch import GetMatchScraper
from .habr import HabrCareerScraper
from .superjob import SuperjobScraper
from .linkedin import LinkedInScraper

ALL_SCRAPERS = [
    HHScraper,
    GetMatchScraper,
    HabrCareerScraper,
    SuperjobScraper,
    LinkedInScraper,
]
