using System.Text.Json.Serialization;
using Microsoft.Extensions.Options;
using RagGateway.Application.Interfaces;
using RagGateway.Infrastructure.Configuration;

namespace RagGateway.Infrastructure.AI;

public sealed class OllamaGenerationClient : ILlmGenerationClient
{
    private readonly HttpClient _http;
    private readonly string _model;

    public OllamaGenerationClient(HttpClient http, IOptions<RagGatewayOptions> options)
    {
        _http = http;
        _model = options.Value.GenerationModel;
    }

    public async Task<string> GenerateAsync(string prompt, CancellationToken cancellationToken = default)
    {
        var response = await _http.PostAsJsonAsync(
            "/api/generate",
            new OllamaGenerateRequest
            {
                Model = _model,
                Prompt = prompt,
                Stream = false
            },
            cancellationToken);

        response.EnsureSuccessStatusCode();

        var result = await response.Content.ReadFromJsonAsync<OllamaGenerateResponse>(cancellationToken)
            ?? throw new InvalidOperationException("Ollama returned an empty generation response.");

        if (string.IsNullOrWhiteSpace(result.Response))
            throw new InvalidOperationException($"Ollama returned an empty answer for model '{_model}'.");

        return result.Response.Trim();
    }

    private sealed class OllamaGenerateRequest
    {
        [JsonPropertyName("model")]
        public string Model { get; set; } = string.Empty;

        [JsonPropertyName("prompt")]
        public string Prompt { get; set; } = string.Empty;

        [JsonPropertyName("stream")]
        public bool Stream { get; set; }
    }

    private sealed class OllamaGenerateResponse
    {
        [JsonPropertyName("response")]
        public string Response { get; set; } = string.Empty;
    }
}
