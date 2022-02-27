# Kubernetes config:
gcloud container clusters get-credentials grader-cluster --region=us-central1
kubectl create namespace grader-k8-namespace
kubectl create serviceaccount --namespace grader-k8-namespace grader-k8-sa

#This is added to the yaml creating the Pod:
#spec:
#  serviceAccountName: grader-k8-sa

#GCP config:
gcloud iam service-accounts create grader-sa

#Add all the roles we need:
gcloud projects add-iam-policy-binding data8x-scratch \
    --member "serviceAccount:grader-sa@data8x-scratch.iam.gserviceaccount.com" \
    --role "roles/editor"

gcloud projects add-iam-policy-binding data8x-scratch \
    --member "serviceAccount:grader-sa@data8x-scratch.iam.gserviceaccount.com" \
    --role "roles/cloudkms.cryptoKeyEncrypterDecrypter"


#Tie the K8 SA to GCloud SA:
#Allow impersonation:
gcloud iam service-accounts add-iam-policy-binding grader-sa@data8x-scratch.iam.gserviceaccount.com \
    --role roles/iam.workloadIdentityUser \
    --member "serviceAccount:data8x-scratch.svc.id.goog[grader-k8-namespace/grader-k8-sa]"


#Annotate the K8 Service account:
kubectl annotate serviceaccount \
        --namespace grader-k8-namespace grader-k8-sa \
        iam.gke.io/gcp-service-account=grader-sa@data8x-scratch.iam.gserviceaccount.com
