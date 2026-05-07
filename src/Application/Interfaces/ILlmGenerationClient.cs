namespace RagGateway.Application.Interfaces;

public interface ILlmGenerationClient
{
    Task<string> GenerateAsync(string prompt, CancellationToken cancellationToken = default);
}
