namespace RagGateway.Infrastructure.Configuration;

public sealed class RagGatewayOptions
{
    public const string Section = "RagGateway";

    public string OllamaBaseUrl { get; set; } = "http://localhost:11434";
    public string QdrantBaseUrl { get; set; } = "http://localhost:6333";
    public string OllamaModel { get; set; } = "nomic-embed-text";
    public string QdrantCollection { get; set; } = "knowledge_v2";
    public string? QdrantApiKey { get; set; }
    public float ScoreThreshold { get; set; } = 0.35f;
    public float NotFoundScoreThreshold { get; set; } = 0.55f;
    public int ResultLimit { get; set; } = 5;

    public string DenseVectorName { get; set; } = "dense";
    public string SparseVectorName { get; set; } = "sparse";
    public bool EnableHybridSearch { get; set; } = true;
    public int HybridPrefetchLimit { get; set; } = 20;
    public int SparsePrefetchLimit { get; set; } = 5;
    public float SparseScoreThreshold { get; set; } = 0.01f;
    public string FusionMethod { get; set; } = "rrf";
    public string SparseInferenceModel { get; set; } = "Qdrant/bm25";
    public string GenerationModel { get; set; } = "llama3.2:3b";
}
