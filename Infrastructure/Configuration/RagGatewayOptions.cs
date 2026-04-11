namespace PetroChina.Eproc.RagGateway.Infrastructure.Configuration;

public sealed class RagGatewayOptions
{
    public const string Section = "RagGateway";

    public string OllamaBaseUrl { get; set; } = "http://localhost:11434";
    public string QdrantBaseUrl { get; set; } = "http://localhost:6333";
    public string OllamaModel { get; set; } = "nomic-embed-text";
    public string QdrantCollection { get; set; } = "knowledge";
    public string? QdrantApiKey { get; set; }
    public float ScoreThreshold { get; set; } = 0.65f;
    public int ResultLimit { get; set; } = 5;
}
