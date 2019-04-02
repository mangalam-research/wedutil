from setuptools import setup, find_packages

setup(
    name="wedutil",
    version="0.22.1",
    packages=find_packages(),
    author="Louis-Dominique Dubeau",
    author_email="ldd@lddubeau.com",
    description="Utilities for testing wed with Selenium.",
    license="MPL 2.0",
    keywords=["wed", "selenium", "testing"],
    url="https://github.com/mangalam-research/wedutil",
    classifiers=[
        "Programming Language :: Python :: 3 :: Only",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)",
        "Operating System :: POSIX",
        "Topic :: Software Development :: Testing",
        "Topic :: Software Development :: Quality Assurance"
    ],
)
