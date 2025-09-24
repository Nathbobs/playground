from langchain_community.vectorstores import Chroma
from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders.pdf import PyPDFDirectoryLoader
from dotenv import load_dotenv
import getpass 
import os

load_dotenv() # take environment variables from .env.

data = "data/" #directory of pdf files
chroma_db = "chroma_db/" #directory to store the vectore db

# def load_documents():
#     #loading files from data\ directory
#     print ( "Loading documents..." )
#     loader = PyPDFDirectoryLoader(data)
#     documents = loader.load()
#     print(f"Loaded {len(documents)} documents from {data} directory.")

#loading files from data\ directory
print ( "Loading documents..." )
loader = PyPDFDirectoryLoader(data)
documents = loader.load()
print(f"Loaded {len(documents)} documents from {data} directory.")    


#-------splitting the docs
print ( "Splitting documents..." )
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000, 
    chunk_overlap=200,
    length_function=len,
    )
texts = text_splitter.split_documents(documents)
print(f"Split into {len(texts)} chunks of text.")

#downloading hugging face model
print ( "Downloading embedding model..." )
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
print("Downloaded embedding model.")

#creating the vectore store
print ( "Creating vector store..." )

db = Chroma.from_documents(
    documents = texts,
    embedding = embeddings, 
    persist_directory=chroma_db
    )
db.persist()
print("Created and persisted vector store.")

#load_documents()


# docs_loader = load_documents()
# print (docs_loader[0])






#--------------
# if "OPEN_API_KEY" not in os.environ:
#     os.environ["OPEN_API_KEY"] = getpass.getpass("Enter your OpenAI API key: ")

# vectore_store = InMemoryVectorStore.from_documents(pages, OpenAIEmbeddings())
# docs = vectore_store.similarity_search("Explain to me the Launch Conjuction assessment (LCA) in spacemap", k=2)

# for doc in docs:
#     print(f"Page {doc.metadata['page']}: {doc.page_content [:300]}\n")
