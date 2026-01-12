ARG CORES=12
FROM ros:jazzy-ros-base

LABEL maintainer="Duarte Cruz <duarte.cruz@isr.uc.pt>"

SHELL ["/bin/bash","-c"]

ENV DEBIAN_FRONTEND=noninteractive

# Install packages
RUN apt-get update \
    && apt-get install -y \
    build-essential \
    apt-utils \
    curl \
    git \
    wget \
    vim \
    nano \
    software-properties-common \
    unzip \
    cmake \
    lsb-release \
    dialog \
    libpcap-dev

# Install some python packages
RUN apt-get -y install \
    python3 \
    python3-pip \
    python3-serial \
    python3-rosinstall-generator \
    python3-rosdep \
    python3-colcon-common-extensions

#Install ROS Packages
RUN apt-get install -y ros-jazzy-rviz2 \
    ros-jazzy-tf-transformations \
    ros-jazzy-desktop \
    ros-jazzy-joint-state-publisher \
    ros-jazzy-joint-state-publisher-gui \
    ros-jazzy-xacro \
    ros-jazzy-rmw-cyclonedds-cpp \
    ros-jazzy-ur-description \
    ros-jazzy-rqt-tf-tree \
    ros-jazzy-pcl-ros \
    ros-jazzy-pcl-conversions \
    ros-jazzy-laser-filters \
    ros-jazzy-pointcloud-to-laserscan \
    ros-jazzy-diagnostic-updater \
    ros-jazzy-librealsense2* \
    ros-jazzy-realsense2-* \
    ros-jazzy-rosbag2-storage-mcap

#Configure catkin workspace
ENV CATKIN_WS=/root/ros2_ws
RUN mkdir -p $CATKIN_WS/src

#Compile workspace
WORKDIR $CATKIN_WS
RUN . /opt/ros/jazzy/setup.sh && colcon build --symlink-install

RUN echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc
RUN echo "source /root/ros2_ws/install/setup.bash" >> ~/.bashrc
RUN echo "cd ros2_ws/" >> ~/.bashrc
RUN echo "export __NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia" >> ~/.bashrc
RUN echo "export RMW_IMPLEMENTATION=rmw_fastrtps_cpp" >> ~/.bashrc

# Clean-up
WORKDIR /root
RUN apt upgrade -y
RUN apt-get clean

CMD ["bash"]
