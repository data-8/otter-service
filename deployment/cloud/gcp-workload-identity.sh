# gcloud iam workload-identity-pools create "grader-pool" \
#   --project="data8x-scratch" \
#   --location="global" \
#   --display-name="Grader Pool"


# gcloud iam workload-identity-pools providers create-oidc "github-actions" \
#   --project="data8x-scratch" \
#   --location="global" \
#   --workload-identity-pool="grader-pool" \
#   --display-name="Grader Provider" \
#   --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.aud=assertion.aud" \
#   --issuer-uri="https://token.actions.githubusercontent.com"

# this stick around for 30 days and the name can not be reused
gcloud iam workload-identity-pools undelete "grader-pool" \
  --project="data8x-scratch" \
  --location="global" 

# this stick around for 30 days and the name can not be reused
gcloud iam workload-identity-pools providers undelete "github-actions" \
  --project="data8x-scratch" \
  --location="global" \
  --workload-identity-pool="grader-pool" 

gcloud iam service-accounts add-iam-policy-binding "grader-sa@data8x-scratch.iam.gserviceaccount.com" \
  --project="data8x-scratch" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/75088546496/locations/global/workloadIdentityPools/grader-pool/*"
