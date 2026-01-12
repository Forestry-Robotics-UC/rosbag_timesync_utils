ARG CORES=12
FROM ros:humble-ros-base

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
RUN apt-get install -y ros-humble-rviz2 \
    ros-humble-tf-transformations \
    ros-humble-desktop \
    ros-humble-joint-state-publisher \
    ros-humble-joint-state-publisher-gui \
    ros-humble-xacro \
    ros-humble-rmw-cyclonedds-cpp \
    ros-humble-ur-description \
    ros-humble-rqt-tf-tree \
    ros-humble-pcl-ros \
    ros-humble-pcl-conversions \
    ros-humble-laser-filters \
    ros-humble-pointcloud-to-laserscan \
    ros-humble-diagnostic-updater \
    ros-humble-librealsense2* \
    ros-humble-realsense2-* \
    ros-humble-rosbag2-storage-mcap

#Configure catkin workspace
ENV CATKIN_WS=/root/ros2_ws
RUN mkdir -p $CATKIN_WS/src

#Compile workspace
WORKDIR $CATKIN_WS
RUN . /opt/ros/humble/setup.sh && colcon build --symlink-install

RUN echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
RUN echo "source /root/ros2_ws/install/setup.bash" >> ~/.bashrc
RUN echo "cd ros2_ws/" >> ~/.bashrc
RUN echo "export __NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia" >> ~/.bashrc
RUN echo "export RMW_IMPLEMENTATION=rmw_fastrtps_cpp" >> ~/.bashrc

# Clean-up
WORKDIR /root
RUN apt upgrade -y
RUN apt-get clean

CMD ["bash"]
