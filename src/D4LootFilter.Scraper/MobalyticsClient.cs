using System.Diagnostics;
using System.Text.Json;

namespace D4LootFilter.Scraper;

public class MobalyticsClient
{
    private const string Endpoint = "https://mobalytics.gg/api/diablo4/v4/graphql/query";
    private const string UserAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36";

    private const string Query =
        "query Diablo4UgFeaturedDocumentQuery($input: Diablo4UserGeneratedDocumentInputBySlug!) " +
        "{ game: diablo4 { documents { userGeneratedDocumentBySlug(input: $input) { error data { id slugifiedName type " +
        "data { name buildVariants { values { id genericBuilder { slots { gameSlotSlug gameEntity { slug title type " +
        "modifiers { gearStats { id isGreater isMasterwork } temperingStats { id isGreater isMasterwork } } " +
        "entity { ... on D4Aspect { __typename title: name } ... on D4UniqueItem { __typename title: name chaos mythic } } } } } } } } " +
        "content { __typename ... on NgfDocumentCmWidgetContentVariantsV1 { data { childrenVariants { id title } } } } } } } } }";

    public async Task<string> FetchBuildAsync(string slug, CancellationToken ct = default)
    {
        var payload = new
        {
            query = Query,
            variables = new
            {
                input = new
                {
                    slug,
                    type = "builds",
                    widgetsOverride = Array.Empty<object>(),
                }
            },
            operationName = "Diablo4UgFeaturedDocumentQuery",
        };

        var bodyJson = JsonSerializer.Serialize(payload);
        var tempFile = Path.GetTempFileName();
        try
        {
            await File.WriteAllTextAsync(tempFile, bodyJson, ct);

            var psi = new ProcessStartInfo
            {
                FileName = "curl.exe",
                ArgumentList =
                {
                    "-s", "--fail-with-body",
                    "-X", "POST", Endpoint,
                    "-H", "Content-Type: application/json",
                    "-H", $"User-Agent: {UserAgent}",
                    "-H", "Accept: application/json",
                    "-H", "Origin: https://mobalytics.gg",
                    "-H", $"Referer: https://mobalytics.gg/diablo-4/builds/{slug}",
                    "-d", $"@{tempFile}",
                    "--max-time", "15",
                },
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
                CreateNoWindow = true,
            };

            using var process = Process.Start(psi)
                ?? throw new InvalidOperationException("Failed to start curl.exe");

            var output = await process.StandardOutput.ReadToEndAsync(ct);
            var error = await process.StandardError.ReadToEndAsync(ct);

            await process.WaitForExitAsync(ct);

            if (process.ExitCode != 0)
                throw new HttpRequestException(
                    $"Mobalytics API request failed (curl exit {process.ExitCode}): {error}");

            if (string.IsNullOrWhiteSpace(output))
                throw new HttpRequestException("Mobalytics API returned empty response");

            return output;
        }
        finally
        {
            try { File.Delete(tempFile); } catch { }
        }
    }
}
