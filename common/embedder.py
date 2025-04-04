import os
from dotenv import load_dotenv

import pathway as pw
from pathway.stdlib.ml.index import KNNIndex
from pathway.xpacks.llm import embedders


load_dotenv()


embedding_dimension = int(os.environ.get("EMBEDDING_DIMENSION", 1024))
embedder = embedders.SentenceTransformerEmbedder(model="intfloat/e5-large-v2")

def embeddings(context, data_to_embed):
    return context + context.select(vector=embedder(data_to_embed))


def index_embeddings(embedded_data):
    return KNNIndex(embedded_data.vector, embedded_data, n_dimensions=embedding_dimension)
