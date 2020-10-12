import codecs
import os
import re
from setuptools import setup


with open("README.md", "r") as fh:
    long_description = fh.read()


here = os.path.abspath(os.path.dirname(__file__))


def find_version(*file_paths):
    with codecs.open(os.path.join(here, *file_paths), "r") as fp:
        version_file = fp.read()
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


setup(
    name="subpiper",
    version=find_version(r"subpiper", "__init__.py"),
    description="Subprocess wrapper for separate, unbuffered capturing / redirecting of stdout and stderr",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/waszil/subpiper",
    author="csaba.nemes",
    author_email="waszil.waszil@gmail.com",
    license="GPLv3",
    packages=["subpiper"],
    install_requires=[],
    setup_requires=["pytest-runner"],
    tests_require=["pytest"],
    zip_safe=False,
)
