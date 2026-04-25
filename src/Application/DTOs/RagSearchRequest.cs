using System.Text.Json.Serialization;

namespace RagGateway.Application.DTOs;

public sealed class RagSearchRequest
{
    [JsonPropertyName("query")]
    public string Query { get; set; } = string.Empty;

    [JsonPropertyName("project")]
    public string? Project { get; set; }

    [JsonPropertyName("chunk_type")]
    public string? ChunkType { get; set; }

    [JsonPropertyName("feature_slug")]
    public string? FeatureSlug { get; set; }
}
