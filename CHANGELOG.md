## 0.1.21

#### Enhancements made

- Save_Path are trailing forward slash

## 0.1.20

#### Enhancements made

- Fixed URI to include backslash

## 0.1.19

#### Enhancements made

- Configured the grading to download autotgrader materials each time so
that the materials can be changed and the system not re-deployed
- fixed image name in deployment.yaml; mistake in set-image path

## 0.1.18

#### Enhancements made

- cloud deploy not longer dependent on local build

## 0.1.17

#### Enhancements made

- deploys from branches to appropriate namespaces
- converted to otter-service(removed from gofer-service repo)

## 0.1.11

#### Enhancements made

- Configure GitHub Actions: releases, deployments
- Added init.py to src dir to run pytests from GH
- arrange test files Github Action to run tests
- Github Action configured to build off master
- Github Action configured to build docker image
- Github Action configured to push docker image and deploy to cluster
- Added Persistent Volume
- Added NFS


## 0.1

### 0.1.0 - 2021-10-23

#### Enhancements made

- swapped otter grader to gofer-grader

#### Bugs fixed

- improved error handling to ensure we don't try to post a bad submission
