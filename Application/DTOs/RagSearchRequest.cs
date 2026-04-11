using System.Text.Json.Serialization;

namespace PetroChina.Eproc.RagGateway.Application.DTOs;

public sealed class RagSearchRequest
{
    [JsonPropertyName("query")]
    public string Query { get; set; } = string.Empty;

    [JsonPropertyName("project")]
    public string? Project { get; set; }
}
