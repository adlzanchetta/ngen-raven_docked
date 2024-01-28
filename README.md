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

Build a Docker image with an arbitrary tag - here we use "*localbuild/ngen-raven:latest*":

```bash
$ docker build . --file Dockerfile --tag localbuild/ngen-raven:latest
```

If everything worked fine, the chosen tag should be listed in the output of:

```bash
$ docker image ls
```

## Using the Docker image

An iterative Docker container can be started with:

```bash
$ docker run -it localbuild/ngen-raven:latest
```

There, NextGen realization (without Raven) provided as example can be run with:

```bash
$ build_serial/ngen data/catchment_data.geojson all data/nexus_data.geojson all data/example_realization_config.json
```