using System.Text.Json.Serialization;
using Microsoft.Extensions.Options;
using RagGateway.Application.Interfaces;
using RagGateway.Infrastructure.Configuration;

namespace RagGateway.Infrastructure.AI;

public sealed class OllamaEmbeddingClient : IEmbeddingClient
{
    private readonly HttpClient _http;
    private readonly string _model;

    public OllamaEmbeddingClient(HttpClient http, IOptions<RagGatewayOptions> options)
    {
        _http = http;
        _model = options.Value.OllamaModel;
    }

    public async Task<float[]> GenerateEmbeddingAsync(string text, CancellationToken cancellationToken = default)
    {
        var response = await _http.PostAsJsonAsync(
            "/api/embeddings",
            new OllamaEmbeddingRequest { Model = _model, Prompt = text },
            cancellationToken);

        response.EnsureSuccessStatusCode();

        var result = await response.Content.ReadFromJsonAsync<OllamaEmbeddingResponse>(cancellationToken)
            ?? throw new InvalidOperationException("Ollama returned an empty embedding response.");

        if (result.Embedding is not { Length: > 0 })
            throw new InvalidOperationException($"Ollama returned zero-length embedding for model '{_model}'.");

        return result.Embedding;
    }

    private sealed class OllamaEmbeddingRequest
    {
        [JsonPropertyName("model")]
        public string Model { get; set; } = string.Empty;

        [JsonPropertyName("prompt")]
        public string Prompt { get; set; } = string.Empty;
    }

    private sealed class OllamaEmbeddingResponse
    {
        [JsonPropertyName("embedding")]
        public float[] Embedding { get; set; } = [];
    }
}
