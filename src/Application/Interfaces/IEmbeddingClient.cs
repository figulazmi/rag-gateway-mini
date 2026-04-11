namespace RagGateway.Application.Interfaces;

public interface IEmbeddingClient
{
    Task<float[]> GenerateEmbeddingAsync(string text, CancellationToken cancellationToken = default);
}
