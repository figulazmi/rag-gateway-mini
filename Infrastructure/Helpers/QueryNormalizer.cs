namespace PetroChina.Eproc.RagGateway.Infrastructure.Helpers;

public static class QueryNormalizer
{
    private const int MinWordCount = 8;

    // Phrases appended word-by-word until the 8-word minimum is reached.
    // Order is intentional: most semantically neutral first.
    private static readonly string[] PaddingWords =
    [
        "implementation", "details", "best", "practice",
        "code", "example", "architecture", "backend"
    ];

    /// <summary>
    /// Ensures the query has at least 8 words for a semantically rich embedding.
    /// Deterministic: same input always produces same output.
    /// </summary>
    public static string Normalize(string query)
    {
        if (string.IsNullOrWhiteSpace(query))
            return string.Join(' ', PaddingWords);

        query = query.Trim();
        var words = query.Split(' ', StringSplitOptions.RemoveEmptyEntries);

        if (words.Length >= MinWordCount)
            return string.Join(' ', words);

        var parts = new List<string>(words);
        foreach (var word in PaddingWords)
        {
            if (parts.Count >= MinWordCount)
                break;
            parts.Add(word);
        }

        return string.Join(' ', parts);
    }
}
