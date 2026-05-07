using System.Text.RegularExpressions;

namespace RagGateway.Application.Services;

public static partial class CitationVerifier
{
    public static CitationVerificationResult Verify(string answer, int chunkCount)
    {
        var sentences = SplitSentences(answer);
        var unverified = new List<string>();
        var tagged = new List<string>();

        foreach (var sentence in sentences)
        {
            var references = CitationRegex()
                .Matches(sentence)
                .Select(m => int.Parse(m.Groups[1].Value))
                .ToList();

            var verified = references.Count > 0 && references.All(r => r >= 1 && r <= chunkCount);
            if (verified)
            {
                tagged.Add(sentence);
                continue;
            }

            unverified.Add(sentence);
            tagged.Add($"[UNVERIFIED] {sentence}");
        }

        return new CitationVerificationResult(string.Join(" ", tagged), unverified);
    }

    private static List<string> SplitSentences(string answer)
        => SentenceRegex()
            .Split(answer.Trim())
            .Select(s => s.Trim())
            .Where(s => s.Length > 0)
            .ToList();

    [GeneratedRegex(@"(?<=[.!?])\s+")]
    private static partial Regex SentenceRegex();

    [GeneratedRegex(@"\[(\d+)\]")]
    private static partial Regex CitationRegex();
}

public sealed record CitationVerificationResult(string TaggedAnswer, List<string> UnverifiedSentences);
