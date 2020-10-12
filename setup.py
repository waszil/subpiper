from setuptools import setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="subpiper",
    version="0.2",
    description="Subprocess wrapper for separate, unbuffered capturing / redirecting of stdout and stderr",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/waszil/subpiper",
    author="csaba.nemes",
    author_email="waszil.waszil@gmail.com",
    license="GPL",
    packages=["subpiper"],
    install_requires=[],
    zip_safe=False,
)
