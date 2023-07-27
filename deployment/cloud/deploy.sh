version=$(<src/otter_service/__init__.py)
version=${version##__version__ = }
version=`sed -e 's/^"//' -e 's/"$//' <<<"$version"`
branch_name=$(git symbolic-ref -q HEAD)
branch_name=${branch_name##refs/heads/}
branch_name=${branch_name:-HEAD}

JUPYTERHUB_BASE_URL=https://hubv2.data8x.berkeley.edu
if [ "$branch_name" == "staging" ]; then
    JUPYTERHUB_BASE_URL=https://hubv2-staging.data8x.berkeley.edu
fi
JUPYTERHUB_API_URL="$JUPYTERHUB_BASE_URL/hub/api"

if [ "$branch_name" == "dev" ] && [ "$1" == "build" ]; then
    python3 -m build
    python3 -m pip install dist/otter_service-${version}.tar.gz --force
    python3 -m twine upload dist/*$version*
    
    yq eval ".services.app.build.args.OTTER_SERVICE_VERSION=\"$version\"" -i docker-compose.yml
    # if breaks on Permission denied run: gcloud auth login
    gcloud builds submit --substitutions=_TAG_NAME=$version --config ./deployment/cloud/cloudbuild.yaml
fi

export KUBECONFIG=./kube-context
# gcloud container --project "data8x-scratch" clusters create-auto "otter-cluster" --region "us-central1" --release-channel "regular" --network "projects/data8x-scratch/global/networks/default" --subnetwork "projects/data8x-scratch/regions/us-central1/subnetworks/default"
gcloud container clusters get-credentials otter-cluster-v3 --region us-central1 --project data8x-scratch                  
kubectl config use "gke_data8x-scratch_us-central1-c_otter-cluster-v3"
if [ "$branch_name" == "staging" -o "$branch_name" == "prod" -o "$branch_name" == "dev" ]; then
    #NFS_IP=$(gcloud compute addresses list --filter="name=( 'otter-nfs-$branch_name-private-ip')" --format="get(address)" 2>&1)
    LB_IP=$(gcloud compute addresses list --filter="name=( 'otter-lb-external-ip-$branch_name')" --format="get(address)" 2>&1)
    NAMESPACE=otter-$branch_name
    kubectl config set-context --current --namespace=$NAMESPACE
    kubectl create namespace $NAMESPACE --save-config --dry-run=client -o yaml | kubectl apply -f -
    #echo "NFS IP: ${NFS_IP}"
    echo "LB IP: ${LB_IP}"
    ./deployment/cloud/deploy-service-account.sh
    
    kubectl apply -f ./deployment/cloud/deploy-storage-class.yaml
    kubectl apply -f ./deployment/cloud/deployment-opt-persistent-volume-claim.yaml
    kubectl apply -f ./deployment/cloud/deployment-tmp-persistent-volume-claim.yaml

    yq eval ".data.ENVIRONMENT=\"$NAMESPACE\"" -i ./deployment/cloud/deployment-config-encrypted.yaml
    yq eval ".data.JUPYTERHUB_BASE_URL=\"$JUPYTERHUB_BASE_URL\"" -i ./deployment/cloud/deployment-config-encrypted.yaml
    yq eval ".data.JUPYTERHUB_API_URL=\"$JUPYTERHUB_API_URL\"" -i ./deployment/cloud/deployment-config-encrypted.yaml
#     #we ignore the checksum so that clear text values can be changes for deployments -- like POST_GRADE can can be made false
#     #for testing and more
    sops -d --ignore-mac ./deployment/cloud/deployment-config-encrypted.yaml | kubectl apply -f -
    
    yq -i ".spec.template.spec.containers[0].image = \"gcr.io/data8x-scratch/otter-srv:${version}\"" ./deployment/cloud/deployment.yaml 
    kubectl apply -f ./deployment/cloud/deployment.yaml
    
    kubectl set image deployment/otter-pod -n otter-$branch_name otter-srv=gcr.io/data8x-scratch/otter-srv:$version
    
    yq eval ".spec.loadBalancerIP=\"$LB_IP\"" -i deployment/cloud/deployment-service.yaml
    kubectl apply -f ./deployment/cloud/deployment-service.yaml
    
    kubectl apply -f ./deployment/cloud/deployment-autoscale-horizontal-pod.yaml

    ./deployment/cloud/gcp-workload-identity.sh
    
    git checkout -- deployment/cloud/deployment-service.yaml
    git checkout -- deployment/cloud/deployment-config-encrypted.yaml
fi
rm -f ./kube-context