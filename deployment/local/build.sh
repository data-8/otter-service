version=$(<src/otter_service/__init__.py)
version=${version##__version__ = }
version=`sed -e 's/^"//' -e 's/"$//' <<<"$version"`
cp -R ../otter-grader ./otter-grader
python3 -m build
python3 -m pip install dist/otter_service-${version}.tar.gz --force
docker-compose build
rm -rf ./otter-grader
docker-compose up
