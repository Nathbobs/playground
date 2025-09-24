import getpass
import os

from termcolor import colored
from langchain_community.vectorstores import Chroma
from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from langchain_community.chat_models import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv

load_dotenv()  # take environment variables from .env.

chroma_db = "chroma_db/"  # directory to store the vector db

#initializing the embedding model
print("Initializing embedding model...")
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
print("Initialized embedding model.")

print("Loading Chroma DB...")
db = Chroma(persist_directory=chroma_db, embedding_function=embeddings)
print("Chroma DB loaded.")

print("#------------------------")
llm = ChatOpenAI(model="gpt-3.5-turbo", 
                 temperature=0.9, 
                 api_key=os.getenv("OPENAI_API_KEY"))
                 
print("Initialized LLM.")


#setting up RAG
custom_prompt = PromptTemplate(
    input_variables=["context", "question"],
    template="""Use the following context to answer the question. If you do not know the answer, 
    just say that you do not have enough information to answer the provided research. Don't try to come up with an answer.
    \n\nContext: {context}\n\nQuestion: {question}\n\nAnswer:""",
)

QA_CHAIN_PROMPT = custom_prompt #using the custom prompt template

#retrieve the search results
retriever = db.as_retriever(search_type="similarity",search_kwargs={"k": 4}) #retrieving top 3 similar docs
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=retriever,
    return_source_documents=True,
    chain_type_kwargs={"prompt": QA_CHAIN_PROMPT},

)
print("RAG setup complete.")

#chat loop

print("#----------------------------------------------------------------------------------")
print("You can start chatting with the documents now! Type 'exit' to quit.")

#-----------
while True:
    query = input(colored("\nEnter your question: ", "blue", attrs=["bold"]))
    if query.lower() == "exit":
        print("Exiting the chat. Goodbye!")
        break

    print("Processing your question...")
    result = qa_chain({"query": query})

    answer = result["result"]
    source_docs = result["source_documents"]

    print(colored(f"\nAnswer: {answer}\n","green", attrs=["bold"]))
    print(colored("""------------------------------------------------------------------------------------------------------------\n""" , "yellow", attrs=["bold"]))
    print("Source Documents:")
    for i, doc in enumerate(source_docs):
        print(colored(f"\nDocument {i + 1}:\n{doc.page_content}\n", "light_red"))
    print("""---------------------------------------------------------------------------------------------------------------------\n """)
