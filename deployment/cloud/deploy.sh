version=$(<src/otter_service/__init__.py)
version=${version##__version__ = }
version=`sed -e 's/^"//' -e 's/"$//' <<<"$version"`
#python3 -m twine upload dist/*$version*
# gcloud container --project "data8x-scratch" clusters create-auto "otter-cluster" --region "us-central1" --release-channel "regular" --network "projects/data8x-scratch/global/networks/default" --subnetwork "projects/data8x-scratch/regions/us-central1/subnetworks/default"
github_key=$(sops -d src/otter_service/secrets/gh_key.yaml)
github_key=${github_key##github_access_token: }
# if breaks on Permission denied run: gcloud auth login
# gcloud builds submit --substitutions=_GITHUB_KEY=$github_key,_TAG_NAME=$version  --config ./deployment/cloud/cloudbuild.yaml

branch_name=$(git symbolic-ref -q HEAD)
branch_name=${branch_name##refs/heads/}
branch_name=${branch_name:-HEAD}
export KUBECONFIG=./kube-context
gcloud container clusters get-credentials otter-cluster --region us-central1 --project data8x-scratch                  
kubectl config use "gke_data8x-scratch_us-central1_otter-cluster"
if [ "$branch_name" == "staging" -o "$branch_name" == "prod" -o "$branch_name" == "dev" ]; then
    NFS_IP=$(gcloud compute addresses list --filter="name=( 'otter-nfs-$branch_name-private-ip')" --format="get(address)" 2>&1)
    LB_IP=$(gcloud compute addresses list --filter="name=( 'otter-lb-external-ip-$branch_name')" --format="get(address)" 2>&1)
    NAMESPACE=otter-$branch_name
    kubectl config set-context --current --namespace=$NAMESPACE
    kubectl create namespace $NAMESPACE --save-config --dry-run=client -o yaml | kubectl apply -f -
    echo "NFS IP: ${NFS_IP}"
    echo "LB IP: ${LB_IP}"
    ./deployment/cloud/deploy-service-account.sh
    
    yq eval ".spec.nfs.server=\"$NFS_IP\"" -i deployment/cloud/deployment-persistent-volume.yaml
    yq eval ".metadata.name=\"otter-volume-$branch_name\"" -i deployment/cloud/deployment-persistent-volume.yaml
    
    kubectl apply -f ./deployment/cloud/deployment-persistent-volume.yaml 
    kubectl apply -f ./deployment/cloud/deployment-persistent-volume-claim.yaml
    
    #we ignore the checksum so that clear text values can be changes for deployments -- like POST_GRADE can can be made false
    #for testing and more
    sops -d --ignore-mac ./deployment/cloud/deployment-config-encrypted.yaml | kubectl apply -f -
    kubectl apply -f ./deployment/cloud/deployment.yaml

    yq eval ".spec.loadBalancerIP=\"$LB_IP\"" -i deployment/cloud/deployment-service.yaml
    kubectl apply -f ./deployment/cloud/deployment-service.yaml

    kubectl apply -f ./deployment/cloud/deployment-autoscale-vertical-pod-rec.yaml
    kubectl apply -f ./deployment/cloud/deployment-autoscale-horizontal-pod.yaml

    ./deployment/cloud/gcp-workload-identity.sh
fi
rm -f ./kube-context