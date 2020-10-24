import codecs
import os
import os.path

from setuptools import setup  # type: ignore[import]

_here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(_here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()


def get_version(rel_path):
    with codecs.open(os.path.join(_here, rel_path), "r") as fp:
        for line in fp.read().splitlines():
            if line.startswith("__version__"):
                return line.split('"' if '"' in line else "'")[1]
        else:
            raise RuntimeError("Unable to find version string.")


with open("requirements.txt") as f:
    required = f.read().splitlines()

PACKAGE_NAME = "spotify_popularity_playlist"

setup(
    name=PACKAGE_NAME,
    version=get_version(f"{PACKAGE_NAME}/__init__.py"),
    description="Why listen to only the top 10 most popular songs when you can listen "
    "to an artist's most popular songs from start to finish?",
    long_description=long_description,
    author="Aaron Sewall",
    author_email="aaronsewall@example.com",
    url="https://github.com/aaronsewall/spotify-popularity-playlist",
    license="MPL-2.0",
    packages=[PACKAGE_NAME],
    install_requires=required,
    entry_points={
        "console_scripts": [
            f"{PACKAGE_NAME} = {PACKAGE_NAME}.popularity_playlist:popularity_playlist",
        ],
    },
    include_package_data=True,
    classifiers=["Programming Language :: Python :: 3.6"],
)
