import rosbag2_py
from rclpy.serialization import deserialize_message, serialize_message
from rosidl_runtime_py.utilities import get_message
import json, os, shutil, sys

# Receives bag path via sys.argv
path_in = sys.argv[1]
path_out = f"{path_in}_Corrected"

bagfiles = []

# Target topics subject to timestamp correction
targets = [
    "/rslidar_packets",
    "/ouster/points",
    "/ouster/imu",
    "/imu/data",
    "/imu/mag",
    "/camera/camera/color/image_raw",
    "/camera/camera/aligned_depth_to_color/image_raw"
]

# Sorts bag files numerically based on suffix
files = sorted(
    [file for file in os.listdir(path_in) if file.endswith(".mcap")],
    key=lambda x: int(x.split("_")[-1].replace(".mcap", ""))
)

for file in files:
    bagfiles.append(os.path.join(path_in, file))

# Process each bag file
counter = 0
for file in bagfiles:
    messages = {}
    topics = {}

    print(f"Reading bag file: {file.split('/')[-1]}")

    # Create output bag writer
    writer = rosbag2_py.SequentialWriter()
    storage_corrected = rosbag2_py.StorageOptions(uri=f"{path_out}_{counter}", storage_id="mcap")
    converter = rosbag2_py.ConverterOptions(input_serialization_format="cdr", output_serialization_format="cdr")

    writer.open(storage_corrected, converter)

    # Create input bag reader
    reader = rosbag2_py.SequentialReader()
    storage = rosbag2_py.StorageOptions(uri=file, storage_id="mcap")
    converter = rosbag2_py.ConverterOptions(input_serialization_format="cdr", output_serialization_format="cdr")

    reader.open(storage, converter)

    # Read all topics and messages from input bag
    for topic in reader.get_all_topics_and_types():
        if topic.name not in topics:
            topics[topic.name] = topic.type

            output_topic = topic.name
            if topic.name in targets: output_topic = f"{topic.name}/corrected"

            # Create topic on output bag
            metadata = rosbag2_py.TopicMetadata(
                name=output_topic,
                type=topics[topic.name],
                serialization_format="cdr"
            )

            writer.create_topic(metadata)
            print(f"Created topic on output bag: {output_topic}")

        # Initialize message storage
        if topic.name not in messages:
            messages[topic.name] = []

    # Read messages from input bag
    while reader.has_next():
        topic, msg, timestamp = reader.read_next()

        data = {
            "message": msg,
            "record_ts": timestamp,
            "corrected_ts": None
        }

        messages[topic].append(data)

    # List number of messages read per topic
    for topic in messages:
        print(f"Messages read from {topic}: {len(messages[topic])}")

    # Process BPearl packets for timestamp correction
    if "/rslidar_packets" in messages:
        for message in messages["/rslidar_packets"]:
            decoded = deserialize_message(
                message["message"], 
                get_message("rslidar_msg/msg/RslidarPacket")
            )

            corrected_ts = int(decoded.header.stamp.sec * 1e9 + decoded.header.stamp.nanosec)
            if corrected_ts != 0:
                message["corrected_ts"] = corrected_ts

    # Process Ouster points for timestamp correction
    if "/ouster/points" in messages:
        for message in messages["/ouster/points"]:
            decoded = deserialize_message(
                message["message"], 
                get_message("sensor_msgs/msg/PointCloud2")
            )

            # Corrects timestamp based on delta from reference (manual for now, automatic later on)
            header_ts = int(decoded.header.stamp.sec * 1e9 + decoded.header.stamp.nanosec)
            delta = header_ts - ouster_data['internal']

            corrected_ts = ouster_data['epoch'] + delta

            # Applies corrected timestamp on the header as well
            decoded.header.stamp.sec = corrected_ts // int(1e9)
            decoded.header.stamp.nanosec = corrected_ts % int(1e9)
            message["corrected_ts"] = corrected_ts

            message["message"] = serialize_message(decoded)

    # Process Ouster IMU data for timestamp correction
    if "/ouster/imu" in messages:
        for message in messages["/ouster/imu"]:
            decoded = deserialize_message(
                message["message"], 
                get_message("sensor_msgs/msg/Imu")
            )
            
            # Corrects timestamp based on delta from reference
            header_ts = int(decoded.header.stamp.sec * 1e9 + decoded.header.stamp.nanosec)
            delta = header_ts - ouster_data['internal']

            corrected_ts = ouster_data['epoch'] + delta
            
            # Applies corrected timestamp on the header as well
            decoded.header.stamp.sec = corrected_ts // int(1e9)
            decoded.header.stamp.nanosec = corrected_ts % int(1e9)
            message["corrected_ts"] = corrected_ts
            
            message["message"] = serialize_message(decoded)            

    # Process Realsense color images for timestamp correction
    if "/camera/camera/color/image_raw" in messages:
        for message, metadata in zip(
            messages["/camera/camera/color/image_raw"],
            messages["/camera/camera/color/metadata"]    
        ):
            decoded_md = deserialize_message(
                metadata["message"], 
                get_message("realsense2_camera_msgs/msg/Metadata")
            )
            
            decoded = deserialize_message(
                message["message"], 
                get_message("sensor_msgs/msg/Image")
            )

            json_data = json.loads(decoded_md.json_data)

            # Uses the frame timestamp parameter present in the metadata
            corrected_ts = int(json_data["frame_timestamp"] * 1e6)

            # Applies corrected timestamp on the header as well
            decoded.header.stamp.sec = corrected_ts // int(1e9)
            decoded.header.stamp.nanosec = corrected_ts % int(1e9)
            message["corrected_ts"] = corrected_ts

            message["message"] = serialize_message(decoded)

    # Process Realsense aligned depth images for timestamp correction
    if "/camera/camera/aligned_depth_to_color/image_raw" in messages:
        for message, metadata in zip(
            messages["/camera/camera/aligned_depth_to_color/image_raw"],
            messages["/camera/camera/depth/metadata"]    
        ):
            decoded_md = deserialize_message(
                metadata["message"], 
                get_message("realsense2_camera_msgs/msg/Metadata")
            )

            decoded = deserialize_message(
                message["message"], 
                get_message("sensor_msgs/msg/Image")
            )

            json_data = json.loads(decoded_md.json_data)
            
            # Uses the frame timestamp and actual exposure parameters present in the metadata
            corrected_ts = int(json_data["frame_timestamp"] * 1e6) - (json_data["actual_exposure"] * 1000) - 1000000

            # Applies corrected timestamp on the header as well
            decoded.header.stamp.sec = corrected_ts // int(1e9)
            decoded.header.stamp.nanosec = corrected_ts % int(1e9)
            message["corrected_ts"] = corrected_ts

            message["message"] = serialize_message(decoded)

    # Process IMU data for timestamp correction
    if "/imu/data" in messages:
        for message in messages["/imu/data"]:
            decoded = deserialize_message(
                message["message"], 
                get_message("sensor_msgs/msg/Imu")
            )

            corrected_ts = int(decoded.header.stamp.sec * 1e9 + decoded.header.stamp.nanosec)
            message["corrected_ts"] = corrected_ts

            # Adjust frame_id
            decoded.header.frame_id = "xsens_imu"
            message["message"] = serialize_message(decoded)

    # Process IMU magnetometer data for timestamp correction
    if "/imu/mag" in messages:
        for message in messages["/imu/mag"]:
            decoded = deserialize_message(
                message["message"], 
                get_message("sensor_msgs/msg/MagneticField")
            )

            corrected_ts = int(decoded.header.stamp.sec * 1e9 + decoded.header.stamp.nanosec)
            message["corrected_ts"] = corrected_ts

    # Write messages to output bag with corrected timestamps
    for topic in messages:
        output_topic = topic
        if topic in targets: output_topic = f"{topic}/corrected"
        print(f"Writing messages to {output_topic} on output bag")

        for message in messages[topic]:
            corrected_ts = message["corrected_ts"]        
            output_ts = corrected_ts if corrected_ts is not None else message["record_ts"]

            writer.write(output_topic, message["message"], int(output_ts))

    # Close reader and writer
    del reader, writer
    counter += 1

corrected_folder = f"{path_out}_0"

for folder in os.listdir(path_in.split("/")[0]):
    # Move all processed bags into one single folder
    if "_Corrected" in folder and "_Corrected_0" not in folder:
        folder_path = os.path.join(path_in.split("/")[0], folder)

        print(f"Moving files from {folder_path} to {corrected_folder}")

        for file in os.listdir(folder_path):
            if file.endswith(".mcap"):
                shutil.move(
                    os.path.join(folder_path, file),
                    corrected_folder
                )

        # Remove now empty folder
        shutil.rmtree(folder_path)