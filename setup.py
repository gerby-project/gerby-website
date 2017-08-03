from setuptools import setup

setup(
    name="gerby",
    packages=["gerby"],
    include_package_data=True,
    install_requires=[
        "flask",
        "peewee",
    ],
)
