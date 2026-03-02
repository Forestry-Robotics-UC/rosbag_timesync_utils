import rosbag2_py
from rclpy.serialization import deserialize_message, serialize_message
from rosidl_runtime_py.utilities import get_message
import json, os, shutil, sys

# Receives bag path via sys.argv
path_in = sys.argv[1]
path_out = f"{path_in}_Processed"

bagfiles = []

# Target topics subject to timestamp correction
targets = [
    "/imu/data",
    "/camera/camera/color/image_raw",
    "/camera/camera/aligned_depth_to_color/image_raw",
]

# Sorts bag files numerically based on suffix
files = sorted(
    [file for file in os.listdir(path_in) if file.endswith(".mcap")],
    key=lambda x: int(x.split("_")[-1].replace(".mcap", ""))
)

for file in files:
    bagfiles.append(os.path.join(path_in, file))

# Process each bag file sequentially
for file in bagfiles:
    bag_number = file.split("_")[-1].replace(".mcap", "")

    messages = {}
    topics = {}

    print(f"Reading bag file: {file.split('/')[-1]}")

    # Create output bag writer
    writer = rosbag2_py.SequentialWriter()
    storage_Processed = rosbag2_py.StorageOptions(uri=f"{path_out}_{bag_number}", storage_id="mcap")
    converter = rosbag2_py.ConverterOptions(input_serialization_format="cdr", output_serialization_format="cdr")

    writer.open(storage_Processed, converter)

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
            # NOTE: id is a mandatory parameter when using this script in Jazzy, but it is not used
            # when using this script in Humble, so make sure to comment it or uncomment depending on
            # the ROS version used
            metadata = rosbag2_py.TopicMetadata(
                # id=topic.id,
                name=output_topic,
                type=topics[topic.name],
                serialization_format="cdr"
            )

            writer.create_topic(metadata)
            print(f"Created topic on output bag: {output_topic}")


    # Read messages from input bag
    while reader.has_next():
        topic, msg, timestamp = reader.read_next()

        # Decodes message as soon as read to extract header timestamp, which is the default publish
        # timestamp for the processed bags
        decoded = deserialize_message(
            msg, 
            get_message(topics[topic])
        )

        header_ts = int(decoded.header.stamp.sec * 1e9 + decoded.header.stamp.nanosec) if hasattr(decoded, "header") else timestamp

        # To correlate Realsense metadata messages with the corresponding image message, metadata for
        # these topics is stored as a dictionary with the header timestamp as key, timestamp which is
        # the same in the corresponding image header
        if "/depth/metadata" in topic or "/color/metadata" in topic:
            # Initialize message storage
            if topic not in messages:
                messages[topic] = {}

            exp_time = 0
            json_data = json.loads(decoded.json_data)

            # The actual_exposure parameter may be missing so make sure to default exposure time to 0
            if "actual_exposure" in json_data:
                exp_time = json_data["actual_exposure"]
            
            messages[topic][header_ts] = {
                "coded_msg": msg,
                "exp_time": exp_time,
                "header_ts": header_ts,
                "corrected_ts": None
            }
        else:
            # Initialize message storage
            if topic not in messages:
                messages[topic] = []

            # Also saves decoded message for any potential future use
            messages[topic].append(
                {
                    "coded_msg": msg,
                    "decoded_msg": decoded,
                    "header_ts": header_ts,
                    "corrected_ts": None
                }
            )

    # List number of messages read per topic
    for topic in messages:
        print(f"Messages read from {topic}: {len(messages[topic])}")
            
    # Process Realsense color images for timestamp correction using exposure time
    if "/camera/camera/color/image_raw" in messages:
        for message in messages["/camera/camera/color/image_raw"]:        
            # For Realsense, header timestamp is same as frame timestamp from corresponding metadata
            exp_time = messages["/camera/camera/color/metadata"].get(message["header_ts"], {}).get("exp_time", 0)
            
            message["corrected_ts"] = int(message["header_ts"] - (exp_time * 1e3))

    # Process Realsense aligned depth images for timestamp correction using exposure time
    if "/camera/camera/aligned_depth_to_color/image_raw" in messages:
        for message in messages["/camera/camera/aligned_depth_to_color/image_raw"]:
            # For Realsense, header timestamp is same as frame timestamp from corresponding metadata
            exp_time = messages["/camera/camera/depth/metadata"].get(message["header_ts"], {}).get("exp_time", 0)
            
            message["corrected_ts"] = int(message["header_ts"] - (exp_time * 1e3))

    # Process IMU data for frame id adjustment
    if "/imu/data" in messages:
        for message in messages["/imu/data"]:
            # Adjust frame_id
            message["decoded_msg"].header.frame_id = "xsens_imu"
            message["coded_msg"] = serialize_message(message["decoded_msg"])

    # Write messages to output bag with corrected timestamps
    for topic in messages:
        output_topic = topic
        if topic in targets: output_topic = f"{topic}/corrected"
        print(f"Writing messages to {output_topic} on output bag")

        for message in messages[topic]:
            if "/depth/metadata" in topic or "/color/metadata" in topic: message = messages[topic][message]

            header_ts = message["header_ts"]
            corrected_ts = message["corrected_ts"]

            # Defaults publish timestamp to the extracted header timestamp unless a
            # corrected timestamp exists
            output_ts = header_ts if corrected_ts is None else corrected_ts

            writer.write(output_topic, message["coded_msg"], int(output_ts))

    # Close reader and writer
    del reader, writer

corrected_folder = f"{path_out}_0"

for folder in os.listdir(path_in.split("/")[0]):
    # Move all processed bags into one single folder
    if "_Processed" in folder and "_Processed_0" not in folder:
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