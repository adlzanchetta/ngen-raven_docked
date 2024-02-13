# NGen-Raven docked

## Description

As NOAA's [Next Gen](https://github.com/NOAA-OWP/ngen) gains relevance and attention as a framework for integrating hydrological models occouring at different scales, efforts to implement the appropriate [BMI](https://csdms.colorado.edu/wiki/BMI) interface for established hydrologic modelling systems such as CSHS-CWRA's [Raven](https://github.com/CSHS-CWRA/RavenHydroFramework) become more and more demanded.

To reduce the ~~annoying headaches~~ challenges related with the process of compiling such systems in different machines (*a.k.a.* improve portability) for direct use or for development, Docker images can be used to create self-contained and ready-to-run operational subsystems.

This repository is just a minimalistic distribution of a Dockerfile that creates a Docker image containing, compiled and ready-to-run:

- NextGen for serial runs;
- NextGen for parallel runs;
- NextGen's partition generator (for set-up of parallel runs);
- NextGen's source code and git repository;
- Raven standalone app;
- Raven shared library (for use with NextGen).

## Creating the Docker image

**NOTES:** 

- it is assumed that [Docker](https://www.docker.com/) is already installed and properly configured in your machine;
- commands are for a Linux system, but shouldn't be very different for other O.S.s.

Clone this repository content and enter the resulting folder:

```bash
$ git clone https://github.com/adlzanchetta/ngen-raven_docked.git
$ cd ngen-raven_docked
```

### For the latest version of both NGen and Raven

Ensure you are in the main branch and it is up to date:

```bash
$ git branch main
$ git pull
```

Build a Docker image with an arbitrary tag - suggested here: "*localbuild/ngen-raven:latest*":

```bash
$ docker build . --file Dockerfile --tag localbuild/ngen-raven:latest
```

If everything worked fine, the chosen tag should be listed in the output of:

```bash
$ docker image ls
```

### For dated versions of both NGen and Raven

Select the brench that has the desired date - in this example: "*v-2024.01.24*"

```bash
$ git switch v-2024.01.24
$ git pull
```

Build a Docker image with an arbitrary tag - suggested here: "*localbuild/ngen-raven:2024.01.24*":

```bash
$ docker build . --file Dockerfile --tag localbuild/ngen-raven:2024.01.24
```

If everything worked fine, the chosen tag should be listed in the output of:

```bash
$ docker image ls
```

## Using the Docker image

### Running only NGen with embedded data

An iterative Docker container with the arbitrary name ```ngen-raven_latest``` <sup>1</sup> can be started with:

```bash
$ docker run -it --name ngen-raven_latest localbuild/ngen-raven:latest
```

**Note<sup>1</sup> :** If a name is not given, a random name composed by two random words will be set, so, while not mandatory, providing a meaningful name is recommended.

Inside the iterative session, a NextGen realization provided as example (without Raven) can be run with:

```bash
# cd /ngen
# /ngen/build_serial/ngen data/catchment_data.geojson all data/nexus_data.geojson all data/example_realization_config.json
```

It will create three ephemeral ```cat-[...].csv``` files at the current working directory. They will desapear as soon as the current session finishes.

### Running with persistent external files

To have a Docker container accessing files in the hosting machine, it need to be started with a local directory mounted into it. Suppose you want to mount the folder ```./some/local_data```<sup>2</sup>, the recommended command to be used is:

```bash
$ docker run -it -v ./v2024-01-24_NGen-Raven/data:/data --name ngen-raven_2024.01.24 localbuild/ngen-raven:2024.01.24
```

**Note<sup>2</sup> :** It is assumed that the Docker is already configured to have the folder ```./some/local_data``` among the shared resources.

The abovepresented command will start a container named ```ngen-raven_2024.01.24``` in which any change in the content of ```/data``` will persist at ```./some/local_data``` even after the end of the session.

### Running NGen + Raven with persistent external files

A NGen realization calling multiple Raven models is provided as example and it can be found in the directory ```data_v2024-01-24```, (in the root of this repository). These files are NOT included in a Docker container created out of this ```Dockerfile```.

To run this example, it is recommended to launch a Docker container having the root of this repository was working directory with:

```bash
$ docker run -it -v ./data_v2024-01-24:/data localbuild/ngen-raven:2024.01.24
```

Inside the container:

```bash
# cd /data/3_models_outputs/
# /ngen/build_serial/ngen /data/1_raw/gis/catchments.geojson all /data/1_raw/gis/nexus.geojson all /data/2_models_inputs/realization_raven.json
```

The output files will be persistently written at ```./data_v2024-01-24/3_models_outputs``` in your local machine.
