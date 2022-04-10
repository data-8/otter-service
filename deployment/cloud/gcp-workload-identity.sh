WORKLOAD_ID_POOL_OUT=$(gcloud iam workload-identity-pools describe "grader-pool" \
  --project="data8x-scratch" \
  --location="global" 2>&1)

WORKLOAD_ID_POOL_PROVIDERS_OUT=$(gcloud iam workload-identity-pools providers describe "github-actions" \
  --project="data8x-scratch" \
  --location="global" \
  --workload-identity-pool="grader-pool" 2>&1)

if [[ $WORKLOAD_ID_POOL_OUT =~ "DELETED" ]]; then
  # this stick around for 30 days and the name can not be reused
  gcloud iam workload-identity-pools undelete "grader-pool" \
    --project="data8x-scratch" \
    --location="global"
  echo Workload Identity Pools: grader-pool: UnDeleted and Active
elif [[ $WORKLOAD_ID_POOL_OUT =~ "NOT_FOUND" ]]; then
  gcloud iam workload-identity-pools create "grader-pool" \
    --project="data8x-scratch" \
    --location="global" \
    --display-name="Grader Pool"
  echo Workload Identity Pools: grader-pool: Created
else
  echo Workload Identity Pools: grader-pool: Active
fi

if [[ $WORKLOAD_ID_POOL_PROVIDERS_OUT =~ "DELETED" ]]; then
  # this stick around for 30 days and the name can not be reused
  gcloud iam workload-identity-pools providers undelete "github-actions" \
    --project="data8x-scratch" \
    --location="global" \
    --workload-identity-pool="grader-pool"
  echo Workload Identity Pools Prividers: github-actions: UnDeleted and Active
elif [[ $WORKLOAD_ID_POOL_PROVIDERS_OUT =~ "NOT_FOUND" ]]; then
    gcloud iam workload-identity-pools providers create-oidc "github-actions" \
    --project="data8x-scratch" \
    --location="global" \
    --workload-identity-pool="grader-pool" \
    --display-name="Grader Provider" \
    --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.aud=assertion.aud" \
    --issuer-uri="https://token.actions.githubusercontent.com"
    echo Workload Identity Pools Prividers: github-actions: Created
else
  echo Workload Identity Pools Providers: OIDC for github-actions: Active
fi

gcloud iam service-accounts add-iam-policy-binding "grader-sa@data8x-scratch.iam.gserviceaccount.com" \
  --project="data8x-scratch" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/75088546496/locations/global/workloadIdentityPools/grader-pool/*" \
  --no-user-output-enabled

echo Workload identity Pools: Updated IAM policy for serviceAccount grader-sa