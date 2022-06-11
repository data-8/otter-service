Reference: https://medium.com/@ngoodger_7766/nfs-filestore-on-gcp-for-free-859593e18bdf

# gcloud compute addresses create otter-lb-external-ip-dev --project=data8x-scratch --region=us-central1
# gcloud compute addresses create otter-lb-external-ip-staging --project=data8x-scratch --region=us-central1
# gcloud compute addresses create otter-lb-external-ip-prod --project=data8x-scratch --region=us-central1

gcloud compute addresses create otter-nfs-prod-private-ip \
    --addresses 10.128.0.35 \
    --region us-central1 \
    --subnet default

gcloud compute addresses create otter-nfs-staging-private-ip \
    --addresses 10.128.0.36 \
    --region us-central1 \
    --subnet default

gcloud compute addresses create otter-nfs-dev-private-ip \
    --addresses 10.128.0.37 \
    --region us-central1 \
    --subnet default

gcloud compute instances create otter-nfs-prod --private-network-ip=10.128.0.35 --boot-disk-size=30GB \
 --image=ubuntu-2004-focal-v20220308 --image-project=ubuntu-os-cloud --machine-type=f1-micro --tags=nfs

gcloud compute instances create otter-nfs-staging --private-network-ip=10.128.0.36 --boot-disk-size=10GB \
 --image=ubuntu-2004-focal-v20220308 --image-project=ubuntu-os-cloud --machine-type=f1-micro --tags=nfs

gcloud compute instances create otter-nfs-dev --private-network-ip=10.128.0.37 --boot-disk-size=10GB \
 --image=ubuntu-2004-focal-v20220308 --image-project=ubuntu-os-cloud --machine-type=f1-micro --tags=nfs

gcloud compute ssh otter-nfs-prod --zone=us-central1-c
gcloud compute ssh otter-nfs-staging --zone=us-central1-c
gcloud compute ssh otter-nfs-dev --zone=us-central1-c

sudo apt install -y nfs-kernel-server
sudo mkdir /data
sudo chown nobody:nogroup /data
sudo chmod 777 /data
sudo vim /etc/exports
/data *(rw,sync,no_subtree_check)
sudo systemctl restart nfs-kernel-server


gcloud compute firewall-rules create nfs --allow=tcp:111,udp:111,tcp:2049,udp:2049 --target-tags=nfs



