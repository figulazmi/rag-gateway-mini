using System.Text.Json.Serialization;

namespace RagGateway.Application.DTOs;

public sealed class RagResultItem
{
    [JsonPropertyName("score")]
    public float Score { get; set; }

    [JsonPropertyName("content")]
    public string Content { get; set; } = string.Empty;

    [JsonPropertyName("metadata")]
    public Dictionary<string, object> Metadata { get; set; } = [];
}
