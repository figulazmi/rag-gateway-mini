using System.Text.Json.Serialization;

namespace RagGateway.Application.DTOs;

public sealed class RagDebugResponse
{
    [JsonPropertyName("normalized_query")]
    public string NormalizedQuery { get; set; } = string.Empty;

    [JsonPropertyName("project_filter")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? ProjectFilter { get; set; }

    [JsonPropertyName("threshold")]
    public float Threshold { get; set; }

    [JsonPropertyName("total_raw_results")]
    public int TotalRawResults { get; set; }

    [JsonPropertyName("results_above_threshold")]
    public int ResultsAboveThreshold { get; set; }

    [JsonPropertyName("results")]
    public List<RagResultItem> Results { get; set; } = [];
}
