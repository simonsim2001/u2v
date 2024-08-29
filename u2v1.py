import streamlit as st
import pandas as pd

# Load the data
df = pd.read_csv('https://raw.githubusercontent.com/simonsim2001/u2v/main/U2VStartups_final_with_locations.csv')

# Initialize session state for selected startups
if 'selected_startups' not in st.session_state:
    st.session_state['selected_startups'] = pd.DataFrame()

# Streamlit interface
st.title("Startup Data Dashboard")

# Data Overview
st.subheader("Dataset Overview")
total_startups = len(df)
unique_categories = df['Category'].nunique() if 'Category' in df.columns else 'N/A'
locations = df['Location'].nunique() if 'Location' in df.columns else 'N/A'

st.write(f"**Total Startups:** {total_startups}")

# Search Bar
st.subheader("Search and Filter Startups")
keywords = st.text_input("Enter keywords to search (separate by commas)")

# Split the keywords by comma and remove any leading/trailing spaces
keyword_list = [kw.strip() for kw in keywords.split(',')] if keywords else []

# Filter the dataframe by the keywords
if keyword_list:
    filtered_df = df.copy()
    for keyword in keyword_list:
        filtered_df = filtered_df[filtered_df.apply(lambda row: row.astype(str).str.contains(keyword, case=False).any(), axis=1)]
else:
    filtered_df = df

# Interactive Table with Selection by Name
st.subheader("Select Startups")
if 'name' in filtered_df.columns:
    selected_names = st.multiselect("Select startups by name to add to your list", filtered_df['name'].unique())
    filtered_df = filtered_df[filtered_df['name'].isin(selected_names)] if selected_names else filtered_df
else:
    st.write("No 'name' column found in the dataset.")

st.dataframe(filtered_df)

# Add selected startups to the session state
if st.button("Add selected startups"):
    selected_startups = df[df['Name'].isin(selected_names)] if 'Name' in df.columns else pd.DataFrame()
    st.session_state['selected_startups'] = pd.concat([st.session_state['selected_startups'], selected_startups]).drop_duplicates().reset_index(drop=True)
    st.success(f"Added {len(selected_startups)} startups to your list.")

# Display the selected startups
if not st.session_state['selected_startups'].empty:
    st.subheader("Selected Startups")
    st.dataframe(st.session_state['selected_startups'])

    # Button to download selected data as CSV
    csv = st.session_state['selected_startups'].to_csv(index=False)
    st.download_button(label="Download selected startups as CSV", data=csv, mime="text/csv")

# Run the app using 'streamlit run <your_script.py>'