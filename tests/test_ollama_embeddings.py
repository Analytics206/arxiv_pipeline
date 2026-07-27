from src.retrieval.ollama_embeddings import OllamaEmbeddingModel


def test_query_and_document_prefixes_are_applied_separately():
    model = OllamaEmbeddingModel.__new__(OllamaEmbeddingModel)
    model.model_name = "test-model"
    model.query_prefix = "query: "
    model.document_prefix = "document: "
    inputs = []

    def fake_embed(values):
        inputs.append(values)
        return [[float(index)] for index, _ in enumerate(values, start=1)]

    model._embed = fake_embed

    assert model.embed_documents(["alpha", "beta"]) == [[1.0], [2.0]]
    assert model.embed_query("gamma") == [1.0]
    assert inputs == [
        ["document: alpha", "document: beta"],
        ["query: gamma"],
    ]
