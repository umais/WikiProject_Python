import os
import time
import spacy
import csv
import gender_guesser.detector as gender
import wikipediaapi
import networkx as nx

# Wikipedia API setup
wiki_wiki = wikipediaapi.Wikipedia(user_agent="DataScienceProject/1.0", language='en')

# The topic to analyze
topic_title = "Artificial Intelligence"

# Load the English NLP model
nlp = spacy.load("en_core_web_sm")

# Ensure the directory exists
output_folder = "Wiki_Person_Connections"
os.makedirs(output_folder, exist_ok=True)

# Initialize gender detector once
gender_detector = gender.Detector()

def detect_gender(name):
    """Detects the gender of a person based on their first name."""
    name_parts = name.split()
    first_name = name_parts[0] if name_parts else name
    gender_result = gender_detector.get_gender(first_name)
    
    if gender_result in ['male', 'mostly_male']:
        return 'Male'
    elif gender_result in ['female', 'mostly_female']:
        return 'Female'
    else:
        return 'Unknown'

def is_person_name(text):
    """Checks if the given text is recognized as a person's name."""
    doc = nlp(text)
    return any(ent.label_ == "PERSON" for ent in doc.ents)

def process_page(title):
    """Fetches links for a Wikipedia page and determines the gender of identified persons."""
    start_time = time.time()
    page = wiki_wiki.page(title)
    if not page.exists():
        print(f"Page '{title}' does not exist.")
        return []

    links = list(page.links.keys())
    person_data = []
    
    for link in links:
        if is_person_name(link):
            gender_result = detect_gender(link)
            person_data.append((link, gender_result))
    
    print(f"Found {len(person_data)} persons in the page: {title} - Time Taken: {time.time() - start_time:.2f} sec")
    return person_data

def save_to_csv(filepath, person_data):
    """Saves identified names and genders to a CSV file."""
    with open(filepath, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["Name", "Gender"])
        writer.writerows(person_data)
    print(f"Data saved to {filepath}")

# Step 1: Process the main topic and save results
main_csv_filename = f"{topic_title.replace(' ', '_')}_Linked_People.csv"

if not os.path.exists(main_csv_filename):
    print("Processing main topic page...")
    person_list = process_page(topic_title)
    save_to_csv(main_csv_filename, person_list)
else:
    print(f"{main_csv_filename} already exists. Skipping topic processing.")

# Read names from the first CSV
original_people = set()
person_gender_map = {}

print("Reading main topic CSV...")
with open(main_csv_filename, mode='r', encoding='utf-8') as file:
    reader = csv.reader(file)
    next(reader)  # Skip header row
    for row in reader:
        if row:  # Ensure row is not empty
            person_name = row[0].strip()
            gender = row[1].strip()
            if person_name:
                original_people.add(person_name)
                person_gender_map[person_name] = gender

print(f"Loaded {len(original_people)} names from CSV.")

# Step 2: Process each person's Wikipedia page and save connections
for index, person_name in enumerate(original_people, start=1):
    person_filename = os.path.join(output_folder, f"{person_name.replace(' ', '_')}.csv")

    if not os.path.exists(person_filename):
        print(f"({index}/{len(original_people)}) Processing {person_name}...")
        start_time = time.time()
        person_data = process_page(person_name)
        save_to_csv(person_filename, person_data)
        print(f"Finished processing {person_name} - Time Taken: {time.time() - start_time:.2f} sec")
    else:
        print(f"({index}/{len(original_people)}) {person_name} already processed. Skipping.")

# Step 3: Build Graph using NetworkX
print("Building the graph...")
G = nx.DiGraph()

# Add the root topic node
G.add_node(topic_title, type="Topic")

# Connect the main topic to all identified people
for person_name in original_people:
    gender = person_gender_map.get(person_name, "Unknown")
    G.add_node(person_name, type="Person", gender=gender)
    G.add_edge(topic_title, person_name)  # Edge from root to person

# Step 4: Establish connections between people
print("Adding connections between people...")
for person_name in original_people:
    person_filename = os.path.join(output_folder, f"{person_name.replace(' ', '_')}.csv")

    if os.path.exists(person_filename):
        with open(person_filename, mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            next(reader)  # Skip header row
            
            for row in reader:
                if row:
                    linked_person = row[0].strip()
                    linked_gender = row[1].strip()

                    if linked_person:
                        if linked_person in original_people:
                            # If linked person is in original list, make a bidirectional edge
                            G.add_edge(person_name, linked_person)
                            G.add_edge(linked_person, person_name)
                        else:
                            # If not in the original list, create a one-directional edge
                            G.add_node(linked_person, type="Person", gender=linked_gender)
                            G.add_edge(person_name, linked_person)

# Step 5: Save the Graph
graph_filename = f"{topic_title.replace(' ', '_')}_Graph.graphml"
nx.write_graphml(G, graph_filename)
print(f"Graph saved as {graph_filename}")
