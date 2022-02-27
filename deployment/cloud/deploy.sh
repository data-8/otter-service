version=$(<src/gofer_service/__init__.py)
version=${version##__version__ = }
version=`sed -e 's/^"//' -e 's/"$//' <<<"$version"`
python3 -m twine upload dist/*$version*

github_key=$(sops -d src/gofer_service/secrets/gh_key.yaml)
github_key=${github_key##github_access_token: }
gcloud builds submit --substitutions=_GITHUB_KEY=$github_key  --config ./deployment/cloud/cloudbuild.yaml

./deployment/cloud/deploy-service-account.sh
kubectl apply -f ./deployment/cloud/deployment-persistent-volume.yaml
# we ignore the checksum so that clear text values can be changes for deployments -- like POST_GRADE can can be made false
# for testing
sops -d --ignore-mac ./deployment/cloud/deployment-config-encrypted.yaml | kubectl apply -f -
kubectl apply -f ./deployment/cloud/deployment.yaml
kubectl apply -f ./deployment/cloud/deployment-service.yaml
