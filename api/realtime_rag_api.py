import os
import pathway as pw
from pathway.stdlib.ml.index import KNNIndex
from pathway.xpacks.llm import embedders
from datetime import datetime
from common.llm_helper import openai_chat_completion

# Load environment variables
embedding_dimension = int(os.environ.get("EMBEDDING_DIMENSION", 1536))
embedder = embedders.SentenceTransformerEmbedder(model="intfloat/e5-large-v2")

# ✅ Define schemas
class MedicalDataSchema(pw.Schema):
    doc: str  # Medical research articles

class QueryInputSchema(pw.Schema):
    query: str  # Incoming doctor query

def prompt(index, embedded_query, user_query):
    """Generates AI response based on indexed medical documents."""
    if user_query is None:
        print("No valid query received, skipping prompt generation.")
        return None

    print("Generating prompt for query:", user_query)

    @pw.udf
    def build_prompt(local_indexed_data: list, query: str) -> str:
        docs_str = "\n".join(local_indexed_data)
        return f"Given the following data:\n{docs_str}\nAnswer this query: {query}. Assume that current date is {datetime.now()}. Clean the output."

    relevant_docs = index.get_nearest_items(
        embedded_query.vector, k=3, collapse_rows=True
    ).select(local_indexed_data_list=pw.this.doc)

    query_context = embedded_query + relevant_docs.promise_universe_is_equal_to(embedded_query)

    # Ensure user_query is directly passed as a string, not as a class or other object
    generated_prompt = query_context.select(
        prompt=build_prompt(pw.this.local_indexed_data_list, user_query)  # Make sure user_query is a string
    )

    print("Generated prompt:", generated_prompt.to_pandas())  # Debugging

    response = generated_prompt.select(
        query_id=pw.this.id,
        result=openai_chat_completion(pw.this.prompt)
    )

    return response


def run(host, port):
    """Handles clinical queries and returns AI-generated responses."""
    print("Server will start...")
    print("Initializing Pathway real-time RAG API...")

    query, response_writer = pw.io.http.rest_connector(
        host=host,
        port=port,
        schema=QueryInputSchema,
        autocommit_duration_ms=50,
        delete_completed_queries=True,  
    )

    if query.query is not None:
        print(f"Received query: {query.query}, proceeding with processing.")

        print("Loading medical literature data...")
        medical_data = pw.io.jsonlines.read(
            "./pubmed_full_articles.jsonl",
            schema=MedicalDataSchema,
            mode="streaming"
        )

        print("Computing embeddings for documents...")
        embedded_data = medical_data + medical_data.select(vector=embedder(pw.this.doc))

        print("Indexing embeddings...")
        index = KNNIndex(embedded_data.vector, embedded_data, n_dimensions=embedding_dimension)

        print("Processing incoming queries...")
        embedded_query = query.select(vector=embedder(pw.this.query))  # Ensure query is correctly passed

        print("Generating AI response...")
        responses = prompt(index, embedded_query, query.query)  # Pass query.query here as a string

        response_writer(responses.select(response=pw.this.result))

        print("Starting Pathway pipeline...")
        pw.run()

    else:
        print("No query received, skipping processing.")
