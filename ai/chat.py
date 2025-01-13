import json
from langchain_openai import ChatOpenAI
from langchain_community.document_loaders import JSONLoader
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from dotenv import load_dotenv
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_core.prompts import ChatPromptTemplate
import os

class Chat:
    files = ["ai/data/gameJam.json"]
    documents: list[Document] = []
    def __init__(self):
        load_dotenv()
        self.llm = ChatOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ["OPENROUTER_API_KEY"],
            temperature=0,
            model="meta-llama/llama-3.2-3b-instruct:free")
        self.vectorstore = InMemoryVectorStore(embedding=HuggingFaceEmbeddings(model_name="intfloat/multilingual-e5-large"))

    def initalize(self):
        print("Loading documents")
        for file in self.files:
            doc = self._prepareDocument(file)
            self.documents.extend(doc)
            print("Documents loaded")
        self.vectorstore.add_documents(self.documents)

    def response(self, content: str):
        vector_context = self.vectorstore.as_retriever(search_kwargs={"k": 3}).invoke(content)
        templete = ChatPromptTemplate([
            ("system", str("""
            > **System Instruction** You are an AI assistant strictly designed to retrieve information from a vector database. You are not allowed to generate or infer any information that is not explicitly stored in the vector database. Follow these guidelines to assist students effectively:
            > **Your role:** You are a Computer Science club assistant agent tasked with helping students find resources, classes, and events based on their specific queries.
            > **Task:** Use Retrieval Argmented Generation (RAG) to provide the relevant informations based on the student's query.
            > **Process:**
            > 1. **Understand the query:** Carefully analyze the student's query to idnetify the main keywords and context (eg. classes, events, or resources).
            > 2. **Retrieve relevant information:** Search through a vast database of resources, classes and events to find the most pertinent data.
            > 3. **Generate a response:** Combine the retrieved information to create a concise and informative response that includes the most relavant information, along with brief summaries of their content. 
            > Below is an example of how you can respond to a student's query:
            > **Example Query:** "what is the 2025 Game Jam?"
            > **Example Response:** "Based on your query, here are the answer(s) to your questions:
            > The 2025 Game Jam is an annual event that brings together game developers from around the world to collaborate and create innovative games. 
            
            **Additional Considerations:**
            By strictly adhering to the above guidelines, you will provide students with valuable information to help them make informed decisions.
            """)), ("system", "context:\n\n {user_context}"), ("user", "{user_input}")
            ])
        
        response = templete.invoke({
            "user_context": vector_context,
            "user_input": content
        })
        
        for chunk in self.llm.stream(response):
            yield chunk.content.replace("\u0000", "")
        return chunk.content
    
    def _prepareDocument(self, file_path: str):
        if not os.path.exists(file_path):
            raise "File does not exist"
        
        loader = JSONLoader(
            file_path=file_path,
            jq_schema=".content[]",  
            text_content=False,
        ) 
        docs = loader.load()
        return docs;
              

    def parse_document(self, document: str):
        lines = document.split("\n")
        data = {}
        for line in lines:
            if line.strip():
                key, value = line.split(":", 1)
                data[key.strip()] = value.strip()
                if value.strip().startswith("["):
                    data[key.strip()] = [item.strip().strip("'") for item in value.strip()[1:-1].split("', '")]
        return data


    def generateEmbedding(self, context: list[str]):
        embedding = HuggingFaceEmbeddings(model_name="intfloat/multilingual-e5-large")
        vector = embedding.embed_documents(context)
        return vector