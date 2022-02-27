version=$(<src/gofer_service/__init__.py)
version=${version##__version__ = }
version=`sed -e 's/^"//' -e 's/"$//' <<<"$version"`
python3 -m build
python3 -m pip install dist/gofer-service-${version}.tar.gz --force
docker-compose build
docker-compose up