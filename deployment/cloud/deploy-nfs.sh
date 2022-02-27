Reference: https://medium.com/@ngoodger_7766/nfs-filestore-on-gcp-for-free-859593e18bdf

gcloud compute addresses create gofer-nfs-private-ip \
    --addresses 10.128.0.31 \
    --region us-central1 \
    --subnet default

gcloud compute instances create gofer-nfs-server --private-network-ip=10.128.0.31 --boot-disk-size=30GB \
 --image=ubuntu-2004-focal-v20220308 --image-project=ubuntu-os-cloud --machine-type=f1-micro --tags=nfs
gcloud compute ssh nfs-server --zone=us-central1-c
sudo apt install -y nfs-kernel-server
sudo mkdir /data
sudo chown nobody:nogroup /data
sudo chmod 777 /data
sudo vim /etc/exports
/data *(rw,sync,no_subtree_check)
sudo systemctl restart nfs-kernel-server
gcloud compute firewall-rules create nfs --allow=tcp:111,udp:111,tcp:2049,udp:2049 --target-tags=nfs



