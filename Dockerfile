FROM rockylinux:8 as builder

RUN yum update -y \
    && yum install -y dnf-plugins-core \
    && yum -y install epel-release \
    && yum repolist \
    && yum install -y tar git gcc-c++ gcc make cmake python38 python38-devel python38-numpy bzip2 udunits2-devel \
    && yum install -y openmpi openmpi-devel \
    && dnf clean all \
  	&& rm -rf /var/cache/yum

RUN curl -L -o boost_1_79_0.tar.bz2 https://sourceforge.net/projects/boost/files/boost/1.79.0/boost_1_79_0.tar.bz2/download \
    && tar -xjf boost_1_79_0.tar.bz2 \
    && rm boost_1_79_0.tar.bz2

ENV BOOST_ROOT="/boost_1_79_0"

ENV CXX=/usr/bin/g++

# at this point we only need the CMakeLists.txt file and the src directory
RUN git clone https://github.com/NOAA-OWP/ngen.git /ngen

WORKDIR /ngen

# VERSION DEPENDENT: ensure commit of 2024.19.02 - be518f7deecaccf21ce8105e32196bf4c0b4d440
RUN git pull \
 && git reset --hard be518f7

RUN git submodule update --init --recursive -- test/googletest \
 && git submodule update --init --recursive -- extern/pybind11

RUN cmake -DNGEN_WITH_NETCDF:BOOL=OFF \
          -DNGEN_WITH_SQLITE:BOOL=OFF \
          -B /ngen/build_serial \
          -S . \
 && cmake --build ./build_serial --target ngen

# extern googletest also needs o be built
WORKDIR /ngen/extern/test_bmi_cpp/cmake_build

RUN make

WORKDIR /ngen/

# for the parallel build, we need to load the openmpi module so that cmake can the MPI headers
RUN source /etc/profile.d/modules.sh \
 && module load mpi/openmpi-x86_64 \
 && cmake -DNGEN_WITH_MPI:BOOL=ON \
          -DNGEN_WITH_PYTHON:BOOL=ON \
          -DNGEN_WITH_NETCDF:BOOL=OFF \
          -DNGEN_WITH_SQLITE:BOOL=OFF \
          -B /ngen/build_parallel \
          -S .

# it is also useful to have the partitionGenerator executable built
RUN bash -c "cd /ngen/build_parallel && cmake --build . --target partitionGenerator --"

# the following lines are for including Raven to the image (adlzanchetta fork is used for dev)
# RUN git clone https://github.com/CSHS-CWRA/RavenHydroFramework.git /raven
RUN git clone https://github.com/adlzanchetta/RavenHydroFramework.git /raven

WORKDIR /raven

# VERSION DEPENDENT: ensure commit of 2024.02.19 - bc4038fb296c5de0429bd9ca6e1e6c2321befefb
RUN git reset --hard bc4038f

RUN mkdir /raven/build \
 && cmake -DCOMPILE_LIB=ON -B /raven/build/ -S /raven/ \
 && make -C /raven/build/

# activating the openmpi module as session starts makes 'mpirun' and mpi headers available with
# 'docker run -it <image_name>'
CMD bash -c "source /etc/profile.d/modules.sh && module load mpi/openmpi-x86_64 && /bin/bash"

WORKDIR /