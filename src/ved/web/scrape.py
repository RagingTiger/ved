"""Scraping tools."""
import os
import re
from abc import ABC
from abc import abstractmethod
from base64 import b64decode
from base64 import b64encode
from dataclasses import dataclass
from pathlib import Path
from re import Pattern
from typing import Dict
from typing import Generator
from typing import Set
from typing import Tuple
from typing import Union
from urllib.parse import urljoin
from urllib.parse import urlparse

import requests
from basc_py4chan import Board
from basc_py4chan import Thread as ChanThread
from basc_py4chan import get_all_boards
from bs4 import BeautifulSoup
from tqdm.auto import tqdm
from youtube_dl import YoutubeDL


@dataclass
class BaseScraper(ABC):
    """Scraper abstract base class."""

    url: str

    def __post_init__(self) -> None:
        """Apply post constructor processing to args."""
        self._validate_url()

    def _validate_url(self) -> None:
        """Check that URL matches domain name."""
        assert (
            self._get_domain() in self.url
        ), f"URL ({self.url}) does not match scraping domain ({self._get_domain()})"

    def _encode_base64(self, word: str) -> bytes:
        """Encode a string to base64."""
        return b64encode(word.encode())

    def _decode_base64(self, word: bytes) -> str:
        """Decode a base 64 encoded string."""
        return b64decode(word).decode()

    def _get_domain(self) -> str:
        """Convenience utility for decode base64 domain name."""
        return self._decode_base64(self.domain)

    @property
    def youtubedl_options(self) -> Dict[str, Union[bool, int, str]]:
        """Property for default options for youtube-dl."""
        return {
            "ignoreerrors": True,
            "no_warnings": True,
            "nooverwrites": True,
            "outtmpl": self.outpath_template,
            "quiet": True,
            "restrictfilenames": True,
            "simulate": False,
            "sleep_interval": 3,
            "max_sleep_interval": 10,
        }

    @property
    def outpath_template(self) -> str:
        """Property for generating full output file path template."""
        return str(self.download_dir / self.filename_template)

    @property
    def filename_template(self) -> str:
        """Property for generating file name template."""
        return "%(title)s.%(ext)s"

    @property
    @abstractmethod
    def download_dir(self) -> Path:
        """Abstract property for directory to scrape files to."""
        pass

    @property
    @abstractmethod
    def domain(self) -> bytes:
        """Abstract property for domain name stored in base64 bytes string."""
        pass

    @abstractmethod
    def scrape(self) -> None:
        """Scrape image/video files from URL."""
        pass


class FourChanScraper(BaseScraper):
    """4chan scraper."""

    domain = b"NGNoYW4ub3Jn"
    download_dir = Path(os.getcwd()) / "scrape/4chan"
    encoded_search_words = (
        b"YmlzZXh1YWw=",
        b"Y3Jvc3NkcmVzcw==",
        b"ZmFnZw==",
        b"ZmVtYm95",
        b"bGFkeWJveQ==",
        b"c2hlbWFsZQ==",
        b"c2lzcw==",
        b"dGdpcmw=",
        b"dHJhbm4=",
        b"dHJhbnM=",
        b"dHJhcA==",
    )
    encoded_exclude_words = (
        b"YmxhY2tlZA==",
        b"aGF0ZQ==",
        b"cmVrdA==",
        b"dHJhbnNpdGlvbg==",
    )

    def __post_init__(self) -> None:
        """Need to do some additional setup for 4chan board object."""
        # get 4chan board path instance
        board_path = Path(self.url)

        # set board instance
        self.board = Board(board_path.name)

        # call parent
        super().__post_init__()

    def _validate_url(self) -> None:
        """Do additional checks on 4chan board name/path."""
        # call parent
        super()._validate_url()

        # confirm given board name is in list of boards
        assert self.board.name in [
            board.name for board in get_all_boards()
        ], f"{self.board} not found in list of 4chan boards."

    def _decode_words(self, words: Tuple[bytes, ...]) -> Tuple[str, ...]:
        """Decode base64 encoded byte strings."""
        # loop over encoded words
        return tuple(self._decode_base64(word) for word in words)

    def _encode_words(self, words: Tuple[str, ...]) -> Tuple[bytes, ...]:
        """Encode strings into base64 byte strings."""
        # loop over decoded words
        return tuple(self._encode_base64(word) for word in words)

    def _get_all_threads(self) -> Generator[ChanThread, None, None]:
        """Pull out all threads from target board."""
        yield from self.board.get_all_threads(expand=True)

    def _filter_threads(self) -> Generator[ChanThread, None, None]:
        """Scan threads of target board for keywords."""
        # decode words
        dec_search_words = self._decode_words(self.encoded_search_words)
        dec_exclude_words = self._decode_words(self.encoded_exclude_words)

        # first loop over all the threads for the given board
        for thread in self._get_all_threads():
            # now get special thread title
            thread_title = thread.semantic_slug.lower()

            # search for matches
            matches = tuple(word in thread_title for word in dec_search_words)

            # search for excluded words
            exclude = tuple(word in thread_title for word in dec_exclude_words)

            # check if any union exists
            if any(matches) and not any(exclude):
                # got a match!
                yield thread

    def scrape(self) -> None:
        """Get image/video files from 4chan threads."""
        # notify user of beginning download ...
        print(f"Downloading threads from: {self._get_domain()}/{self.board.name} ...")

        # loop over all threads in the board
        for thread in tqdm(tuple(self._filter_threads()), position=0):
            # create new download directory for each thread
            thread_dir = self.download_dir / thread.semantic_slug

            # get youtubedl options
            ytdl_opts = self.youtubedl_options

            # update custom thread download dir
            ytdl_opts["outtmpl"] = str(thread_dir / self.filename_template)

            # get youtube-dl context
            with YoutubeDL(ytdl_opts) as ytdl:
                # lopop over all file urls in thread
                for url in tqdm(
                    tuple(thread.files()),
                    desc="Downloading files",
                    position=1,
                    leave=False,
                    postfix=thread.semantic_slug,
                ):
                    # download file
                    ytdl.download([url])


class LinkScraper(BaseScraper):
    """Hyperlink scraping base class."""

    @property
    @abstractmethod
    def pattern(self) -> Pattern[str]:
        """Abstract property for a regex pattern."""
        pass

    def _extract_url_base(self) -> str:
        """Pull domain name out of user supplied URL."""
        # get parsed url
        parsed_url = urlparse(self.url)

        # recombine scheme and netloc
        return parsed_url.scheme + "://" + parsed_url.netloc

    def _get_all_links(self) -> Generator[str, None, None]:
        """Scrape all links at given URL."""
        # get HTML from web URL
        html = requests.get(self.url).text

        # get all <a> element
        soup = BeautifulSoup(html, "html.parser").find_all("a")

        # loop over <a> elements in html "soup"
        for anchor_element in soup:
            # get href
            if (href := anchor_element.get("href")) is not None:
                # generate href
                yield href

    def _get_unique_links(self) -> Set[str]:
        """Simply create a set of unique links from all scraped links."""
        return set(self._get_all_links())

    def _filter_links(self) -> Generator[str, None, None]:
        """Yield links that actually match regex pattern."""
        # get parsed user url
        url_base = self._extract_url_base()

        # loop over all the href links from given URL
        for href in self._get_unique_links():
            # check regex pattern
            match = self.pattern.match(href)

            # check if link matches
            if match is not None:
                # and yield them
                yield urljoin(url_base, href)

    def scrape(self) -> None:
        """Scrape image/video files from URL."""
        # notify user of beginning download ...
        print(f"Downloading files from: {self.url} ...")

        # get youtube-dl context
        with YoutubeDL(self.youtubedl_options) as ytdl:
            # loop over all links
            for link in tqdm(tuple(self._filter_links()), position=0):
                # download file
                ytdl.download([link])


class ASTScraper(LinkScraper):
    """Scraper for AST website."""

    domain = b"YXNoZW1hbGV0dWJlLmNvbQ=="
    download_dir = Path(os.getcwd()) / "scrape/ast"
    pattern = re.compile(r"^/videos/\d+/[a-z0-9-_]+/.*$", re.IGNORECASE)


class PHScraper(LinkScraper):
    """Scraper for PH website."""

    domain = b"cG9ybmh1Yi5jb20="
    download_dir = Path(os.getcwd()) / "scrape/ph"
    pattern = re.compile(r"^/view_video\.php.*", re.IGNORECASE)
