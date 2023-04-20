"""
Creates a playlist for a given artist sorted by popularity.

Specify the following environment variables before starting this script.
export SPOTIPY_CLIENT_ID='your-spotify-client-id'
export SPOTIPY_CLIENT_SECRET='your-spotify-client-secret'
export SPOTIPY_REDIRECT_URI='your-app-redirect-url'  # e.g. http://localhost
export SPOTIPY_USERNAME='your-username'
"""
import os
from itertools import chain
from pprint import pprint
from typing import Generator, List, TypeVar

from fuzzywuzzy import fuzz, process  # type: ignore[import]
from spotipy import Spotify  # type: ignore[import]
from spotipy.oauth2 import SpotifyClientCredentials  # type: ignore[import]
from spotipy.oauth2 import SpotifyOAuth

from spotify_popularity_playlist.spotify_types import (
    Album,
    AlbumMatch,
    Artist,
    ArtistAlbums,
    Scorer,
)

ARTIST = "artist"
ARTISTS = f"{ARTIST}s"
TRACKS = "tracks"
ARTIST_CHUNK_SIZE = 20
TRACK_CHUNK_SIZE = 50
PLAYLIST_CHUNK_SIZE = 100
USERNAME = os.environ["SPOTIPY_USERNAME"]
DEFAULT_SCOPE = Spotify(client_credentials_manager=(SpotifyClientCredentials()))


def spotify_scope(scope_name: str) -> Spotify:
    """
    Create a Spotify object with a particular scope.

    :param scope_name: name of the scope
    :return: Spotify object at a specific scope
    """
    scope = Spotify(auth_manager=SpotifyOAuth(scope=scope_name))
    scope.trace = False
    return scope


def artists_search(artist_name: str) -> List[Artist]:
    """
    Return a list of Artists from a spotify search.

    :param artist_name: name of the artist to search
    :return: List[Artist]
    """
    artists: List[Artist] = DEFAULT_SCOPE.search(
        q=f"{ARTIST}:{artist_name}", type=ARTIST, limit=15
    )[ARTISTS]["items"]
    return artists


def simplified_artist_albums(
    first_page_simplified_artist_albums: ArtistAlbums,
) -> List[Album]:
    """
    Gets all simplified artist albums via pagination.

    :param first_page_simplified_artist_albums: ArtistAlbums
    :return: List[Album]
    """
    cur_page_simplified_artist_albums = first_page_simplified_artist_albums
    all_simplified_artist_albums = cur_page_simplified_artist_albums["items"]
    while cur_page_simplified_artist_albums["next"] is not None:
        cur_page_simplified_artist_albums = DEFAULT_SCOPE.next(
            cur_page_simplified_artist_albums
        )
        all_simplified_artist_albums.extend(cur_page_simplified_artist_albums["items"])
    return all_simplified_artist_albums


def deduplicate_by_name_and_add_popularity(
    albums: List[Album],
    threshold: int = 99,
    scorer: Scorer = fuzz.token_set_ratio,
) -> List[Album]:
    """
    Adapted from fuzzywuzzy dedupe function. Does string comparison on names but we
    index tracks by their unique id. Returns a list of albums sorted by popularity.

    :param albums: List[Album]
    :param threshold: int
    :param scorer: Scorer, fuzz.token_set_ratio seems to work well for song titles.
    :return: List[Album]
    """
    extractor_album_ids = []
    album_id_dict = {album["id"]: album.copy() for album in albums}
    dupe_album_id_names_dict = {album["id"]: album["name"] for album in albums}
    for item in albums:
        # return all duplicate album_matches found
        album_matches = [
            AlbumMatch(album_name=album_name, score=score, album_id=album_id)
            for album_name, score, album_id in process.extract(
                query=item["name"],
                choices=dupe_album_id_names_dict,
                limit=None,
                scorer=scorer,
            )
        ]
        # filter album_matches based on the threshold
        filtered_album_matches = [
            album_match
            for album_match in album_matches
            if album_match.score > threshold
        ]
        # if there is only 0 or 1 items in *filtered*, no duplicates were found so
        # append to *extracted*. match[2] is an id.
        if len(filtered_album_matches) == 1 or not [
            i.album_id
            for i in filtered_album_matches
            if i.album_id in extractor_album_ids
        ]:
            extractor_album_ids.append(item["id"])

    # check that extractor differs from contain_dupes (e.g. duplicates were found)
    # if not, then return the original list
    return (
        sorted(
            [album_id_dict[album_id] for album_id in extractor_album_ids],
            key=lambda d: d["popularity"],
            reverse=True,
        )
        if len(extractor_album_ids) != len(albums)
        else albums
    )


T = TypeVar("T")
"""Represents a homogenous member of a list"""


def chunks(list_: List[T], chunk_size: int) -> Generator[List[T], None, None]:
    """
    Yield successive n-sized chunks from list_.

    :param list_: List
    :param chunk_size: int
    :return: Generator[List, None, None]
    """
    for idx in range(0, len(list_), chunk_size):
        yield list_[idx : idx + chunk_size]


def create_top_tracks_playlist(username: str, artist: Artist) -> None:
    """
    Create the top tracks playlist for an artist for a particular authenticated user.
    We deduplicate a little after we get full track information so that the most popular
    unique track is at the top. `simplified` refers to the simplified object returned by
    the spotify api by particular functions.

    Ideally there would be an easy way to combine the popularity of two identical tracks
    to boost that track's popularity but track popularity isn't strictly linear, so
    scores of 100+ could then occur.
    :param username: str
    :param artist: Artist
    :return: None
    """
    artist_album_ids = [
        artist_album["id"]
        for artist_album in simplified_artist_albums(
            DEFAULT_SCOPE.artist_albums(artist["id"], limit=50)
        )
    ]
    artist_albums = list(
        chain(
            *[
                DEFAULT_SCOPE.albums(album_ids_chunk)["albums"]
                for album_ids_chunk in chunks(artist_album_ids, ARTIST_CHUNK_SIZE)
            ]
        )
    )
    # Iterate through album tracks and only take ones matching that artist
    artist_simplified_track_ids = [
        track["id"]
        for track in list(chain(*[album[TRACKS]["items"] for album in artist_albums]))
        if artist["id"] in (track_artist["id"] for track_artist in track[ARTISTS])
    ]

    artist_tracks = list(
        chain(
            *[
                DEFAULT_SCOPE.tracks(track_ids_chunk)[TRACKS]
                for track_ids_chunk in chunks(
                    artist_simplified_track_ids, TRACK_CHUNK_SIZE
                )
            ]
        )
    )
    artist_tracks_by_popularity = deduplicate_by_name_and_add_popularity(
        sorted(artist_tracks, key=lambda track: track["popularity"], reverse=True),
        threshold=99,
        scorer=fuzz.token_sort_ratio,
    )
    playlist_modify_public_scope = spotify_scope("playlist-modify-public")
    new_playlist = playlist_modify_public_scope.user_playlist_create(
        user=username, name=artist["name"] + " by Popularity"
    )
    for track_ids_chunk in chunks(
        [track["id"] for track in artist_tracks_by_popularity], PLAYLIST_CHUNK_SIZE
    ):
        playlist_modify_public_scope.playlist_add_items(
            playlist_id=new_playlist["id"], items=track_ids_chunk
        )
    print(f"Popularity playlist created for: {artist}")


def main() -> None:
    """
    Main function for popularity_playlist.py

    :return: None
    """
    # genre_artists = get_genre_artists("pirate")
    while True:
        artist_name = input("Enter an artist name: ")
        if not artist_name:
            exit("Enter an artist name!")
        artist_results = artists_search(artist_name)
        if not artist_results:
            print("No results...")
            continue
        # Prettily print a numbered list of of artists with index numbers to select from
        pprint(
            [
                f"{idx}: {i['name']} ({i['genres']})"
                for idx, i in enumerate(artist_results)
            ]
        )
        artist_idx = int(
            input("Select the number of the artist you want (default 0): ") or "0"
        )
        create_top_tracks_playlist(USERNAME, artist_results[artist_idx])
        more_artists = input("Do you want to create another playlist (y/n)?")
        if more_artists not in ["y", "\n"]:
            break


if __name__ == "__main__":
    main()
