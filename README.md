# otter-nb service

This repo contains a tornado flask app that accepts .ipynb files and grades them in a dockerized environment. Assuming you are running a Jupyterhub, you can ask Jupyterhub to run this otter-service as a service; you also have the option to run it in a stand alone manner. Grades are saved to a gcloud Cloud Firestore.

A separate Jupyterhub extension, [gofer_submit](https://github.com/data-8/gofer_submit), presents a "Submit" button to the user in a notebook rendered in Jupyterhub. The button is configured to serialize and send the notebook to this otter-service as well as notify the the user of the successful submission.

# FireStore/Database setup

All grades are written to gcloud Cloud FireStore. During local testing with pytest, the tests remove the collection created after verifying the data was written. Local docker testing, does not delete the entries but the collection is called, otter-docker-local-test, and can be viewed and deleted by going to the gcloud console and navigating to Cloud Firebase or Cloud Firestore.

# Configuration

## Notebook(ipynb metadata)
The ipynb notebooks need to include the metadata for which assignment they are. In the case of Data 8x, there are three pieces of information that are relevant: the course id, section and lab. These are set in the metadata section of every notebook:
```
metadata:{
    "course": "8x",
    "section": "1",
    "lab": "lab01"
    ...
}
```

## Course config path
Please see the repository `data-8/materials-x22-private`. The repository houses a config file, 8x_course_config_edge.json and 8x_course_config.json. The system relies on this file specified in the environment variable, `COURSE_CONFIG_PATH`, to know which lab is associated with which assignment id in EdX. If you are not posting grades to an LTI server, than you do not need to worry about this.


## Test files
This gets tricky. The notebooks and the corresponding test files used by this service are of course connected. The files `Dockerfile` and `Dockerfile-dev` (used for local testing) download the current set of test files from the repository, `materials-x22-private`, for the `materials-x22` notebooks. If you bring in different notebooks, you would need to change the two dockerfiles to bring in the corresponding tests. 

We assume a specific path to the test files. If you mirror the path found in the `materials-x22-private` repository, all will work well. If you change the path, then you must change the `solutions-path` variable in `grade_assignment.py`.

## Docker Image
This just FYI. The Dockerfile pulls an image : 
```
docker pull ucbdsinfra/otter-grader
```
This image is used by otter-grader to run the containerized grading.

# EdX/LTI integration

The system posts the grade back to the EdX via LTI. You need to have the `LTI_CONSUMER_KEY` and `LTI_CONSUMER_SECRET` defined and encoded via `sops` for this to work correctly. The secrets are in `otter-service/secrets/gke_key.yaml`

# External installation with a re-direct from Jupyterhub

This is the current deployment configuration. We deploy the otter-service to gcloud and there is a re-direct from the Jupyterhub [configuration files](https://github.com/berkeley-dsep-infra/datahub/blob/7fed76f46e3636b3be225f1b149911aa9f1c6b1b/deployments/data8x/config/common.yaml#L22) in the [datahub repository](https://github.com/berkeley-dsep-infra/datahub/tree/staging/deployments/data8x/config) that passes authentication information to otter-service.

Once the GKE cluster is created in gcloud, executing the `deployment/cloud/deploy.sh` file  deploys the service to the cloud. 

# Deployment Details:
## Rollback: 
If we deploy and find problems the quickest way to rollback the deployment is to look at the revision history and undo the deployment by deploying to a previous revision number:
- kubectl rollout history deployment otter-pod -n grader-k8-namespace
- kubectl rollout history deployment otter-pod -n grader-k8-namespace --revision=# <-- to see details like the version of the image used
- kubectl rollout undo deployment/otter-pod -n grader-k8-namespace --to-revision=#

## CI/CD:
If you push a tag in the standard form of a version number(XX.XX.XX), GitHub action creates a release from this tag, pushes the release to pypi.org, builds the docker image, pushes it google's image repository and deploys the new image into the GKE cluster.

## pod size recommendations
There is a vertical pod autoscaler deployed to recommend memory and cpu sizing to the otter-pod pods.
You can see recommendations via either of these commands:
- kubectl get vpa -n grader-k8-namespace
- kubectl get vpa -n grader-k8-namespace --output yaml

It is called an autoscaler but I configured the resource to just recommend and not actually autoscale vertically.

## pod horizontal scaling
A horizontal autoscale is configured to spin up a new pod when 80% of CPU requested is utilized. There is maximum
of 10 pods allowed.

You can see the status of the horizontal scaling via this command:
- kubectl get hpa -n grader-k8-namespace

# pytest
Run ./deployment/local/pytest.sh -- this will start the Firestore emulator and run the tests.
If the emulator is already running it shuts it down. I shut down the emulator when the tests are done
as well but you could comment out this line to check out the data that was stored.

# Local installation for testing/developing

Install a FireStore Emulator so you test locally:
- Install FireStore CLI: https://firebase.google.com/docs/cli/#install-cli-mac-linux
- firebase login
- firebase projects:list
- firebase setup:emulators:firestore
- make java jdk installed
- firebase emulators:start --only firestore --project data8x-scratch
- You can see the UI here: http://localhost:4000/firestore
- python3 -m pip install google-cloud-firestore
- You will notice the re-direct in firebase_local fixture used by test_write_grade in test_otter_nb.py


With docker installed, you can use the `Dockerfile-dev` file to deploy a local instance of otter-service. The `deployment/local/build.sh` file gives some guidance to building and installing local changes to otter-service for testing. The usual process is to make changes, execute `build.sh`, which relies on a `docker-compose.yml` file. A sample is below but before we look, I would also study the file `tests/integration.py`. If you execute this file, you can test the service via a web connection. 

Sample docker-compose.yml:
```
version: "3.9"
services:
  app:
    image: otter-srv
    build:
      context: .
      dockerfile: Dockerfile-dev
      args:
        GIT_ACCESS_TOKEN: your_access_token generated by your github account -- see below
        OTTER_SERVICE_VERSION: whatever_version you specify in otter-service/__init__.py
    env_file:
      - ../.local-env
    ports:
      - 10101:10101
    volumes:
      - /tmp/otter:/mnt/data
    entrypoint: ''

networks:
  default:
    driver: bridge
```

Notes:
- GIT_ACCESS_TOKEN is generated in your GitHub account. This is used to download the materials-x22-private archive to the otter-service docker image -- if you have test files somewhere else and they are not in a private repo this is unnecessary and you would need to change the relevant lines in the Dockerfile and Dockerfile-dev files.

- .local-env These are environment variables that must be set. They mirror the variables in  `deployment/cloud/deployment-config-encrypted.yaml`. You do not need to encrypt your local-env file with sops. 

# Service installation in JupyterHub

Instructions can be found here for running it as a service within your [jupyterhub](https://jupyterhub.readthedocs.io/en/stable/reference/services.html#launching-a-hub-managed-service)

