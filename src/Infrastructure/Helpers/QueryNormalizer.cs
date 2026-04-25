namespace RagGateway.Infrastructure.Helpers;

public static class QueryNormalizer
{
    public static string Normalize(string query)
    {
        if (string.IsNullOrWhiteSpace(query))
            return string.Empty;

        return string.Join(' ', query.Trim().Split(' ', StringSplitOptions.RemoveEmptyEntries));
    }
}
