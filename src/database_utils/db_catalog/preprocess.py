import os
from pathlib import Path
import logging
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain.schema.document import Document
from langchain_openai import OpenAIEmbeddings
from langchain_google_vertexai import VertexAIEmbeddings
from google.oauth2 import service_account
from google.cloud import aiplatform
import vertexai

from database_utils.db_catalog.csv_utils import load_tables_description

load_dotenv(override=True)

GCP_PROJECT = os.getenv("GCP_PROJECT")
GCP_REGION = os.getenv("GCP_REGION")
GCP_CREDENTIALS = os.getenv("GCP_CREDENTIALS")

if GCP_CREDENTIALS and GCP_PROJECT and GCP_REGION:
    aiplatform.init(
    project=GCP_PROJECT,
    location=GCP_REGION,
    credentials=service_account.Credentials.from_service_account_file(GCP_CREDENTIALS)
    )
    vertexai.init(project=GCP_PROJECT, location=GCP_REGION, credentials=service_account.Credentials.from_service_account_file(GCP_CREDENTIALS))


# EMBEDDING_FUNCTION = VertexAIEmbeddings(model_name="text-embedding-004")#OpenAIEmbeddings(model="text-embedding-3-large")
EMBEDDING_FUNCTION = OpenAIEmbeddings(model="text-embedding-3-large")


def make_db_context_vec_db(db_directory_path: str, db_manager=None, text_chunks=None, ids=None, source_id_list=None, metadata_list=None, database_manager=None, **kwargs) -> None:
    """
    Creates a context vector database for the specified database directory.
    Supports both structured table descriptions and direct text input.

    Args:
        db_directory_path (str): The path to the database directory.
        db_manager (DatabaseInterface, optional): Database manager for MySQL-backed storage.
                                                If None, uses traditional ChromaDB storage.
        text_chunks (List[str], optional): Alternative input - list of text chunks to vectorize.
        ids (List[str], optional): Alternative input - IDs for each text chunk.
        source_id_list (List[str], optional): Alternative input - source IDs for each text chunk.
        metadata_list (List[Dict], optional): Alternative input - metadata for each text chunk.
        database_manager (DatabaseInterface, optional): Alternative parameter name for db_manager (for compatibility).
        **kwargs: Additional keyword arguments, including:
            - use_value_description (bool): Whether to include value descriptions (default is True).
    """
    # Handle alternative parameter name for backward compatibility
    if database_manager is not None and db_manager is None:
        db_manager = database_manager
        
    # Set default values
    db_id = Path(db_directory_path).name if isinstance(db_directory_path, (str, Path)) else "default"
    use_value_description = kwargs.get("use_value_description", True)
    docs = []
    
    # Determine input mode based on parameters
    using_direct_input = text_chunks is not None and ids is not None
    
    if using_direct_input:
        # Direct text input mode
        logging.info(f"Using direct input mode with {len(text_chunks)} text chunks")
        
        # Create documents from direct input
        for i, text in enumerate(text_chunks):
            chunk_id = ids[i] if i < len(ids) else f"chunk_{i}"
            chunk_source_id = source_id_list[i] if source_id_list and i < len(source_id_list) else db_id
            chunk_metadata = metadata_list[i] if metadata_list and i < len(metadata_list) else {}
            
            # Add text_chunk_id to metadata
            chunk_metadata["text_chunk_id"] = chunk_id
            
            # Create document
            docs.append(Document(page_content=text, metadata=chunk_metadata))
            
    elif isinstance(db_directory_path, (str, Path)):
        # Traditional table description mode
        table_description = load_tables_description(db_directory_path, use_value_description)
        
        # Process all descriptions into documents
        for table_name, columns in table_description.items():
            for column_name, column_info in columns.items():
                metadata = {
                    "table_name": table_name,
                    "original_column_name": column_name,
                    "column_name": column_info.get('column_name', ''),
                    "column_description": column_info.get('column_description', ''),
                    "value_description": column_info.get('value_description', '') if use_value_description else "",
                    "text_chunk_id": f"{table_name}_{column_name}"
                }
                for key in ['column_name', 'column_description', 'value_description']:
                    if column_info.get(key, '').strip():
                        docs.append(Document(page_content=column_info[key], metadata=metadata))
    else:
        raise ValueError("Either db_directory_path or text_chunks/ids must be provided")
        
    logging.info(f"Creating context vector database with {len(docs)} documents")
    
    # Choose storage method based on db_manager
    if db_manager is not None:
        # Use MySQL + ChromaDB integration via database manager
        logging.info(f"Using database manager for vector storage")
        
        # Compute embeddings for all documents
        logging.info(f"Computing {len(docs)} embeddings")
        texts = [doc.page_content for doc in docs]
        
        # Handle empty document case
        if not texts:
            logging.warning("No text content to embed")
            return
            
        embeddings = EMBEDDING_FUNCTION.embed_documents(texts)
        
        # Store each vector using the database manager
        logging.info(f"Storing vectors in database")
        for i, doc in enumerate(docs):
            # Extract source_id from metadata or use default
            source_id = doc.metadata.get("source_id", db_id)
            
            # Store through database interface
            try:
                db_manager.store_vector(
                    vector=embeddings[i],
                    metadata=doc.metadata,
                    source_id=source_id
                )
            except Exception as e:
                logging.error(f"Error storing vector {i}: {e}")
            
        logging.info(f"Successfully stored {len(docs)} vectors using database manager")
    else:
        # Traditional ChromaDB storage
        if not isinstance(db_directory_path, (str, Path)):
            raise ValueError("db_directory_path must be provided for ChromaDB storage")
            
        vector_db_path = Path(db_directory_path) / "context_vector_db"

        if vector_db_path.exists():
            os.system(f"rm -r {vector_db_path}")

        vector_db_path.mkdir(exist_ok=True)

        # Store documents directly in ChromaDB
        Chroma.from_documents(docs, EMBEDDING_FUNCTION, persist_directory=str(vector_db_path))
        logging.info(f"Context vector database created at {vector_db_path}")
