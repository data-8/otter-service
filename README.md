# Gofer_nb service

This repo contains a tornado flask app that accepts .ipynb files and grades them in a dockerized environment. Assuming you are running a Jupyterhub, you can ask it to run this app as a service so that you don't have to run it as a standalone. Grades will be saved to a sqlite database.

Paired with the submit_extension [here](https://github.com/data-8/gofer_submit), the user simply clicks a button to submit their notebook and will receive a notification that their submission has been saved and will be graded.

# Database setup

This service assumes the existence of a database called `gradebook.db` with . To create it, run `create_database.py` to set up a database with the default naming and schema.

TODO A script will be provided to pull a csv version of records stored in the database.


# Configuration

There are three critical steps to set up ahead of time for this to work.

First, the ipynb notebooks should have the metadata for which assignment they are. In the case of Data 8x, there are two pieces of information that are relevant, the section and the lab number.

Second, tests should be placed in a location that can be specified by the assignment metadata. This could simply be done by making the directory structure correspond to numbers, or by having a python dict from assignment names to test directories.

Third, a docker image should be made that specifies the user environment. This prevents their (arbitrary) notebook code from being run on the server that hosts everyone.

# EdX/LTI integration

The workflow for posting grades back to a course is still being standardized and is a work in progress. To do this properly this will require coordination between assignment metadata, associating them with the correct assignment identifiers, and paths to where the test directories live.

# Service installation

Instructions can be found here for running it as a service within your jupyterhub: https://jupyterhub.readthedocs.io/en/stable/reference/services.html#launching-a-hub-managed-service

TODO: write instructions for installing the service on an arbitrary server.
