version=$(<src/otter_service/__init__.py)
version=${version##__version__ = }
version=`sed -e 's/^"//' -e 's/"$//' <<<"$version"`
branch_name=$(git symbolic-ref -q HEAD)
branch_name=${branch_name##refs/heads/}
branch_name=${branch_name:-HEAD}
if [ "$branch_name" == "dev" ] && [ "$1" == "build" ]; then
    python3 -m build
    python3 -m pip install dist/otter_service-${version}.tar.gz --force
    python3 -m twine upload dist/*$version*
    
    #for local dev
    yq eval ".services.app.build.args.OTTER_SERVICE_VERSION=\"$version\"" -i docker-compose.yml
    # if breaks on Permission denied run: gcloud auth login
    # build and push otter-srv
    gcloud builds submit --substitutions=_TAG_NAME=$version --config ./deployment/cloud/cloudbuild.yaml
fi
ns=$(kubectl get namespaces | grep otter-${branch_name})
sops -d -i --ignore-mac ./otter-service/values.yaml
if [[ $ns == *"otter-${branch_name}"* ]]; then
    helm upgrade --install otter-srv --set otter_srv.tag=$version otter-service --values otter-service/values.yaml --values otter-service/values.$branch_name.yaml --namespace otter-$branch_name --skip-crds 
else
    # Use this when namespace completely deleted
    helm install otter-srv --set otter_srv.tag=$version otter-service --values otter-service/values.yaml --values otter-service/values.$branch_name.yaml --create-namespace --namespace otter-$branch_name --skip-crds 
fi
git checkout -- ./otter-service/values.yaml

