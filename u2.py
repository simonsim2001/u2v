
import streamlit as st
import pandas as pd
from h2ogpte import H2OGPTE as ArtemisXSL
import csv
import os
import tempfile
from io import StringIO
from dotenv import load_dotenv
from h2ogpte import H2OGPTE

load_dotenv()

# Initialize Artemis clients
client = H2OGPTE(
    address="https://h2ogpte.genai.h2o.ai",
    api_key="sk-6wxubRmRhOv1BAMTxvC9MAzLKfwApSOsJ3vmx06siLwhiOAN"
)

client_2 = H2OGPTE(
    address="https://h2ogpte.genai.h2o.ai",
    api_key="sk-Iqp8na0YJvlg8zOuiTJiI83j6b5OzcsmEDmg4ZdlGvMXZpqr"
)

default_collection_id = "bbfbd9ae-189b-4add-b8dc-df251ec71873"

# Initialize session state
if 'selected_startups' not in st.session_state:
    st.session_state['selected_startups'] = pd.DataFrame()
if 'chat_session_id' not in st.session_state:
    st.session_state['chat_session_id'] = None
if 'chat_name' not in st.session_state:
    st.session_state['chat_name'] = None

def main():
    st.title("Startup Data Dashboard")

    # Load the data
    df = pd.read_csv(
        'https://raw.githubusercontent.com/simonsim2001/u2v/main/U2VStartups_final_with_locations.csv'
    )

    # Data Overview
    st.subheader("Dataset Overview")

    # Calculate key metrics
    total_startups = len(df)
    total_locations = df['location'].nunique() if 'location' in df.columns else 'N/A'
    total_incubators = df['incubator_name'].nunique() if 'incubator_name' in df.columns else 'N/A'
    total_websites = df['website'].nunique() if 'website' in df.columns else 'N/A'

    # Display key metrics
    col1, col3, col4, col5 = st.columns(4)
    col1.metric("Total Startups", total_startups)
    col3.metric("Total Locations", total_locations)
    col4.metric("Total Incubators", total_incubators)
    col5.metric("Total Websites", total_websites)

    # Search Bar
    st.subheader("Search and Filter Startups")
    keywords = st.text_input("Enter keywords to search (separate by commas)")

    # Split the keywords by comma and remove any leading/trailing spaces
    keyword_list = [kw.strip() for kw in keywords.split(',')] if keywords else []

    # Filter the dataframe by the keywords
    if keyword_list:
        filtered_df = df.copy()
        for keyword in keyword_list:
            filtered_df = filtered_df[
                filtered_df.apply(
                    lambda row: row.astype(str).str.contains(keyword, case=False).any(),
                    axis=1
                )
            ]
    else:
        filtered_df = df.copy()

    # Display the filtered dataframe
    st.subheader("Filtered Startups")
    st.dataframe(filtered_df)

    # Interactive multiselect for selecting startups by name from the filtered list
    if 'name' in filtered_df.columns:
        st.subheader("Select Startups from Filtered List")
        selected_filtered_names = st.multiselect(
            "Select startups from the filtered list to add to your selection",
            filtered_df['name'].unique()
        )
    else:
        st.write("No 'name' column found in the dataset.")

    # Interactive multiselect for selecting startups by name from the entire dataset
    if 'name' in df.columns:
        st.subheader("Select Startups from Entire Dataset")
        selected_all_names = st.multiselect(
            "Select startups from the entire dataset to add to your selection",
            df['name'].unique()
        )
    else:
        st.write("No 'name' column found in the dataset.")

    # Combine selected names
    selected_names = list(set(selected_filtered_names + selected_all_names))

    # Add selected startups to the session state
    if st.button("Add selected startups"):
        selected_startups = df[df['name'].isin(selected_names)] if 'name' in df.columns else pd.DataFrame()
        st.session_state['selected_startups'] = pd.concat(
            [st.session_state['selected_startups'], selected_startups]
        ).drop_duplicates().reset_index(drop=True)
        st.success(f"Added {len(selected_startups)} startups to your list.")

    # Display the selected startups
    if not st.session_state['selected_startups'].empty:
        st.subheader("Selected Startups")
        st.dataframe(st.session_state['selected_startups'])

        # Button to download selected data as CSV
        csv_data = st.session_state['selected_startups'].to_csv(index=False)
        st.download_button(
            label="Download selected startups as CSV",
            data=csv_data,
            file_name='selected_startups.csv',
            mime="text/csv"
        )

        # Button to ingest selected startups into Artemis
        if st.button("Ingest Selected Startups into Artemis"):
            ingest_selected_startups(st.session_state['selected_startups'])

    else:
        st.info("No startups selected yet.")


    # Artemis Q&A Section
    st.title("Ask Questions about the Startups")

    # Switch collection mode
    switch_collection_mode()

    # Load recent chats
    load_recent_chats()

    # Submit question
    submit_question()

    # Download conversation
    download_conversation()

    # Document Management
    st.sidebar.header("Document Database")
    list_and_delete_documents(default_collection_id)

    # Upload and ingest documents (allowing CSV files)
    uploaded_files = st.file_uploader("Upload additional documents (PDF, CSV, TXT)", type=["pdf", "csv", "txt"], accept_multiple_files=True)
    if uploaded_files and st.button('Upload and Ingest Files'):
        for uploaded_file in uploaded_files:
            upload_and_ingest_document(default_collection_id, uploaded_file)

def ingest_selected_startups(selected_df):
    """Ingest the selected startups data into Artemis."""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp:
            selected_df.to_csv(tmp.name, index=False)
            tmp_path = tmp.name

        # Upload the CSV file to Artemis
        with open(tmp_path, "rb") as f:
            with st.spinner(f"Uploading selected startups to Artemis..."):
                upload_id = client_2.upload('selected_startups.csv', f)
                st.success("Upload successful.")

        # Ingest the uploaded CSV into the collection
        with st.spinner("Processing document..."):
            response = client_2.ingest_uploads(
                collection_id=default_collection_id,
                upload_ids=[upload_id],
                gen_doc_summaries=False,
                gen_doc_questions=False
            )
            st.success("Selected startups ingested into Artemis.")

        # Clean up the temporary file
        os.unlink(tmp_path)

    except Exception as e:
        st.error(f"Error ingesting selected startups: {e}")

def start_new_chat():
    """Create a new chat session and update session state."""
    try:
        st.session_state.chat_session_id = client.create_chat_session_on_default_collection()
        st.session_state.chat_name = "New Conversation"
        st.info("Started a new chat session.")
    except Exception as e:
        st.error(f"Failed to start a new chat session: {str(e)}")

def display_chat_history(session_id):
    """Display the chat history for a given session ID."""
    if session_id:
        try:
            messages = client.list_chat_messages_full(chat_session_id=session_id, offset=0, limit=100)
            for message in messages:
                author = "You" if message.reply_to is None else "Artemis"
                st.write(f"{author} says: {message.content}")
        except Exception as e:
            st.error(f"Failed to load chat history for session {session_id}: {str(e)}")

def load_recent_chats():
    """Load and allow selection of recent chat sessions."""
    st.sidebar.header("Chat History")
    try:
        recent_chats = client.list_recent_chat_sessions(offset=0, limit=50)
        if not recent_chats:
            st.sidebar.write("No recent chats available.")
            return

        chat_descriptions = [f"{chat.collection_name} - {chat.updated_at.strftime('%Y-%m-%d %H:%M:%S')}" for chat in recent_chats]
        chat_ids = [chat.id for chat in recent_chats]

        selected_chat_index = st.sidebar.selectbox("Select a chat:", options=range(len(chat_descriptions)), format_func=lambda x: chat_descriptions[x])
        selected_chat_id = chat_ids[selected_chat_index]

        if st.session_state.chat_session_id != selected_chat_id:
            st.session_state.chat_session_id = selected_chat_id
            st.rerun()

    except Exception as e:
        st.sidebar.error(f"Failed to load recent chats: {str(e)}")

def display_references(message_id, user_question):
    """Display references for a given message, match document names with IDs, and search for chunks in each document."""
    try:
        references = client.list_chat_message_references(message_id)
        documents = client.list_documents_in_collection(collection_id=default_collection_id, offset=0, limit=100)
        doc_name_to_id = {doc.name: doc.id for doc in documents}
        document_chunks_fetched = {}

        if references:
            st.write("\n")
            st.markdown("### References (up to 8):", unsafe_allow_html=True)
            for ref in references[:8]:
                doc_name = ref.document_name
                score = ref.score

                document_id = doc_name_to_id.get(doc_name)
                if not document_id:
                    st.write(f"Document name '{doc_name}' not found in collection.")
                    continue

                offset = document_chunks_fetched.get(document_id, 0)

                search_results = client.search_chunks(
                    collection_id=default_collection_id,
                    query=user_question,
                    topics=[document_id],
                    offset=offset,
                    limit=1
                )

                if search_results:
                    result = search_results[0]
                    cutoff_index = result.text[:1200].rfind('.') + 1
                    displayed_text = result.text[:cutoff_index] if cutoff_index > 0 else result.text[:1200]
                    ref_details = f"<div style='font-family:\"Arial\", sans-serif;font-size:16px;padding:10px;border-left:3px solid #007BFF;margin-bottom:10px;'><strong>Document:</strong> {doc_name}, <strong>Score:</strong> {score}<br><strong>Text:</strong> {displayed_text}</div>"
                    st.markdown(ref_details, unsafe_allow_html=True)

                    document_chunks_fetched[document_id] = offset + 1
                else:
                    st.write(f"No additional text found for '{doc_name}' at offset {offset}.")
        else:
            st.write("No references found for this response.")
    except Exception as e:
        st.error(f"Failed to load references: {str(e)}")

def submit_question():
    """Submit a user question to the current chat session and display the response with references."""
    with st.form(key='Question_Form'):
        user_question = st.text_input("Ask your question here:", key="question_input")
        submit_button = st.form_submit_button("Submit")
    
    if submit_button and user_question:
        if 'chat_session_id' not in st.session_state or st.session_state['chat_session_id'] is None:
            start_new_chat()
        try:
            with st.spinner('Waiting for Artemis...'):
                with client.connect(st.session_state['chat_session_id']) as session:
                    response = session.query(user_question)
                    st.markdown(f'<div style="font-family:sans-serif;font-size:16px">{response.content}</div>', unsafe_allow_html=True)
                    display_references(response.id, user_question)
        except Exception as e:
            st.error(f"Failed to submit question: {str(e)}")

def switch_collection_mode():
    """Allows switching the RAG type for the Artemis collection directly upon selection using a radio button interface."""
    rag_types = {
        "Creative [~10s.]": "rag",
        "Focus [~15s.]": "hyde2",
        "Laser Cut [~45s.]": "rag+"
    }
    
    st.sidebar.header("System Controls")
    selected_mode = st.sidebar.radio("Choose mode:", list(rag_types.keys()), key='selected_mode')

    if st.session_state['selected_mode'] and rag_types[st.session_state['selected_mode']] != st.session_state.get('last_mode', None):
        st.session_state['last_mode'] = rag_types[st.session_state['selected_mode']]
        with st.spinner("Applying changes..."):
            try:
                update_result = client.update_collection_rag_type(
                    collection_id=default_collection_id,
                    name="Artemis",
                    description="Artemis collection",
                    rag_type=rag_types[st.session_state['selected_mode']]
                )
                st.sidebar.success(f"Mode switched to {st.session_state['selected_mode']}.")
            except Exception as e:
                st.sidebar.error(f"Failed to apply mode: {str(e)}")

def download_conversation():
    """Allow users to download their conversation as a CSV file, with an option to include references."""
    include_references = st.radio("Include references in the download?", ("Yes (only available for the initial session)", "No"))

    if st.button("Prepare Download Conversation"):
        with st.spinner('Preparing your download, please wait...'):
            if 'chat_session_id' in st.session_state:
                try:
                    messages = client.list_chat_messages_full(chat_session_id=st.session_state['chat_session_id'], offset=0, limit=100)
                    documents = client.list_documents_in_collection(collection_id=default_collection_id, offset=0, limit=100)
                    doc_name_to_id = {doc.name: doc.id for doc in documents}
                    
                    filename = "conversation_with_references.csv" if include_references == "Yes (only available for the initial session)" else "conversation.csv"

                    csv_file = StringIO()
                    writer = csv.writer(csv_file)
                    headers = ['Dialogue']
                    if include_references == "Yes (only available for the initial session)":
                        headers.append('References')
                    writer.writerow(headers)

                    for message in messages:
                        if message.reply_to is None:
                            author = "You: "
                        else:
                            author = "Artemis: "
                        
                        message_line = f"{author}{message.content}"

                        references_info = ""
                        if author == "Artemis: " and include_references == "Yes (only available for the initial session)":
                            ref_data = client.list_chat_message_references(message_id=message.id)
                            for ref in ref_data[:5]:
                                doc_name = ref.document_name
                                score = ref.score
                                document_id = doc_name_to_id.get(doc_name)

                                if not document_id:
                                    references_info += f"\nDocument name '{doc_name}' not found in collection.\n\n"
                                    continue

                                search_results = client.search_chunks(
                                    collection_id=default_collection_id,
                                    query=message.content,
                                    topics=[document_id],
                                    offset=0,
                                    limit=1
                                )

                                if search_results:
                                    result = search_results[0]
                                    cutoff_index = result.text[:1000].rfind('.') + 1
                                    displayed_text = result.text[:cutoff_index] if cutoff_index > 0 else result.text[:1000]
                                    references_info += f"Document: {doc_name}, Score: {score}, Text: {displayed_text.strip()}\n\n"
                                else:
                                    references_info += f"Document: {doc_name}, Score: {score}, Text: No text found.\n\n"

                        row = [message_line]
                        if include_references == "Yes (only available for the initial session)":
                            row.append(references_info)
                        writer.writerow(row)

                    csv_file.seek(0)
                    csv_bytes = csv_file.getvalue().encode()
                    csv_file.close()
                    
                    st.download_button(label="Download CSV", data=csv_bytes, file_name=filename, mime='text/csv')
                except Exception as e:
                    st.error(f"Failed to download conversation: {str(e)}")
            else:
                st.warning("No active chat session available to download.")

def upload_and_ingest_document(collection_id, uploaded_file):
    """Uploads and ingests a single document to the specified collection using a dedicated API key."""
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp:
            tmp.write(uploaded_file.getbuffer())
            tmp_path = tmp.name

        with open(tmp_path, "rb") as f:
            with st.spinner(f"Uploading {uploaded_file.name}..."):
                upload_id = client_2.upload(uploaded_file.name, f)
                st.success("Upload successful.")

        with st.spinner("Processing document..."):
            response = client_2.ingest_uploads(
                collection_id=collection_id,
                upload_ids=[upload_id],
                gen_doc_summaries=False,
                gen_doc_questions=False
            )
            st.success("Document processed successfully.")

    except Exception as e:
        st.error(f"Error processing {uploaded_file.name}: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

def delete_document(document_id):
    """Delete a specific document by ID with user confirmation."""
    confirm_key = f"confirm_delete_{document_id}"

    if st.session_state.get(confirm_key, False):
        try:
            client_2.delete_documents([document_id])
            st.sidebar.success(f"Document {document_id} deleted successfully.")
            del st.session_state[confirm_key]
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"Failed to delete document: {str(e)}")
            if confirm_key in st.session_state:
                del st.session_state[confirm_key]
    else:
        if st.sidebar.button(f"Delete {document_id}", key=f"delete_{document_id}"):
            st.session_state[confirm_key] = True
            st.sidebar.warning("Click again to confirm deletion. This action cannot be reversed!")

def list_and_delete_documents(collection_id):
    """List and provide an option to delete documents from the collection."""
    try:
        documents = client_2.list_documents_in_collection(collection_id, offset=0, limit=100)
        num_documents = len(documents)
        capacity_percentage = (num_documents / 100) * 100  # Assuming 100 is the max capacity

        st.sidebar.metric(label="Artemis Capacity on Current Data", value=f"{capacity_percentage:.0f}%", delta=None)

        if documents:
            for doc in documents:
                st.sidebar.text(doc.name)
                delete_document(doc.id)
        else:
            st.sidebar.write("No documents available to display.")
    except Exception as e:
        st.sidebar.error(f"Error retrieving documents: {str(e)}")

if __name__ == "__main__":
    main()

