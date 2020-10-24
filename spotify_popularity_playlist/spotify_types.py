from typing import List, NamedTuple, Optional

from mypy_extensions import TypedDict
from typing_extensions import Protocol


class ExternalUrls(TypedDict):
    """External URLs dict"""

    spotify: str


class Followers(TypedDict):
    """Followers dict"""

    href: Optional[str]
    total: int


class Image(TypedDict):
    """Image dict"""

    height: int
    url: str
    width: int


class Artist(TypedDict):
    """Artist dict"""

    external_urls: ExternalUrls
    followers: Followers
    genres: List[str]
    href: Optional[str]
    id: str
    images: List[Image]
    name: str
    popularity: int
    type: str
    uri: str


class Album(TypedDict, total=False):
    """Album dict, popularity in in a full Album dict"""

    album_group: str
    album_type: str
    artists: List[Artist]
    available_markets: List[str]
    external_urls: ExternalUrls
    href: str
    id: str
    images: List[Image]
    name: str
    popularity: int
    release_date: str
    release_date_precision: str
    total_tracks: int
    type: str
    uri: str


class ArtistAlbums(TypedDict):
    """Artist Albums dict"""

    href: str
    items: List[Album]
    limit: int
    next: str
    offset: int
    previous: str
    total: int


class Scorer(Protocol):
    def token_set_ratio(
        self, s1: str, s2: str, force_ascii: bool = True, full_process: bool = True
    ) -> int:
        ...


class AlbumMatch(NamedTuple):
    """Represent album names matched by fuzzywuzzy"""

    album_name: str
    score: int
    album_id: str
