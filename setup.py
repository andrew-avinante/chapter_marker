from setuptools import find_packages, setup

with open("VERSION") as version_file:
    version = version_file.read().strip()

setup(
    name="chapter-svc",
    version=version,
    packages=find_packages(),
    include_package_data=True,
    install_requires=["kafka-python", "media-lib", "ffmpeg-python"],
    entry_points={
        "console_scripts": [
            "chapter-svc=src.app:main"
        ]
    },
)
