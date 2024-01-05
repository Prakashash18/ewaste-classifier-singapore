# main.py
import streamlit as st
from ultralytics import YOLO
from PIL import Image, ImageDraw, ImageFont
from collections import Counter
import requests
from pykml import parser
import googlemaps
import json
import urllib
import time
import numpy as np

if "next_page" in st.session_state:
    selected_page = "Find Bin"
    default=1
else:
    default=0

# Sidebar navigation
page_options = ["Upload Photo", "Find Bin", "Take Photo"]
selected_page = st.sidebar.selectbox("Select Action", page_options, index = default)

# Load model
model = YOLO('best_ewaste_5_Jan_2024.pt')

api_key = "AIzaSyCvWRdzEZOPkpBsGWOY_nYM-QAEewjvHmU"

gmaps = googlemaps.Client(key=api_key)

def upload_photo():
    st.header('Regulated ewaste :green[detection] system :wastebasket:', divider=True)

    st.markdown("""
    ## Instructions

    1. Please follow these steps:
        - Step 1: Upload your images to detect ewaste
        - Step 2: Identified ewaste can be recycled
        - Step 3: Find a bin near you

    """)

    with st.container():
        # Upload image
        uploaded_file = st.file_uploader(
            "Upload your images here",
            accept_multiple_files=True,
            type=['jpg', 'jpeg', 'png']
        )

    st.divider()

    with st.sidebar:
        global threshold
        threshold = st.slider('Set confidence levels', 0.0, 1.0, 0.7)

    with st.container():
        if uploaded_file:
            detected_labels = []
            image_dict = {}

            for imagesPath in uploaded_file:
                img = Image.open(imagesPath) 

                # Prediction
                results = model.predict(img)

                for result in results:
                  print("Inside !")
                  res = result.boxes
                  print(res.conf)

                  if not res:
                    image_dict["Unknown"] = img
                    detected_labels.append("Unknown")
                    continue

                  # print(res)
                  for det in res:
                     print("Inside 2 !")
                     # Create a drawing object to draw bounding boxes
                     draw = ImageDraw.Draw(img)
                     font = ImageFont.truetype("Arial.ttf", 36) # set larger font size
                     x1, y1, x2, y2, conf, cls = det.data[0]  # Extract the bounding box coordinates, confidence, and class

                     if conf > threshold: #reduce false positives
                        draw.rectangle([x1, y1, x2, y2], outline='green', width=3)
                        draw.text((x1, y1), f'{results[0].names[int(cls)]} ({conf:.2f})', fill='red', font=font)
                        image_dict[results[0].names[int(cls)]] = img
                        detected_labels.append(results[0].names[int(cls)])
                     else:
                        image_dict["Unknown"] = img
                        detected_labels.append("Unknown")

            label_counts = Counter(detected_labels)

            label_counts_dict = dict(label_counts)

            print(label_counts_dict)

            if "Unknown" in label_counts_dict:
                del label_counts_dict["Unknown"]

            st.subheader("The following can be :green[recycled] :recycle:")
            st.table(label_counts_dict  )

            # Button to go to the second page
            if st.button("Find ewaste bin", type="primary"):
                print("Hi")
                selected_page = "Find Bin"
                default = 1 #index of Find Bin
                st.session_state.next_page = "Find Bin"
                st.rerun()

            unique_detections = set(detected_labels)

            iconed_unique_detections = [":warning: " + i if i == "Unknown" else i for i in list(unique_detections)]

            tabs = st.tabs(iconed_unique_detections)

            for label, tab in zip(unique_detections, tabs):
                if label =="Unknown":
                    tab.write(f":warning: :orange[{label}]")
                else:
                    tab.write(label)

                tab.image(image_dict[label])

def find_bin():
    st.header('Find an :blue[ewaste bin] near me :sunglasses:')

    # Load KML file
    with open('EwasteRecycling_NEW.kml', 'r') as kml_file:
        kml_doc = parser.parse(kml_file)

    # Define the namespace for KML elements
    ns = {'kml': 'http://www.opengis.net/kml/2.2'}

    # Specify the names you want to extract
    names_to_extract = ["ADDRESSBUILDINGNAME", "ADDRESSPOSTALCODE", "ADDRESSSTREETNAME", "DESCRIPTION"]

    # Extract text content from SimpleData elements with specified names for all Placemark elements
    all_data_values = []

    # Find all Placemark elements
    placemarks = kml_doc.findall('.//kml:Placemark', namespaces=ns)

    # Iterate over found Placemark elements
    for placemark in placemarks:
        data_values = {}
        # Extract values for each specified name
        for name in names_to_extract:
            xpath_expression = f".//kml:SimpleData[@name='{name}']"
            element = placemark.find(xpath_expression, namespaces=ns)
            if element is not None:
                data_values[name] = element.text
            else:
                data_values[name] = None
        all_data_values.append(data_values)

    dict_locations= {}

    for locations in all_data_values:
        dict_locations[locations['ADDRESSPOSTALCODE']] = [locations['ADDRESSBUILDINGNAME'], locations['DESCRIPTION'], locations['ADDRESSSTREETNAME']]


    with st.container():
        postal_code = st.text_input("Enter your postal code")

        if postal_code:
            with st.spinner('Wait for it...'):
                origin_coordinates = postal_code

                # Extract information from the result
                distance_value = {}
                distance_text = {}
                
                # Number of items to process at a time
                batch_size = 24
                my_list = list(dict_locations.keys())

                my_list = ["Singapore "+ item for item in my_list]


                # Loop to process items in batches
                for i in range(0, len(my_list), batch_size):
                    batch = my_list[i:i + batch_size]
                    result = gmaps.distance_matrix(origin_coordinates, batch)

                    # Extract information from the result
                    elements = result['rows'][0]['elements']
                    for i in range(len(elements)):
                        if 'distance' in elements[i]:
                            distance_value[result['destination_addresses'][i]] =  elements[i]['distance']['value']
                            distance_text[result['destination_addresses'][i]] = elements[i]['distance']['text']

                sorted_distance_values = sorted(distance_value.items(), key=lambda x:x[1])

                st.write("The 5 nearest bins are at")

                checkbox_value = st.checkbox(":warning: Includes ewaste bins with battery, lamp only and non-regulated ewaste", True)

                final_five = []
                if not checkbox_value:
                    i=0
                    for item in sorted_distance_values:
                        if "ICT equipment" in dict_locations[item[0].split(" ")[1]][1]:
                            i+=1
                            final_five.append(item)

                        if i == 5:
                            break

                else:
                    final_five = sorted_distance_values[:5]

                for item in final_five:
                    f = { 'api' : 1, 'destination' : dict_locations[item[0].split(" ")[1]][2]}
                    location = urllib.parse.urlencode(f)

                    if "ICT equipment" in dict_locations[item[0].split(" ")[1]][1]:
                        with st.expander(f"Distance {distance_text[item[0]]}"):
                          
                            st.write("Building : " + dict_locations[item[0].split(" ")[1]][0])
                            st.write("Address : " + dict_locations[item[0].split(" ")[1]][2])
                            st.write("Description : " + dict_locations[item[0].split(" ")[1]][1])
                            st.write("https://www.google.com/maps/dir/?"+location)
                    else:
                        with st.expander(f"Distance {distance_text[item[0]]} :warning: See Description"):
                            st.write("Building : " + dict_locations[item[0].split(" ")[1]][0])
                            st.write("Address : " + dict_locations[item[0].split(" ")[1]][2])
                            st.write("Description : " + dict_locations[item[0].split(" ")[1]][1])
                            st.write("https://www.google.com/maps/dir/?"+location)


            st.success('Done!')

def take_photo():
    st.title("Take Photo")
    picture = st.camera_input("Take a picture")

    with st.sidebar:
        global threshold
        threshold = st.slider('Set confidence levels', 0.0, 1.0, 0.7)


    if picture:

        img = Image.open(picture)

        detected_labels = []
        image_dict = {}

        # picture_np = np.array(picture)

        # print(type(picture))

        # Prediction
        results = model.predict(img)

        for result in results:
          print("Inside !")
          res = result.boxes
          print(res.conf)

          if not res:
            image_dict["Unknown"] = img
            detected_labels.append("Unknown")
            continue

          # print(res)
          for det in res:
             print("Inside 2 !")
             # Create a drawing object to draw bounding boxes
             draw = ImageDraw.Draw(img)
             font = ImageFont.truetype("Arial.ttf", 36) # set larger font size
             x1, y1, x2, y2, conf, cls = det.data[0]  # Extract the bounding box coordinates, confidence, and class

             if conf > threshold: #reduce false positives
                draw.rectangle([x1, y1, x2, y2], outline='green', width=3)
                draw.text((x1, y1), f'{results[0].names[int(cls)]} ({conf:.2f})', fill='red', font=font)
                image_dict[results[0].names[int(cls)]] = img
                detected_labels.append(results[0].names[int(cls)])
             else:
                image_dict["Unknown"] = img
                detected_labels.append("Unknown")

        label_counts = Counter(detected_labels)

        label_counts_dict = dict(label_counts)

        print(label_counts_dict)

        if "Unknown" in label_counts_dict:
            del label_counts_dict["Unknown"]

        st.subheader("The following can be :green[recycled] :recycle:")
        st.table(label_counts_dict  )

        # Button to go to the second page
        if st.button("Find ewaste bin", type="primary"):
            print("Hi")
            selected_page = "Find Bin"
            default = 1 #index of Find Bin
            st.session_state.next_page = "Find Bin"
            st.rerun()

        unique_detections = set(detected_labels)

        iconed_unique_detections = [":warning: " + i if i == "Unknown" else i for i in list(unique_detections)]

        tabs = st.tabs(iconed_unique_detections)

        for label, tab in zip(unique_detections, tabs):
            if label =="Unknown":
                tab.write(f":warning: :orange[{label}]")
            else:
                tab.write(label)

            tab.image(image_dict[label])


print("Rendering", default)

# Display the selected page
if selected_page == "Upload Photo":
    upload_photo()
elif selected_page == "Find Bin":
    find_bin()
elif selected_page == "Take Photo":
    take_photo()
