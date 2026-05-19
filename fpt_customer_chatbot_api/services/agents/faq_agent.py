import os
import glob
import re
from typing import List

import faiss
from langchain_openai import ChatOpenAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_core.documents import Document
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_experimental.text_splitter import SemanticChunker
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever

from state.agent_state import CompleteOrEscalate

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    api_key=os.getenv("OPENAI_API_KEY")
)

# ---------------------------------------------------------------------------
# Advanced RAG Setup: Load, Chunk, and Index
# ---------------------------------------------------------------------------

_ensemble_retriever = None


def _get_ensemble_retriever():
    """Lazy-load the Ensemble Retriever (FAISS HNSW + BM25)."""
    global _ensemble_retriever
    if _ensemble_retriever is not None:
        return _ensemble_retriever

    data_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "data"
    )

    txt_files = glob.glob(os.path.join(data_dir, "*.txt"))
    if not txt_files:
        return None

    # Use open-source HuggingFace embeddings (all-MiniLM-L6-v2)
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    # Use Semantic Chunking instead of recursive character
    semantic_chunker = SemanticChunker(embeddings)
    all_chunks = []

    for file_path in txt_files:
        try:
            loader = TextLoader(file_path, encoding='utf-8')
            documents = loader.load()
            # Semantic chunker splits by sentences and groups them based on embedding similarity
            chunks = semantic_chunker.split_documents(documents)
            all_chunks.extend(chunks)
        except Exception as e:
            print(f"Error loading {file_path}: {e}")

    if not all_chunks:
        return None

    # --- Build Sparse Retriever (BM25) ---
    bm25_retriever = BM25Retriever.from_documents(all_chunks)
    bm25_retriever.k = 3

    # --- Build Dense Retriever (FAISS HNSW) ---
    # all-MiniLM-L6-v2 produces 384-dimensional embeddings
    dimension = 384 
    # Use HNSW index for fast approximate nearest neighbor search
    index = faiss.IndexHNSWFlat(dimension, 32)
    
    faiss_vectorstore = FAISS(
        embedding_function=embeddings,
        index=index,
        docstore=InMemoryDocstore(),
        index_to_docstore_id={}
    )
    
    # Add chunks to FAISS
    faiss_vectorstore.add_documents(all_chunks)
    faiss_retriever = faiss_vectorstore.as_retriever(search_kwargs={"k": 3})

    # --- Combine into Ensemble Retriever ---
    _ensemble_retriever = EnsembleRetriever(
        retrievers=[bm25_retriever, faiss_retriever],
        weights=[0.3, 0.7] # Prioritize dense search but keep keyword matching
    )
    
    return _ensemble_retriever


# ---------------------------------------------------------------------------
# Query Transformation Tools
# ---------------------------------------------------------------------------

def decompose_query(query: str) -> List[str]:
    """Break a complex query into simpler sub-queries using LLM."""
    prompt = ChatPromptTemplate.from_template(
        "You are an AI assistant helping to search a policy database.\n"
        "Break the following question into 1-3 simpler, distinct sub-questions.\n"
        "If the question is already simple, just return the original question.\n"
        "Return each sub-question on a new line without bullets or numbers.\n\n"
        "Question: {query}"
    )
    chain = prompt | llm
    response = chain.invoke({"query": query})
    
    # Split by newlines and clean up
    sub_queries = [line.strip("- *1234567890. ") for line in response.content.strip().split('\n') if line.strip()]
    if query not in sub_queries:
        sub_queries.insert(0, query) # Always include the original
    return sub_queries[:3]


def generate_hyde(query: str) -> str:
    """Generate a hypothetical document answer using LLM."""
    prompt = ChatPromptTemplate.from_template(
        "You are an expert HR and Compliance officer at FPT Software.\n"
        "Write a short, hypothetical excerpt from the company's official policy document "
        "that would directly answer the following question.\n"
        "Write in Vietnamese if the question is in Vietnamese.\n\n"
        "Question: {query}"
    )
    chain = prompt | llm
    response = chain.invoke({"query": query})
    return response.content


# ---------------------------------------------------------------------------
# Execution Tool
# ---------------------------------------------------------------------------

@tool
def fpt_policy_search(query: str) -> str:
    """Search FPT Software company policies, code of conduct, guidelines, and benefits.
    Use this for questions about company rules, ethics, compliance, and HR policies."""
    retriever = _get_ensemble_retriever()
    if retriever is None:
        return "⚠️ FAQ knowledge base not available. The policy documents could not be loaded."

    # 1. Query Decomposition
    sub_queries = decompose_query(query)
    
    all_retrieved_docs = []
    
    # 2. HyDE & Retrieval for each query
    for sq in sub_queries:
        hype_doc = generate_hyde(sq)
        # Search using the hypothetical document text
        docs = retriever.invoke(hype_doc)
        all_retrieved_docs.extend(docs)

    # 3. Deduplication
    unique_docs = {}
    for doc in all_retrieved_docs:
        # Use page_content hash or length as a simple unique ID
        doc_id = hash(doc.page_content)
        if doc_id not in unique_docs:
            unique_docs[doc_id] = doc

    # Sort top 5 docs by combining metadata or keeping them as-is 
    # (EnsembleRetriever already attempts to sort, but since we aggregated multiple runs, we'll just take the top 5 unique ones)
    final_docs = list(unique_docs.values())[:5]

    if not final_docs:
        return "No relevant policy information found for your query."

    # 4. Format Results
    formatted = []
    for i, doc in enumerate(final_docs, 1):
        source = doc.metadata.get("source", "Unknown")
        filename = os.path.basename(source)
        content = doc.page_content.strip()
        formatted.append(
            f"**Source {i}** (File: {filename}):\\n{content}"
        )

    return "\\n\\n---\\n\\n".join(formatted)


faq_tools = [fpt_policy_search]

faq_agent_prompt = ChatPromptTemplate.from_messages([
    ("system",
     """You are the **FAQ Agent** for FPT Software's customer service system.

Your capabilities:
- Search FPT Software's Code of Business Conduct and company policies (fpt_policy_search)
- Answer questions about company rules, ethics, compliance, benefits, and guidelines

Rules:
1. Always search the policy database before answering.
2. Provide answers with source page references.
3. If the answer is not in the policy documents, clearly state that.
4. When the user's FAQ question is answered or they want to switch topics, call 'CompleteOrEscalate'.
5. Be accurate — do not fabricate policy information.

Current Context:
- User ID: {user_id}
- Email: {email}
- Conversation ID: {conversation_id}
"""),
    ("placeholder", "{messages}")
])

faq_agent_runnable = faq_agent_prompt | llm.bind_tools(
    faq_tools + [CompleteOrEscalate]
)
