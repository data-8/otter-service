# version=$(<src/gofer_service/__init__.py)
# version=${version##__version__ = }
# version=`sed -e 's/^"//' -e 's/"$//' <<<"$version"`
# python3 -m twine upload dist/*$version*

# github_key=$(sops -d src/gofer_service/secrets/gh_key.yaml)
# github_key=${github_key##github_access_token: }
# gcloud builds submit --substitutions=_GITHUB_KEY=$github_key,_TAG_NAME=$version  --config ./deployment/cloud/cloudbuild.yaml

branch_name=$(git symbolic-ref -q HEAD)
branch_name=${branch_name##refs/heads/}
branch_name=${branch_name:-HEAD}
export KUBECONFIG=./kube-context
gcloud container clusters get-credentials gofer-cluster --region us-central1 --project data8x-scratch
kubectl config use "gke_data8x-scratch_us-central1_gofer-cluster"
if [ "$branch_name" == "staging" -o "$branch_name" == "prod" -o "$branch_name" == "dev" ]; then
    NFS_IP=$(gcloud compute addresses list --filter="name=( 'gofer-nfs-$branch_name-private-ip')" --format="get(address)" 2>&1)
    LB_IP=$(gcloud compute addresses list --filter="name=( 'gofer-v2-external-ip-$branch_name')" --format="get(address)" 2>&1)
    NAMESPACE=gofer-$branch_name
    kubectl config set-context --current --namespace=$NAMESPACE
    kubectl create namespace $NAMESPACE --save-config --dry-run=client -o yaml | kubectl apply -f -
    ./deployment/cloud/deploy-service-account.sh
    
    #yq eval ".spec.nfs.server=\"$NFS_IP\"" -i deployment/cloud/deployment-nfs-volume.yaml
    yq eval ".metadata.name=\"gofer-nfs-volume-$branch_name\"" -i deployment/cloud/deployment-nfs-volume.yaml
    
    kubectl apply -f ./deployment/cloud/deployment-nfs-volume.yaml 
    kubectl apply -f ./deployment/cloud/deployment-nfs-volume-claim.yaml

    kubectl apply -f ./deployment/cloud/deployment-nfs-gke.yaml
    kubectl apply -f ./deployment/cloud/deployment-nfs-service.yaml 

    # yq eval ".spec.nfs.server=\"$NFS_IP\"" -i deployment/cloud/deployment-persistent-volume.yaml
    # yq eval ".metadata.name=\"gofer-volume-$branch_name\"" -i deployment/cloud/deployment-persistent-volume.yaml
    
    # kubectl apply -f ./deployment/cloud/deployment-persistent-volume.yaml 
    # kubectl apply -f ./deployment/cloud/deployment-persistent-volume-claim.yaml
    
    # we ignore the checksum so that clear text values can be changes for deployments -- like POST_GRADE can can be made false
    # for testing and more
    # sops -d --ignore-mac ./deployment/cloud/deployment-config-encrypted.yaml | kubectl apply -f -
    # kubectl apply -f ./deployment/cloud/deployment.yaml
    
    # yq eval ".spec.loadBalancerIP=\"$LB_IP\"" -i deployment/cloud/deployment-service.yaml
    # kubectl apply -f ./deployment/cloud/deployment-service.yaml

    # kubectl apply -f ./deployment/cloud/deployment-autoscale-vertical-pod-rec.yaml
    # kubectl apply -f ./deployment/cloud/deployment-autoscale-horizontal-pod.yaml

    # ./deployment/cloud/gcp-workload-identity.sh
fi
rm -f ./kube-context